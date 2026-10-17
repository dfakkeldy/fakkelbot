import inspect
from pathlib import Path
import subprocess
import tempfile
import unittest

import agent_board_remote as api
import test_agent_board_remote as fixtures


class BoardPrefixTests(unittest.TestCase):
    git_tree = fixtures.RemoteBoardTests.git_tree
    fixture_commit = fixtures.RemoteBoardTests.fixture_commit
    post = fixtures.RemoteBoardTests.post

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.remote_path = self.root / 'remote.git'
        subprocess.run(['git', 'init', '--bare', '--initial-branch=main', str(self.remote_path)],
                       check=True, capture_output=True)
        self.api = api
        api.initialize(self.root / 'legacy', 'example/kit')
        remote = api.GitRemote(self.root / 'legacy/git', str(self.remote_path), verify=lambda: None)
        self.a = api.RemoteBoard(self.root / 'legacy', remote=remote)

    def prefixed_client(self, name='namespaced'):
        self.assertIn('prefix', inspect.signature(api.initialize).parameters,
                      'board initialization must support a data prefix')
        self.assertIn('prefix', inspect.signature(api.GitRemote).parameters,
                      'Git event reads and writes must use the same prefix')
        root = self.root / name
        api.initialize(root, 'example/kit', prefix='coordination')
        remote = api.GitRemote(root / 'git', str(self.remote_path), verify=lambda: None,
                               prefix='coordination')
        return api.RemoteBoard(root, remote=remote)

    def test_namespaced_board_preserves_starter_kb_and_root_events(self):
        original = self.post()
        self.a.sync()
        self.fixture_commit({'README.md': b'# Starter kit\n',
                             'kb/bundle/index.md': b'# Private knowledge\n',
                             'bots/audy.md': b'# Audy\n'})
        before = self.git_tree()
        client = self.prefixed_client()
        self.assertEqual([], client.remote.fetch()[1], 'root events belong to the legacy board')
        item = self.post(client, message='A scoped coordination note.')
        client.sync()
        after = self.git_tree()
        for path, value in before.items():
            self.assertEqual(value, after[path], path)
        self.assertIn('coordination/README.md', after)
        self.assertIn('coordination/events/' + item['id'] + '.json', after)
        self.assertIn('coordination/topics/' + item['id'] + '.md', after)
        self.assertEqual([item['id']], [e['id'] for e in client.remote.fetch()[1]])
        self.assertIn('events/' + original['id'] + '.json', after)
        self.assertEqual(1, client.remote.validate_views(client.status()['head'])['messages'])
        self.assertEqual('coordination', client.prefix)

    def test_namespaced_publication_keeps_old_event_bytes_and_relative_links(self):
        client = self.prefixed_client()
        first = self.post(client, kind='question')
        client.sync()
        before = self.git_tree()
        base = client.status()['head']
        self.post(client, thread=first['id'], message='A reply on the same thread.')
        client.sync()
        after = self.git_tree()
        event_path = 'coordination/events/' + first['id'] + '.json'
        self.assertEqual(before[event_path], after[event_path])
        self.assertIn('topics/' + first['id'] + '.md', after['coordination/README.md'].decode())
        self.assertIn('../events/' + first['id'] + '.json', after['coordination/topics/' + first['id'] + '.md'].decode())
        self.assertEqual(2, client.remote.validate_views(client.status()['head'], base=base)['messages'])
        other = self.prefixed_client('reader')
        other.sync(publish=False)
        self.assertEqual(client.records(), other.records())

    def test_prefix_validation_rejects_escape_and_ambiguous_paths(self):
        self.assertIn('prefix', inspect.signature(api.initialize).parameters)
        for index, prefix in enumerate(['../kb', '/coordination', 'coordination/', 'coordination//events',
                                       '.', 'coordination/..', '.github', 'a\\b', 'a\x00b', True]):
            with self.subTest(prefix=repr(prefix)), self.assertRaises(ValueError):
                api.initialize(self.root / ('bad-' + str(index)), 'example/kit', prefix=prefix)

    def test_schema_one_config_remains_legacy_root(self):
        self.assertIn('prefix', inspect.signature(api.GitRemote).parameters)
        config = self.a.root / 'config.json'
        api._atomic(config, api._bytes({'schema': 1, 'repository': 'example/kit'}))
        legacy = api.RemoteBoard(self.a.root, remote=self.a.remote)
        self.assertEqual('', legacy.prefix)
        item = self.post(legacy)
        legacy.sync()
        self.assertIn('events/' + item['id'] + '.json', self.git_tree())
        self.assertNotIn('coordination/README.md', self.git_tree())

    def test_route_specific_git_caches_do_not_reuse_legacy_tracking_history(self):
        client = self.prefixed_client()
        production = api.RemoteBoard(client.root)
        self.assertNotEqual(client.root / 'git', production.remote.root)
        self.assertIn('git-', production.remote.root.name)
        self.assertEqual(production.remote.root, api.RemoteBoard(client.root).remote.root)
