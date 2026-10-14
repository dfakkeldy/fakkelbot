import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import agent_messages as board

ROOT = Path(__file__).resolve().parents[1]

class AgentMessageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Path(self.temp.name) / 'board' / 'messages.jsonl'

    def post(self, **changes):
        values = dict(author='codex', task='board-setup', project='example-app',
                      kind='update', message='Implementation ready for review.',
                      references=['https://github.com/example/project/pull/1'],
                      owner_visible=True)
        values.update(changes)
        return board.post(self.store, **values)

    def test_missing_read_does_not_create_state_and_post_returns_dated_identity(self):
        self.assertEqual([], board.list_messages(self.store))
        self.assertFalse(self.store.parent.exists())
        item = self.post()
        self.assertEqual('coordination', item['audience'])
        self.assertRegex(item['id'], r'^[a-f0-9]{32}$')
        self.assertTrue(item['created_at'].endswith('+00:00'))
        self.assertEqual([item], board.list_messages(self.store))
        self.assertEqual(0o600, self.store.stat().st_mode & 0o777)
        self.assertEqual(0o700, self.store.parent.stat().st_mode & 0o777)

    def test_replies_filters_and_latest_first_preserve_previous_bytes(self):
        first = self.post()
        prior = self.store.read_bytes()
        second = self.post(task='review', kind='handoff', message='Review passed.', reply_to=first['id'])
        self.assertTrue(self.store.read_bytes().startswith(prior))
        self.assertEqual([second, first], board.list_messages(self.store))
        self.assertEqual([second], board.list_messages(self.store, task='review'))
        self.assertEqual([second], board.list_messages(self.store, limit=1))
        self.assertEqual([], board.list_messages(self.store, project='other'))
        with self.assertRaises(ValueError): self.post(reply_to='0'*32)

    def test_acknowledged_posts_sync_file_then_every_directory_ancestor(self):
        self.store = self.store.parent / 'nested' / 'messages.jsonl'
        real_fsync = os.fsync
        expected = [self.store, self.store.parent, *self.store.parent.parents]
        for _ in range(2):
            synced = []
            def sync(fd):
                info = os.fstat(fd)
                synced.append((info.st_dev, info.st_ino))
                real_fsync(fd)
            with mock.patch.object(board.os, 'fsync', side_effect=sync): self.post()
            self.assertEqual([(p.stat().st_dev, p.stat().st_ino) for p in expected], synced)

    def test_invalid_unicode_is_rejected_without_hiding_the_page(self):
        item = self.post()
        for field in ('author', 'task', 'project', 'message', 'references', 'created_at', 'topic', 'owner'):
            bad = dict(item)
            bad[field] = ['https://example.test/\ud800'] if field == 'references' else '\ud800'
            if field == 'created_at': bad[field] = '2026-10-09\ud80012:00:00+00:00'
            self.store.write_text(json.dumps(bad) + '\n')
            with self.assertRaises(ValueError): board.list_messages(self.store)
            self.assertIn('Messages unavailable', board.render(self.store))
            board.render(self.store).encode('utf-8')
        with self.assertRaises(ValueError): self.post(message='\ud800')

    def test_concurrent_cli_processes_preserve_every_message(self):
        def writer(number):
            return subprocess.run([sys.executable, str(ROOT/'agent_messages.py'),
                '--store', str(self.store), 'post', '--author', 'worker', '--task', f'task-{number}',
                '--project', 'example-app', '--kind', 'update', '--owner-visible'],
                input=f'Concurrent result {number}.', text=True, capture_output=True, timeout=15)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = list(pool.map(writer, range(24)))
        self.assertTrue(all(p.returncode == 0 for p in outcomes), [p.stderr for p in outcomes])
        records = board.list_messages(self.store, limit=100)
        self.assertEqual(24, len(records))
        self.assertEqual(24, len({r['id'] for r in records}))
        self.assertEqual({f'task-{n}' for n in range(24)}, {r['task'] for r in records})

    def test_invalid_or_sensitive_input_does_not_append(self):
        self.post(); before = self.store.read_bytes()
        invalid = [dict(owner_visible=False), dict(kind='execute'), dict(message='x'*2001),
            dict(author=''), dict(message='Contact private@example.test'),
            dict(message='Open /Users/jane/notes.md'), dict(message='api_key=secret'),
            dict(message='Call 555-555-0199'), dict(message='https://example.test/?token=private'),
            dict(references=['javascript:alert(1)']), dict(references=['https://user:pass@example.test']),
            dict(references=['https://example.test/?token=private']),
            dict(references=['https://mail.google.com/mail/u/0/#inbox/private']),
            dict(references=['file:///Users/jane/notes.md'])]
        for values in invalid:
            with self.subTest(values=values):
                with self.assertRaises(ValueError): self.post(**values)
        self.assertEqual(before, self.store.read_bytes())

    def test_corruption_fails_closed_without_erasing_data(self):
        self.post()
        with self.store.open('ab') as f: f.write(b'{"private_note":"DO NOT DISPLAY"')
        before = self.store.read_bytes()
        with self.assertRaises(ValueError): board.list_messages(self.store)
        with self.assertRaises(ValueError): self.post()
        page = board.render(self.store)
        self.assertIn('Messages unavailable', page)
        self.assertNotIn('DO NOT DISPLAY', page)
        self.assertEqual(before, self.store.read_bytes())

    def test_invalid_schema_and_duplicate_keys_never_render(self):
        item = self.post()
        for bad in [dict(item, audience='private'), dict(item, private_notes='SECRET'),
                    dict(item, created_at='2026-10-09T12:00:00'), dict(item, id='bad')]:
            self.store.write_text(json.dumps(bad)+'\n')
            with self.assertRaises(ValueError): board.list_messages(self.store)
        self.store.write_text('{"id":"a","id":"b"}\n')
        with self.assertRaises(ValueError): board.list_messages(self.store)

    def test_symlinks_nonprivate_and_hardlinked_files_are_refused(self):
        self.post(); original = self.store.read_bytes()
        alias = self.store.with_name('alias.jsonl'); alias.symlink_to(self.store)
        with self.assertRaises((ValueError,OSError)): board.list_messages(alias)
        with self.assertRaises((ValueError,OSError)): board.post(alias, author='codex',task='t',project='p',kind='update',message='Update',references=[],owner_visible=True)
        self.store.chmod(0o644)
        with self.assertRaises(OSError): board.list_messages(self.store)
        self.store.chmod(0o600)
        hard = self.store.with_name('hard.jsonl'); os.link(self.store,hard)
        with self.assertRaises(OSError): board.list_messages(self.store)
        self.assertEqual(original,self.store.read_bytes())

    def test_render_escapes_text_and_links_without_forms(self):
        item = self.post(message='<script>alert("x")</script> & reviewed',
                         references=['https://github.com/example/project/pull/1#review'])
        page = board.render(self.store)
        self.assertIn('&lt;script&gt;',page); self.assertNotIn('<script>',page)
        self.assertIn('rel="noopener noreferrer"',page)
        self.assertIn(item['id'],page)
        self.assertNotIn('<form',page)
        self.assertIn('not approval',page)

    def test_cli_list_and_validation_exit_codes(self):
        self.post()
        result = subprocess.run([sys.executable,str(ROOT/'agent_messages.py'),'--store',str(self.store),'list'],capture_output=True,text=True)
        self.assertEqual(0,result.returncode)
        self.assertEqual('codex',json.loads(result.stdout)['author'])
        result = subprocess.run([sys.executable,str(ROOT/'agent_messages.py'),'--store',str(self.store),'post','--author','c','--task','t','--project','p'],input='No visibility confirmation.',capture_output=True,text=True)
        self.assertNotEqual(0,result.returncode)
        self.assertNotIn('No visibility confirmation.',result.stderr)

    def test_log_bound_and_lock_timeout_preserve_data(self):
        self.post(); before=self.store.read_bytes()
        with mock.patch.object(board,'MAX_LOG_BYTES',len(before)):
            with self.assertRaises(ValueError):self.post()
        with mock.patch.object(board.fcntl,'flock',side_effect=BlockingIOError), mock.patch.object(board,'LOCK_TIMEOUT',0):
            with self.assertRaises(OSError):board.list_messages(self.store)
        self.assertEqual(before,self.store.read_bytes())

    def test_topic_threads_inbox_ownership_status_and_search(self):
        question = self.post(topic='Review approach', kind='question', message='Who can check the API?')
        root = question['thread_id']
        self.assertEqual(question['id'], root)
        self.assertEqual(root, board.list_threads(self.store, inbox=True)[0]['id'])
        claimed = self.post(thread=root, task='review', kind='ownership', owner='reviewer', status='waiting')
        self.assertEqual(root, claimed['reply_to'])
        self.assertEqual([], board.list_threads(self.store, inbox=True))
        summary = board.list_threads(self.store, project='example-app', status='waiting', search='API')[0]
        self.assertEqual(('reviewer', 2), (summary['owner'], summary['count']))
        reply = self.post(reply_to=claimed['id'], task='follow-up', status='resolved')
        self.assertEqual(('reviewer', root), (reply['owner'], reply['thread_id']))
        self.assertEqual([reply, claimed, question], board.list_messages(self.store, thread=root))
        self.assertEqual([question], board.list_messages(self.store, thread=root, search='API'))
        self.post(thread=root, status='open', unowned=True)
        self.assertEqual(1, len(board.list_threads(self.store, inbox=True)))
        with self.assertRaises(ValueError): self.post(thread=root, project='other')
        with self.assertRaises(ValueError): self.post(thread=root, topic='Different topic')
        with self.assertRaises(ValueError): self.post(thread='0'*32)
        with self.assertRaises(ValueError): self.post(status='approved')

    def test_same_topic_is_one_thread_even_with_simultaneous_posts(self):
        def writer(number):
            return subprocess.run([sys.executable, str(ROOT/'agent_messages.py'), '--store', str(self.store),
                'post', '--author', 'worker', '--task', f'task-{number}', '--project', 'example-app',
                '--topic', 'Shared question', '--kind', 'question', '--owner-visible'],
                input=f'Question detail {number}', text=True, capture_output=True, timeout=15)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = list(pool.map(writer, range(12)))
        self.assertTrue(all(p.returncode == 0 for p in outcomes), [p.stderr for p in outcomes])
        summaries = board.list_threads(self.store, inbox=True)
        self.assertEqual(1, len(summaries)); self.assertEqual(12, summaries[0]['count'])
        self.assertEqual(1, len({r['thread_id'] for r in board.list_messages(self.store)}))
        self.post(topic='Separate topic', project='other')
        result = subprocess.run([sys.executable, str(ROOT/'agent_messages.py'), '--store', str(self.store),
            'threads', '--inbox', '--project', 'example-app', '--search', 'question', '--limit', '1'], text=True, capture_output=True)
        self.assertEqual(0, result.returncode); self.assertEqual(12, json.loads(result.stdout)['count'])

    def test_legacy_records_remain_readable_and_new_replies_preserve_them(self):
        current = self.post()
        legacy = {k:v for k,v in current.items() if k not in board.THREAD_FIELDS}; legacy['schema'] = 1
        self.store.write_text(json.dumps(legacy)+'\n'); prior = self.store.read_bytes()
        reply = self.post(thread=legacy['id'], owner='reviewer')
        self.assertTrue(self.store.read_bytes().startswith(prior))
        self.assertEqual([reply, legacy], board.list_messages(self.store))
        self.assertEqual('reviewer', board.list_threads(self.store)[0]['owner'])
        for changes in [dict(thread_id='0'*32), dict(topic='Changed'), dict(project='other')]:
            self.store.write_bytes(prior + (json.dumps(dict(reply, **changes))+'\n').encode())
            with self.assertRaises(ValueError): board.list_messages(self.store)

    def test_render_groups_threads_and_bounds_conversation_history(self):
        root = self.post(topic='Unowned question', kind='question')
        for n in range(7): self.post(thread=root['id'], message=f'Update number {n}')
        self.post(topic='Owned discussion', project='Other project', owner='reviewer')
        page = board.render(self.store)
        self.assertIn('Shared inbox · unowned', page)
        self.assertIn('Discussion owner: reviewer', page)
        self.assertIn('<h3>Other project</h3>', page)
        self.assertIn('Thread ID:', page)
        self.assertIn('latest five messages', page)
        self.assertNotIn('Update number 0', page)
        self.assertIn('Update number 6', page)
        self.assertNotIn('<form', page)

    def test_legacy_cross_project_reply_remains_readable_and_appendable(self):
        current = self.post()
        root = {k:v for k,v in current.items() if k not in board.THREAD_FIELDS}; root['schema'] = 1
        reply = dict(root, id='a'*32, reply_to=root['id'], project='Other project')
        self.store.write_text(json.dumps(root)+'\n'+json.dumps(reply)+'\n'); prior = self.store.read_bytes()
        self.assertEqual([reply, root], board.list_messages(self.store))
        self.assertEqual(2, board.list_threads(self.store)[0]['count'])
        self.assertIn('Original project: Other project', board.render(self.store))
        new = self.post(thread=root['id'], owner='reviewer')
        self.assertTrue(self.store.read_bytes().startswith(prior))
        self.assertEqual([new, reply, root], board.list_messages(self.store))

if __name__ == '__main__': unittest.main()
