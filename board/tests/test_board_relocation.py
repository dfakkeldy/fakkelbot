import inspect
from pathlib import Path
from unittest import mock
import unittest

import agent_board_remote as api
import test_board_prefix as fixtures


class BoardRelocationTests(unittest.TestCase):
    setUp = fixtures.BoardPrefixTests.setUp
    post = fixtures.BoardPrefixTests.post

    def destination(self, events):
        remote = api.GitRemote(self.root/'destination-cache', str(self.root/'destination.git'),
                               verify=lambda: None, prefix='coordination')
        import subprocess
        subprocess.run(['git','init','--bare','--initial-branch=main',str(self.root/'destination.git')],
                       check=True,capture_output=True)
        remote.fetch()
        if events:remote.publish(None, events)
        return remote

    def routing(self):
        path = self.root/'messages.jsonl'
        api._atomic(path, b'frozen legacy recovery\n')
        api._atomic(api.marker(path), api._bytes({'schema':1,'root':str(self.a.root)}))
        return path

    def relocate(self, path, remote, source=None, source_head=None):
        self.assertTrue(hasattr(api, 'relocate'), 'explicit lossless route relocation is required')
        with mock.patch.object(api, 'configured', return_value=source or self.a):
            return api.relocate(path, 'example/consolidated', prefix='coordination',
                                source_head=source_head, remote=remote)

    def test_relocation_keeps_old_recovery_and_queued_records_then_syncs_once(self):
        first=self.post();self.a.sync()
        source_head=self.a.status()['head']
        target=self.destination(self.a.remote.fetch()[1])
        queued=self.post(message='An offline message to preserve.')
        path=self.routing()
        before={p.relative_to(self.a.root).as_posix():p.read_bytes() for p in self.a.root.rglob('*')
                if p.is_file() and 'git' not in p.relative_to(self.a.root).parts}
        moved=self.relocate(path,target,source_head=source_head)
        self.assertNotEqual(self.a.root,moved.root)
        self.assertEqual('example/consolidated',moved.repository)
        self.assertEqual('coordination',moved.prefix)
        self.assertEqual(1,moved.status()['queued'])
        self.assertEqual({first['id'],queued['id']},{r['id'] for r in moved.records()})
        self.assertEqual(b'frozen legacy recovery\n',path.read_bytes())
        for relative,data in before.items():self.assertEqual(data,(self.a.root/relative).read_bytes(),relative)
        self.assertEqual(str(moved.root),api._json(api.marker(path))['root'])
        moved.sync()
        self.assertEqual(0,moved.status()['queued'])
        self.assertEqual(2,len(target.fetch()[1]))
        repeated=self.relocate(path,target,source=moved,source_head=source_head)
        self.assertEqual(moved.root,repeated.root)
        self.assertEqual(2,len(target.fetch()[1]))

    def test_relocation_refuses_missing_history_without_switching_route(self):
        self.post();self.a.sync();path=self.routing();before=api._read(api.marker(path))
        target=self.destination([])
        with self.assertRaises(ValueError):self.relocate(path,target,source_head=self.a.status()['head'])
        self.assertEqual(before,api._read(api.marker(path)))
        self.assertEqual(1,self.a.status()['synced'])

    def test_relocation_requires_the_reviewed_source_revision(self):
        self.post();self.a.sync();path=self.routing();before=api._read(api.marker(path))
        target=self.destination(self.a.remote.fetch()[1])
        self.post();self.a.sync()
        with self.assertRaises(ValueError):self.relocate(path,target,source_head='0'*40)
        self.assertEqual(before,api._read(api.marker(path)))

    def test_stale_configured_writer_cannot_append_to_old_route_after_switch(self):
        self.post();self.a.sync();path=self.routing()
        self.a.routing_path=path
        target=self.destination(self.a.remote.fetch()[1])
        self.relocate(path,target,source_head=self.a.status()['head'])
        with self.assertRaisesRegex(ValueError,'route|routing'):
            self.post(message='This stale writer must reload its route.')
        self.assertEqual(0,self.a.status()['queued'])
