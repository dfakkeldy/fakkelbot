import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import agent_messages as messages


class RemoteBoardTests(unittest.TestCase):
    def fixture_commit(self, changes):
        head=self.a.remote.fetch()[0]
        env={'GIT_INDEX_FILE':str(self.root/'fixture-index'),
             'GIT_AUTHOR_NAME':'fixture','GIT_COMMITTER_NAME':'fixture',
             'GIT_AUTHOR_EMAIL':'fixture@example.test','GIT_COMMITTER_EMAIL':'fixture@example.test'}
        self.a.remote._git('read-tree',head,env=env)
        for path,data in changes.items():
            if data is None:self.a.remote._git('update-index','--index-info',input=f'0 {"0"*40}\t{path}\n'.encode(),env=env)
            else:
                sha=self.a.remote._git('hash-object','-w','--stdin',input=data).stdout.decode().strip()
                self.a.remote._git('update-index','--add','--cacheinfo',f'100644,{sha},{path}',env=env)
        tree=self.a.remote._git('write-tree',env=env).stdout.decode().strip()
        commit=self.a.remote._git('commit-tree',tree,'-p',head,input=b'fixture\n',env=env).stdout.decode().strip()
        self.a.remote._git('push',str(self.remote_path),f'{commit}:refs/heads/main')
        return head,commit

    def test_revision_validator_accepts_complete_views_and_cli_does_not_write(self):
        import sys
        self.post(kind='question');self.a.sync()
        self.assertTrue(hasattr(self.a.remote,'validate_views'),'read-only snapshot validator required')
        base=self.a.status()['head'];self.post(topic='Another');self.a.sync()
        head=self.a.status()['head'];before=self.git_tree()
        report=self.a.remote.validate_views(head,base=base)
        self.assertEqual(2,report['messages'])
        result=subprocess.run([sys.executable,self.api.__file__,'validate','--git-dir',
                               str(self.remote_path),'--head','main','--base',base],
                              text=True,capture_output=True,timeout=15)
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertEqual(head,json.loads(result.stdout)['head'])
        self.assertEqual(before,self.git_tree())

    def test_validator_detects_old_client_stale_views_and_missing_links(self):
        self.post();self.a.sync()
        self.assertTrue(hasattr(self.a.remote,'validate_views'),'read-only snapshot validator required')
        self.post(topic='Old client post');event=self.api._json(next((self.a.root/'outbox').iterdir()))
        _,head=self.fixture_commit({f"events/{event['id']}.json":self.api._bytes(event)})
        with self.assertRaisesRegex(ValueError,'stale|Generated'):
            self.a.remote.validate_views(head)
        _,head=self.fixture_commit({'README.md':b'[Broken](topics/missing.md)\n'})
        with self.assertRaises(ValueError):self.a.remote.validate_views(head)

    def test_validator_rejects_rewritten_bytes_even_when_regenerated_views_match(self):
        item=self.post();self.a.sync()
        self.assertTrue(hasattr(self.a.remote,'validate_views'),'read-only snapshot validator required')
        path=f"events/{item['id']}.json";original=self.git_tree()[path]
        base,head=self.fixture_commit({path:json.dumps(json.loads(original),indent=2).encode()})
        with self.assertRaisesRegex(ValueError,'history'):
            self.a.remote.validate_views(head,base=base)

    def test_validator_rejects_removed_history_and_cli_returns_nonzero(self):
        import sys
        item=self.post();self.a.sync()
        self.assertTrue(hasattr(self.a.remote,'validate_views'),'read-only snapshot validator required')
        base,head=self.fixture_commit({f"events/{item['id']}.json":None})
        with self.assertRaisesRegex(ValueError,'history'):
            self.a.remote.validate_views(head,base=base)
        result=subprocess.run([sys.executable,self.api.__file__,'validate','--git-dir',
                               str(self.remote_path),'--head','main','--base',base],
                              text=True,capture_output=True,timeout=15)
        self.assertNotEqual(0,result.returncode)
        self.assertNotIn('Traceback',result.stderr)

    def git_tree(self, revision='main'):
        paths=subprocess.check_output(['git','--git-dir',str(self.remote_path),
                                       'ls-tree','-r','--name-only',revision],text=True).splitlines()
        return {p:subprocess.check_output(['git','--git-dir',str(self.remote_path),
                                          'show',f'{revision}:{p}']) for p in paths}

    def test_generated_directory_links_full_thread_and_preserves_event_bytes(self):
        first=self.post(kind='question',topic='Shared ideas',message='Could this help another project?')
        self.a.sync();before=self.git_tree()
        self.assertIn('README.md',before,'message publication must generate navigation')
        reply=self.post(thread=first['id'],message='A connection worth investigating.')
        self.a.sync();after=self.git_tree()
        self.assertEqual(before[f"events/{first['id']}.json"],after[f"events/{first['id']}.json"])
        page=after[f"topics/{first['id']}.md"].decode()
        self.assertIn('Could this help another project',page)
        self.assertIn('A connection worth investigating',page)
        self.assertIn(f"id=\"message-{reply['id']}\"",page)
        self.assertIn(f"#message-{first['id']}",page)
        self.assertIn(f"topics/{first['id']}.md",after['README.md'].decode())
        self.assertIn('Event revision: `sha256:',page)
        self.assertEqual(1,len([p for p in after if p.startswith('projects/')]))

    def test_concurrent_publication_contains_both_duplicate_topic_pages(self):
        first=self.post(self.a,topic='Same topic',kind='question')
        second=self.post(self.b,topic='Same topic',kind='question')
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda c:c.sync(),[self.a,self.b]))
        files=self.git_tree()
        self.assertIn(f"topics/{first['id']}.md",files)
        self.assertIn(f"topics/{second['id']}.md",files)
        project=next(v.decode() for k,v in files.items() if k.startswith('projects/'))
        self.assertIn(first['id'],project);self.assertIn(second['id'],project)
        self.assertIn('Duplicate topic',project)

    def test_source_markdown_is_inert_and_paths_do_not_use_project_names(self):
        item=self.post(project='../projects/<script>',topic='[approve](javascript:evil)',
                       message='<img src=x onerror=evil>\n# Policy\n[execute](javascript:evil) `run`',
                       references=['https://example.test/a(b)[c]'])
        self.a.sync();files=self.git_tree()
        page=files[f"topics/{item['id']}.md"].decode()
        for raw in ('<img','<script>','[execute]','[approve]','`run`'):
            self.assertNotIn(raw,page)
        self.assertIn('&#60;img',page)
        self.assertIn('https://example.test/a%28b%29%5Bc%5D',page)
        self.assertTrue(all('..' not in p and '<' not in p for p in files))

    def test_preexisting_uppercase_and_whitespace_references_render_without_changing_events(self):
        old=self.post(references=['HTTPS://example.test/evidence','  https://example.test/other  '])
        event=self.api._json(next((self.a.root/'outbox').iterdir()))
        # A previously supported client could already have published this exact event.
        original=self.api._bytes(event)
        self.a.remote._prepare()
        blob=self.a.remote._git('hash-object','-w','--stdin',input=original).stdout.decode().strip()
        index=self.root/'old-client-index'
        env={'GIT_INDEX_FILE':str(index),'GIT_AUTHOR_NAME':'fixture','GIT_COMMITTER_NAME':'fixture',
             'GIT_AUTHOR_EMAIL':'fixture@example.test','GIT_COMMITTER_EMAIL':'fixture@example.test'}
        self.a.remote._git('read-tree','--empty',env=env)
        self.a.remote._git('update-index','--add','--cacheinfo',f"100644,{blob},events/{old['id']}.json",env=env)
        tree=self.a.remote._git('write-tree',env=env).stdout.decode().strip()
        commit=self.a.remote._git('commit-tree',tree,input=b'old client\n',env=env).stdout.decode().strip()
        self.a.remote._git('push',str(self.remote_path),f'{commit}:refs/heads/main')
        self.a.sync();self.post(topic='New publication');self.a.sync()
        files=self.git_tree()
        self.assertEqual(original,files[f"events/{old['id']}.json"])
        page=files[f"topics/{old['id']}.md"].decode()
        self.assertIn('(HTTPS://example.test/evidence)',page)
        self.assertIn('(https://example.test/other)',page)

    def test_open_questions_are_bounded_diverse_and_exclude_resolved(self):
        for n in range(7):self.post(project='busy',topic=f'Busy {n}',kind='question',message=f'Question {n}?')
        quiet=self.post(project='quiet',topic='Connection',kind='question',message='Older connection?')
        self.post(project='busy',topic='Newest',kind='question',message='Newest?')
        closed=self.post(project='closed',topic='Done',kind='question',status='resolved')
        self.a.sync();readme=self.git_tree()['README.md'].decode()
        entrance=readme.split('## Open questions across projects')[1].split('## Projects')[0]
        self.assertEqual(5,entrance.count('Full thread'))
        self.assertIn(quiet['id'],entrance);self.assertNotIn(closed['id'],entrance)
        self.assertIn('optional',entrance)
        self.assertIn('return later',entrance)

    def test_older_question_slot_rotates_on_new_events_and_refresh_does_not_publish(self):
        for n in range(8):self.post(project='busy',topic=f'Question {n}',kind='question')
        self.a.sync();before=self.git_tree();head=self.a.status()['head']
        self.b.sync(publish=False)
        self.post(self.b,topic='Offline',kind='question')
        self.b.sync(publish=False)
        self.assertEqual(before,self.git_tree())
        self.post(topic='Unrelated activity');self.a.sync()
        after=self.git_tree()
        self.assertNotEqual(head,self.a.status()['head'])
        def featured(files):return files['README.md'].decode().split('## Open questions across projects')[1].split('## Projects')[0]
        self.assertNotEqual(featured(before),featured(after))

    def test_generated_revision_is_deterministic_and_conflicts_are_visible(self):
        root=self.post(kind='question');self.a.sync();self.b.sync()
        self.post(self.a,thread=root['id'],status='resolved')
        self.post(self.b,thread=root['id'],status='waiting')
        self.a.sync();self.b.sync();self.a.sync()
        events=self.a.remote.fetch()[1]
        self.assertTrue(hasattr(self.api,'render_views'),'deterministic view renderer required')
        views=self.api.render_views(events)
        self.assertEqual(views,self.api.render_views(list(reversed(events))))
        self.assertIn('Conflicting discussion updates',views[f"topics/{root['id']}.md"].decode())
        self.assertEqual({k:v for k,v in self.git_tree().items() if not k.startswith('events/')},views)

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('agent_board_remote'),
                             'portable event store is not implemented')
        import agent_board_remote
        self.api = agent_board_remote
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.remote_path = self.root / 'remote.git'
        subprocess.run(['git', 'init', '--bare', '--initial-branch=main', str(self.remote_path)],
                       check=True, capture_output=True)
        self.a = self.client('a')
        self.b = self.client('b')

    def client(self, name):
        root = self.root / name
        self.api.initialize(root, 'example-org/agent-board')
        remote = self.api.GitRemote(root / 'git', str(self.remote_path), verify=lambda: None)
        return self.api.RemoteBoard(root, remote=remote)

    def post(self, client=None, **changes):
        values = dict(author='codex', task='board', project='example-app', kind='update',
                      message='Ordinary coordination.', references=[], owner_visible=True)
        values.update(changes)
        return (client or self.a).post(**values)

    def test_offline_queue_sync_and_repeat_preserve_identity(self):
        item = self.post()
        self.assertEqual(1, self.a.status()['queued'])
        self.a.sync()
        self.assertEqual(0, self.a.status()['queued'])
        head = self.a.status()['head']
        self.a.sync()
        self.assertEqual(head, self.a.status()['head'])
        self.b.sync()
        self.assertEqual([item['id']], [m['id'] for m in self.b.records()])

    def test_stale_reply_cannot_reset_new_owner_or_status(self):
        root = self.post(); self.a.sync(); self.b.sync()
        self.post(self.a, thread=root['id'], kind='ownership', owner='reviewer', status='waiting')
        self.a.sync()
        self.post(self.b, thread=root['id'], message='Reply from older offline snapshot.')
        self.b.sync(); self.a.sync()
        thread = messages._threads(self.a.records())[root['id']]
        self.assertEqual(('reviewer', 'waiting'), (thread['owner'], thread['status']))
        self.assertEqual(3, len(thread['messages']))

    def test_concurrent_status_updates_are_reported_without_lost_messages(self):
        root = self.post(); self.a.sync(); self.b.sync()
        first = self.post(self.a, thread=root['id'], status='waiting')
        second = self.post(self.b, thread=root['id'], status='resolved')
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda c:c.sync(), [self.a,self.b]))
        self.a.sync(); self.b.sync()
        self.assertEqual(self.a.records(), self.b.records())
        self.assertEqual(3, len(self.a.records()))
        self.assertEqual(1, self.a.status()['conflicts'])
        self.assertEqual({first['id'], second['id']}, {m['id'] for m in self.a.records()[1:]})
        self.post(self.a, thread=root['id'], status='open', message='Reconciled status.')
        self.a.sync(); self.b.sync()
        self.assertEqual('open', messages._threads(self.b.records())[root['id']]['status'])

    def test_concurrent_local_posts_and_remote_replies_are_lossless(self):
        root = self.post(); self.a.sync(); self.b.sync()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            posted = list(pool.map(lambda n:self.post(self.a if n%2 else self.b,
                thread=root['id'], task=f'worker-{n}', message=f'Reply {n}'), range(16)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda c:c.sync(), [self.a,self.b]))
        self.a.sync(); self.b.sync()
        self.assertEqual(17,len(self.a.records()))
        self.assertEqual(self.a.records(),self.b.records())
        self.assertEqual({x['id'] for x in posted}|{root['id']}, {x['id'] for x in self.a.records()})

    def test_uncertain_push_retry_does_not_duplicate(self):
        item = self.post()
        original = self.a.remote.publish
        def uncertain(*args):
            original(*args)
            raise OSError('Connection ended after accepted push')
        with mock.patch.object(self.a.remote,'publish',side_effect=uncertain):
            with self.assertRaises(OSError): self.a.sync()
        self.assertEqual(1,self.a.status()['queued'])
        self.a.sync(); self.b.sync()
        self.assertEqual(0,self.a.status()['queued'])
        self.assertEqual([item['id']],[r['id'] for r in self.b.records()])

    def test_unavailable_remote_keeps_cache_and_outbox(self):
        root = self.post(); self.a.sync()
        self.post(thread=root['id'])
        prior = self.a.records()
        with mock.patch.object(self.a.remote,'fetch',side_effect=OSError('Offline')):
            with self.assertRaises(OSError): self.a.sync()
        self.assertEqual(prior,self.a.records())
        self.assertEqual(1,self.a.status()['queued'])

    def test_same_topic_roots_created_offline_remain_explicit_separate_threads(self):
        x=self.post(self.a,topic='Shared question'); y=self.post(self.b,topic='Shared question')
        self.a.sync(); self.b.sync(); self.a.sync()
        self.assertEqual({x['thread_id'],y['thread_id']},set(messages._threads(self.a.records())))
        self.assertEqual(1,self.a.status()['duplicate_topics'])

    def test_invalid_remote_change_is_rejected_without_replacing_cache(self):
        self.post(); self.a.sync()
        before=self.a.records()
        head,events=self.a.remote.fetch()
        altered=json.loads(json.dumps(events)); altered[0]['record']['message']='Changed existing message'
        with mock.patch.object(self.a.remote,'fetch',return_value=(head,altered)):
            with self.assertRaises(ValueError): self.a.sync()
        self.assertEqual(before,self.a.records())

    def test_sensitive_input_is_rejected_before_queue(self):
        with self.assertRaises(ValueError):self.post(message='Private private@example.test')
        self.assertEqual(0,self.a.status()['queued'])

    def test_read_only_refresh_never_publishes_queued_data(self):
        self.post(self.a); self.a.sync()
        self.post(self.b,topic='Offline question')
        self.b.sync(publish=False)
        self.assertEqual(1,self.b.status()['queued'])
        self.assertEqual(2,len(self.b.records()))
        self.a.sync()
        self.assertEqual(1,len(self.a.records()))

    def test_background_reader_only_refreshes_and_stops(self):
        import threading
        observed=threading.Event()
        def refresh(*,publish):
            self.assertFalse(publish)
            observed.set()
        with mock.patch.object(messages,'_remote',return_value=self.a), mock.patch.object(self.a,'sync',side_effect=refresh):
            stop,worker=messages.start_readonly_refresh(self.root/'client.jsonl',interval=60)
            try:self.assertTrue(observed.wait(2))
            finally:stop.set();worker.join(2)
            self.assertFalse(worker.is_alive())

    def test_malformed_remote_is_a_bounded_validation_error(self):
        with self.assertRaises(ValueError):self.api._reduce([{'private_notes':'DO NOT DISPLAY'}])

    def test_remote_history_removal_keeps_last_valid_cache(self):
        self.post();self.a.sync();before=self.a.records()
        with mock.patch.object(self.a.remote,'fetch',return_value=(None,[])):
            with self.assertRaises(ValueError):self.a.sync()
        self.assertEqual(before,self.a.records())

    def connected_source(self):
        source=self.root/'new-client'/'messages.jsonl'
        with mock.patch.object(self.api,'RemoteBoard',return_value=self.a):
            self.api.connect(source,'example-org/agent-board')
        return source

    def test_connect_freezes_even_empty_source_against_legacy_writers(self):
        source=self.connected_source()
        self.assertEqual(b'',source.read_bytes())
        self.assertEqual(0o400,source.stat().st_mode&0o777)
        with self.assertRaises(PermissionError):os.open(source,os.O_RDWR|os.O_APPEND)

    def test_connect_routes_reads_and_writes_to_the_remote_board(self):
        source=self.connected_source()
        item=messages.post(source,author='codex',task='first',project='example-app',kind='question',
                           message='First question.',references=[],owner_visible=True)
        self.assertEqual(b'',source.read_bytes())
        self.assertEqual([item['id']],[m['id'] for m in messages.list_messages(source)])
        self.assertIn('1 queued',messages.render(source))
        self.a.sync();self.b.sync()
        self.assertEqual([item['id']],[m['id'] for m in self.b.records()])

    def test_connect_again_is_idempotent_and_another_repository_is_refused(self):
        source=self.connected_source()
        routing=self.api.marker(source).read_bytes()
        self.post();self.a.sync()
        with mock.patch.object(self.api,'RemoteBoard',return_value=self.a):
            self.assertEqual(1,self.api.connect(source,'example-org/agent-board').status()['synced'])
            with self.assertRaises(ValueError):self.api.connect(source,'example-org/other-board')
        self.assertEqual(routing,self.api.marker(source).read_bytes())

    def test_public_or_non_main_repository_is_refused_before_any_git_access(self):
        board=self.api.RemoteBoard(self.a.root)
        self.post(board)
        for answer in ({'private':False,'default_branch':'main'},{'private':True,'default_branch':'master'}):
            reply=subprocess.CompletedProcess([],0,stdout=json.dumps(answer).encode(),stderr=b'')
            with mock.patch.object(self.api.subprocess,'run',return_value=reply) as run:
                with self.assertRaisesRegex(ValueError,'private repository with main'):board.sync()
            self.assertEqual(1,run.call_count)
            self.assertEqual(['gh','api','repos/example-org/agent-board'],run.call_args.args[0][:3])
        self.assertEqual(1,board.status()['queued'])

    def test_connect_refuses_existing_messages_without_hiding_them(self):
        source=self.root/'new-client'/'messages.jsonl'
        old=messages.post(source,author='codex',task='old',project='example-app',kind='question',
                          message='Existing question.',references=[],owner_visible=True)
        with self.assertRaises(ValueError):self.api.connect(source,'example-org/agent-board')
        self.assertEqual([old],messages.list_messages(source))

    def test_new_nested_state_directories_are_private(self):
        root=self.root/'fresh'/'nested'/'remote'
        self.api.initialize(root,'example-org/agent-board')
        self.assertEqual(0o700,root.parent.stat().st_mode&0o777)
        self.assertEqual(0o700,root.parent.parent.stat().st_mode&0o777)

    def test_concurrent_offline_cli_processes_preserve_every_queued_id(self):
        import sys
        source=self.connected_source()
        old=self.post();self.a.sync()
        script=Path(messages.__file__)
        def writer(n):
            result=subprocess.run([sys.executable,str(script),'--store',str(source),'post',
                '--author','worker','--task',f'worker-{n}','--project','example-app','--thread',old['id'],
                '--owner-visible','--offline'],input=f'Offline reply {n}',text=True,capture_output=True,timeout=15)
            self.assertEqual(0,result.returncode,result.stderr)
            response=json.loads(result.stdout)
            self.assertEqual('queued',response['delivery'])
            return response['id']
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            ids=list(pool.map(writer,range(12)))
        self.assertEqual(12,len(set(ids)))
        self.assertEqual(12,self.a.status()['queued'])
        self.a.sync();self.b.sync()
        self.assertEqual(set(ids)|{old['id']},{m['id'] for m in self.b.records()})


if __name__ == '__main__': unittest.main()
