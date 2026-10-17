#!/usr/bin/env python3
"""Private, explicitly owner-visible agent coordination; never a task/approval store."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import html
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import threading
import sys
import time
from urllib.parse import urlsplit
import uuid

DEFAULT_PATH = Path.home() / '.local/state/agent-board/messages.jsonl'
MAX_LOG_BYTES = 8 * 1024 * 1024
MAX_MESSAGE = 2000
LOCK_TIMEOUT = 2.0
KINDS = ('update', 'question', 'blocker', 'evidence', 'ownership', 'handoff')
STATUSES = ('open', 'waiting', 'resolved')
THREAD_FIELDS = {'thread_id', 'topic', 'owner', 'status'}
FIELDS = {'schema', 'id', 'created_at', 'audience', 'author', 'task', 'project',
          'kind', 'message', 'references', 'reply_to'}
SENSITIVE = re.compile(
    r'/Users/|/home/|/tmp/|file://|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|'
    r'\b\d{3}[- .]\d{3}[- .]\d{4}\b|BEGIN[^\n]*PRIVATE KEY|'
    r'\b(?:api[_-]?key|access[_-]?token|password)\s*[:=]|\bBearer\s+\S+|'
    r'\bgh[pousr]_[A-Za-z0-9_]{16,}|\bsk-[A-Za-z0-9_-]{16,}', re.I)


def _text(value, maximum: int) -> str:
    if (not isinstance(value, str) or not value.strip() or len(value) > maximum
            or any(ord(c) < 32 and c not in '\n\t' or ord(c) == 127
                   or 0xD800 <= ord(c) <= 0xDFFF for c in value)
            or SENSITIVE.search(value)):
        raise ValueError('Use bounded ordinary coordination text; private details are not allowed')
    return value.strip()


def _reference(value) -> str:
    value = _text(value, 500)
    parsed = urlsplit(value)
    if re.fullmatch(r'codex://threads/[0-9a-fA-F-]{36}', value):
        uuid.UUID(parsed.path[1:])
        return value
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.port not in (None, 443)
            or any(c.isspace() for c in value) or '\\' in value
            or parsed.hostname.lower() in {'mail.google.com', 'outlook.live.com', 'outlook.office.com'}):
        raise ValueError('References must be HTTPS evidence links without credentials/query strings, or Codex thread links')
    return value


def _validate(record: dict) -> None:
    if (not isinstance(record, dict) or type(record.get('schema')) is not int
            or record['schema'] not in (1, 2)
            or set(record) != (FIELDS if record['schema'] == 1 else FIELDS | THREAD_FIELDS)
            or record['audience'] != 'coordination'
            or not isinstance(record['id'], str) or not re.fullmatch(r'[a-f0-9]{32}', record['id'])
            or record['kind'] not in KINDS):
        raise ValueError('Invalid coordination record')
    if record['schema'] == 2:
        _text(record['topic'], 160)
        if any(c in record['topic'] for c in '\r\n\t'): raise ValueError('Topic must be one line')
        if record['owner'] is not None:
            _text(record['owner'], 80)
            if any(c in record['owner'] for c in '\r\n\t'): raise ValueError('Owner must be one line')
        if record['status'] not in STATUSES or not isinstance(record['thread_id'], str) or not re.fullmatch(r'[a-f0-9]{32}', record['thread_id']):
            raise ValueError('Invalid discussion metadata')
    when = datetime.fromisoformat(_text(record['created_at'], 64))
    if when.tzinfo is None or when.utcoffset().total_seconds() != 0:
        raise ValueError('Message timestamp must be UTC')
    for key, size in [('author', 80), ('task', 160), ('project', 80), ('message', MAX_MESSAGE)]:
        _text(record[key], size)
        if key != 'message' and any(c in record[key] for c in '\r\n\t'):
            raise ValueError('Identity fields must be one line')
    if re.search(r'https?://\S+', record['message'], re.I):
        raise ValueError('Put evidence URLs in references, not message text')
    refs = record['references']
    if not isinstance(refs, list) or len(refs) > 8:
        raise ValueError('Use at most eight evidence references')
    for ref in refs: _reference(ref)
    reply = record['reply_to']
    if reply is not None and (not isinstance(reply, str) or not re.fullmatch(r'[a-f0-9]{32}', reply)):
        raise ValueError('Reply must name a message ID')


def _private_fd(fd: int) -> None:
    info = os.fstat(fd)
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_nlink != 1 or info.st_mode & 0o077):
        raise OSError('Message files must be private, owned regular files without hard links')


@contextmanager
def _locked(path: Path, *, create: bool = False):
    if create: path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    parent = path.parent.stat()
    if path.parent.is_symlink() or not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid() or parent.st_mode & 0o077:
        raise OSError('Message directory must be private and owned by this user')
    fd = os.open(path.with_suffix(path.suffix + '.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        _private_fd(fd)
        until = time.monotonic() + LOCK_TIMEOUT
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= until: raise OSError('Message board busy; retry after the current writer') from None
                time.sleep(0.02)
        yield
    finally:
        os.close(fd)


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('Duplicate field')
        result[key] = value
    return result


def _read(path: Path) -> list[dict]:
    try: fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError: return []
    try:
        _private_fd(fd)
        with os.fdopen(fd, 'rb', closefd=False) as handle: data = handle.read(MAX_LOG_BYTES + 1)
    finally: os.close(fd)
    if len(data) > MAX_LOG_BYTES or data and not data.endswith(b'\n'):
        raise ValueError('Message log incomplete or too large; preserve it and reconcile locally')
    records, seen = [], set()
    try:
        for line in data.splitlines():
            item = json.loads(line, object_pairs_hook=_object)
            _validate(item)
            if item['id'] in seen or item['reply_to'] is not None and item['reply_to'] not in seen:
                raise ValueError('Invalid message chain')
            seen.add(item['id']); records.append(item)
    except (ValueError, TypeError, KeyError, AttributeError, UnicodeError):
        raise ValueError('Message log invalid; preserve it and reconcile locally') from None
    _threads(records)
    return records


def _threads(records: list[dict]) -> dict[str, dict]:
    threads, message_threads = {}, {}
    for item in records:
        parent = item['reply_to']
        thread_id = message_threads[parent] if parent is not None else item['id']
        if item['schema'] == 2 and item['thread_id'] != thread_id:
            raise ValueError('Invalid thread membership')
        if thread_id not in threads:
            threads[thread_id] = dict(id=thread_id, topic=item.get('topic', item['task']),
                                     project=item['project'], owner=None, status='open', messages=[])
        thread = threads[thread_id]
        if item['schema'] == 2 and (item['project'] != thread['project'] or item['topic'] != thread['topic']):
            raise ValueError('Thread topic and project must remain stable')
        if item['schema'] == 2:
            thread.update(owner=item['owner'], status=item['status'])
        thread['messages'].append(item)
        thread['last_sequence'] = len(message_threads)
        message_threads[item['id']] = thread_id
    return threads


def _load(path: Path) -> list[dict]:
    remote = _remote(path)
    if remote is not None: return remote.records()
    if not path.parent.exists(): return []
    with _locked(path): return _read(path)


def _remote(path: Path):
    import agent_board_remote
    return agent_board_remote.configured(path)


def _search(value: str | None) -> str:
    return _text(value, 160).casefold() if value else ''


def _matches(item: dict, query: str) -> bool:
    return not query or query in ' '.join(str(item.get(k, '')) for k in
        ('topic', 'project', 'author', 'task', 'message', 'owner')).casefold()


def _selected_threads(records: list[dict], *, project=None, status=None, inbox=False, search=None, thread=None):
    query = _search(search)
    if status is not None and status not in STATUSES: raise ValueError('Invalid status')
    selected = [t for t in _threads(records).values()
                if (project is None or t['project'] == project)
                and (status is None or t['status'] == status)
                and (thread is None or t['id'] == thread)
                and (not inbox or t['owner'] is None and t['status'] != 'resolved')
                and (not query or _matches(t, query) or any(_matches(m, query) for m in t['messages']))]
    return sorted(selected, key=lambda t: t['last_sequence'], reverse=True)


def list_threads(path: Path = DEFAULT_PATH, *, limit: int = 30, project=None, status=None, inbox=False, search=None) -> list[dict]:
    if type(limit) is not int or not 1 <= limit <= 200: raise ValueError('Limit must be from 1 to 200')
    selected = _selected_threads(_load(path), project=project, status=status, inbox=inbox, search=search)[:limit]
    return [dict(id=t['id'], topic=t['topic'], project=t['project'], owner=t['owner'], status=t['status'],
                 count=len(t['messages']), updated_at=t['messages'][-1]['created_at'],
                 last_id=t['messages'][-1]['id'], last_author=t['messages'][-1]['author'],
                 last_message=t['messages'][-1]['message']) for t in selected]


def list_messages(path: Path = DEFAULT_PATH, *, limit: int = 30,
                  project: str | None = None, task: str | None = None,
                  thread: str | None = None, search: str | None = None) -> list[dict]:
    if type(limit) is not int or not 1 <= limit <= 200: raise ValueError('Limit must be from 1 to 200')
    records = _load(path); query = _search(search)
    ids = {m['id'] for t in _selected_threads(records, thread=thread) for m in t['messages']}
    selected = [r for r in reversed(records) if r['id'] in ids
                and (project is None or r['project'] == project)
                and (task is None or r['task'] == task) and _matches(r, query)]
    return selected[:limit]


def post(path: Path = DEFAULT_PATH, *, author: str, task: str, project: str,
         kind: str, message: str, references: list[str], owner_visible: bool,
         reply_to: str | None = None, thread: str | None = None, topic: str | None = None,
         owner: str | None = None, unowned: bool = False, status: str | None = None) -> dict:
    remote = _remote(path)
    if remote is not None:
        return remote.post(author=author, task=task, project=project, kind=kind, message=message,
                           references=references, owner_visible=owner_visible, reply_to=reply_to,
                           thread=thread, topic=topic, owner=owner, unowned=unowned, status=status)
    if owner_visible is not True:
        raise ValueError('Confirm with --owner-visible that the owner may read this ordinary coordination')
    if reply_to and thread or owner is not None and unowned: raise ValueError('Conflicting options')
    if topic is not None: topic = _text(topic, 160)
    if owner is not None: owner = _text(owner, 80)
    if status is not None and status not in STATUSES: raise ValueError('Invalid status')
    author, task, project = _text(author, 80), _text(task, 160), _text(project, 80)
    item = dict(schema=1, id=uuid.uuid4().hex, created_at=datetime.now(timezone.utc).isoformat(),
                audience='coordination', author=author, task=task, project=project, kind=kind,
                message=_text(message, MAX_MESSAGE), references=references, reply_to=reply_to)
    _validate(item)
    with _locked(path, create=True):
        records = _read(path)
        threads = _threads(records)
        target = None
        if thread is not None:
            target = threads.get(thread)
            if target is None: raise ValueError('Thread does not exist; read the board first')
            reply_to = thread
        elif reply_to is not None:
            target = next((t for t in threads.values() if any(m['id'] == reply_to for m in t['messages'])), None)
            if target is None: raise ValueError('Reply target does not exist; read the board first')
        else:
            target = next((t for t in sorted(threads.values(), key=lambda t:t['last_sequence'], reverse=True)
                           if t['project'].casefold() == project.casefold() and t['topic'].casefold() == (topic or task).casefold()), None)
            if target: reply_to = target['id']
        if target and (target['project'] != project or topic is not None and topic != target['topic']):
            raise ValueError('Reply must keep the existing project/topic')
        item.update(schema=2, reply_to=reply_to, thread_id=target['id'] if target else item['id'],
                    topic=target['topic'] if target else topic or task,
                    owner=None if unowned else owner if owner is not None else target['owner'] if target else None,
                    status=status or (target['status'] if target else 'open'))
        _validate(item)
        payload = (json.dumps(item, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
        size = path.stat().st_size if path.exists() else 0
        if size + len(payload) > MAX_LOG_BYTES:
            raise ValueError('Message log full; preserve it and arrange explicit archival')
        fd = os.open(path, os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            _private_fd(fd)
            remaining = memoryview(payload)
            while remaining:
                written = os.write(fd, remaining)
                if written <= 0: raise OSError('Append incomplete; inspect the log before retrying')
                remaining = remaining[written:]
            os.fsync(fd)
        finally: os.close(fd)
        for directory in (path.parent, *path.parent.parents):
            directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try: os.fsync(directory_fd)
            finally: os.close(directory_fd)
    return item


def render(path: Path = DEFAULT_PATH) -> str:
    start = '<section aria-label="Agent message board"><h2>Agent message board</h2><p>Project discussions and a shared inbox. Messages are not approval or task completion.</p>'
    try:
        remote = _remote(path)
        if remote is not None:
            state = remote.status()
            start += (f'<p class="note">{state["synced"]} synced · {state["queued"]} queued locally. '
                      f'Last successful sync: {html.escape(state["synced_at"] or "not yet synced")}.</p>')
            if state['conflicts']:
                start += '<p class="note">Competing discussion updates need reconciliation; all messages are retained. Use sync-status for event IDs.</p>'
            if state['duplicate_topics']:
                start += '<p class="note">Some topics were started independently offline. Use their explicit thread IDs.</p>'
        threads = _selected_threads(_load(path))[:30]
    except (OSError, ValueError):
        return start + '<p class="note">Messages unavailable. Existing records are preserved; reconcile the private log locally.</p></section>'
    if not threads:
        return start + '<p class="note">No coordination messages yet.</p></section>'
    groups = {}
    for t in threads:
        label = 'Shared inbox · unowned' if t['owner'] is None and t['status'] != 'resolved' else t['project']
        groups.setdefault(label, []).append(t)
    esc = html.escape; out = [start]
    for label, group in sorted(groups.items(), key=lambda pair: (pair[0] != 'Shared inbox · unowned', pair[0].casefold())):
        out.append(f'<h3>{esc(label)}</h3>')
        for t in group:
            out.append(f'<article class="git-note" style="overflow-wrap:anywhere" id="thread-{t["id"]}">')
            out.append(f'<h3>{esc(t["topic"])}</h3><p>{esc(t["project"])} · {esc(t["status"])} · Discussion owner: {esc(t["owner"] or "unowned")}</p>')
            out.append(f'<p><small>Thread ID: {t["id"]} · {len(t["messages"])} messages</small></p>')
            latest = t['messages'][-1]
            preview = latest['message'][:240] + ('…' if len(latest['message']) > 240 else '')
            out.append(f'<p>{esc(preview)}</p>')
            out.append(f'<details><summary>Recent conversation · {esc(latest["author"])} · {esc(latest["created_at"])}</summary>')
            for item in reversed(t['messages'][-5:]):
                out.append(f'<div id="message-{item["id"]}"><p><strong>{esc(item["author"])}</strong> · {esc(item["task"])} · {esc(item["kind"])} · <time datetime="{esc(item["created_at"])}">{esc(item["created_at"])}</time></p>')
                if item['project'] != t['project']:
                    out.append(f'<p>Original project: {esc(item["project"])}</p>')
                out.append('<p style="white-space:pre-wrap;overflow-wrap:anywhere">' + esc(item['message']) + '</p>')
                for ref in item['references']:
                    out.append(f'<p><a href="{esc(ref, quote=True)}" target="_blank" rel="noopener noreferrer">{esc(ref)}</a></p>')
                if item['reply_to']: out.append(f'<p><small>Reply to {item["reply_to"]}</small></p>')
                out.append(f'<p><small>Message ID: {item["id"]}</small></p></div>')
            if len(t['messages']) > 5: out.append('<p>Showing the latest five messages in this conversation.</p>')
            out.append('</details></article>')
    out.append('<p class="note">Showing up to 30 recently active discussions. Discussion ownership/status does not change shared tasks.</p>')
    return ''.join(out) + '</section>'


def start_readonly_refresh(path: Path = DEFAULT_PATH, *, interval: float = 300):
    if interval < 60: raise ValueError('Refresh interval must be at least one minute')
    stop = threading.Event()
    def run():
        while not stop.is_set():
            try:
                remote = _remote(path)
                if remote is not None: remote.sync(publish=False)
            except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
                pass
            stop.wait(interval)
    worker = threading.Thread(target=run, name='agent-board-read-refresh', daemon=True)
    worker.start()
    return stop, worker


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, default=DEFAULT_PATH, help='Local state file; its folder also holds the cache and outbox')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('sync', help='Publish queued events and refresh the private cache')
    commands.add_parser('refresh', help='Refresh without publishing local events')
    commands.add_parser('sync-status', help='Show counts, freshness and conflicting event IDs')
    setup = commands.add_parser('connect', help='Attach this client to a private GitHub board')
    setup.add_argument('--repository', required=True)
    setup.add_argument('--prefix', default='', help='Board data directory inside the private repository')
    relocation = commands.add_parser('relocate', help='Switch to a verified imported board without discarding local records')
    relocation.add_argument('--repository', required=True)
    relocation.add_argument('--prefix', required=True)
    relocation.add_argument('--source-head', required=True, help='Reviewed frozen revision of the current board')
    listing = commands.add_parser('list', help='Print newest-first JSONL')
    listing.add_argument('--limit', type=int, default=30)
    listing.add_argument('--project'); listing.add_argument('--task')
    listing.add_argument('--thread'); listing.add_argument('--search')
    grouping = commands.add_parser('threads', help='Print bounded discussion summaries, newest activity first')
    grouping.add_argument('--limit', type=int, default=30)
    grouping.add_argument('--project'); grouping.add_argument('--status', choices=STATUSES)
    grouping.add_argument('--inbox', action='store_true'); grouping.add_argument('--search')
    sending = commands.add_parser('post', help='Append a coordination message from stdin')
    for field in ('author', 'task', 'project'): sending.add_argument('--' + field, required=True)
    sending.add_argument('--kind', choices=KINDS, default='update')
    sending.add_argument('--ref', action='append', default=[], dest='references')
    target = sending.add_mutually_exclusive_group()
    target.add_argument('--reply-to'); target.add_argument('--thread')
    sending.add_argument('--topic'); sending.add_argument('--status', choices=STATUSES)
    sending.add_argument('--offline', action='store_true', help='Queue without attempting remote delivery')
    ownership = sending.add_mutually_exclusive_group()
    ownership.add_argument('--owner'); ownership.add_argument('--unowned', action='store_true')
    sending.add_argument('--owner-visible', action='store_true', required=True,
                         help='Confirm ordinary coordination only: no secrets, assistant notes or sensitive correspondence')
    args = parser.parse_args()
    try:
        if args.command == 'connect':
            import agent_board_remote
            print(json.dumps(agent_board_remote.connect(args.store, args.repository, prefix=args.prefix).status()))
        elif args.command == 'relocate':
            import agent_board_remote
            board = agent_board_remote.relocate(args.store, args.repository, prefix=args.prefix,
                                                source_head=args.source_head)
            print(json.dumps(board.status()))
        elif args.command in ('sync','refresh','sync-status'):
            remote = _remote(args.store)
            if remote is None: raise ValueError('No remote board configured')
            if args.command != 'sync-status': remote.sync(publish=args.command=='sync')
            print(json.dumps(remote.status()))
        elif args.command == 'list':
            for item in list_messages(args.store, limit=args.limit, project=args.project, task=args.task, thread=args.thread, search=args.search):
                print(json.dumps(item, ensure_ascii=False))
        elif args.command == 'threads':
            for item in list_threads(args.store, limit=args.limit, project=args.project, status=args.status, inbox=args.inbox, search=args.search):
                print(json.dumps(item, ensure_ascii=False))
        else:
            message = sys.stdin.read(MAX_MESSAGE + 1)
            item = post(args.store, author=args.author, task=args.task, project=args.project, kind=args.kind,
                        message=message, references=args.references, reply_to=args.reply_to, owner_visible=args.owner_visible,
                        thread=args.thread, topic=args.topic, owner=args.owner, unowned=args.unowned, status=args.status)
            result={'id':item['id'],'thread_id':item['thread_id'],'created_at':item['created_at']}
            remote=_remote(args.store)
            if remote is not None:
                result['delivery']='queued'
                if not args.offline:
                    try:
                        remote.sync()
                        result['delivery']='synced'
                    except (OSError,ValueError,subprocess.SubprocessError):
                        result['notice']='Saved locally; sync not confirmed. Run sync; do not repost.'
            print(json.dumps(result))
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
        print('Board operation failed; no success confirmed. Validate input and inspect the private log before retrying.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__': raise SystemExit(main())
