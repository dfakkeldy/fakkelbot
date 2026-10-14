import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import agent_messages
import board


class BoardWrapperTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.store = Path(temp.name) / 'workspace' / 'messages.jsonl'
        self.default = Path(temp.name) / 'default' / 'messages.jsonl'

    def run_board(self, *args, stdin=''):
        out = io.StringIO()
        with mock.patch.object(board, 'STORE', str(self.store)), \
                mock.patch.object(agent_messages, 'DEFAULT_PATH', self.default), \
                mock.patch.object(sys, 'argv', ['board.py', *args]), \
                mock.patch.object(sys, 'stdin', io.StringIO(stdin)), \
                contextlib.redirect_stdout(out):
            self.assertEqual(0, board.main())
        return [json.loads(line) for line in out.getvalue().splitlines()]

    def test_commands_keep_their_arguments_and_use_the_workspace_store(self):
        self.run_board('post', '--author', 'setup', '--task', 'first-setup', '--project', 'grok-bot-setup',
                       '--topic', 'First setup', '--kind', 'update', '--owner-visible', stdin='Setup finished.')
        threads = self.run_board('threads', '--project', 'grok-bot-setup', '--search', 'First setup', '--limit', '5')

        self.assertEqual([('First setup', 'setup', 'Setup finished.')],
                         [(t['topic'], t['last_author'], t['last_message']) for t in threads])
        self.assertEqual(['Setup finished.'], [m['message'] for m in agent_messages.list_messages(self.store)])
        self.assertFalse(self.default.exists())


if __name__ == '__main__':
    unittest.main()
