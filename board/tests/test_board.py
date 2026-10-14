import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import agent_messages
import board


class BoardWrapperTests(unittest.TestCase):
    def test_post_keeps_its_arguments_and_uses_the_workspace_store(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = Path(temp.name) / 'workspace' / 'messages.jsonl'
        default = Path(temp.name) / 'default' / 'messages.jsonl'
        argv = ['board.py', 'post', '--author', 'setup', '--task', 'first-setup', '--project', 'grok-bot-setup',
                '--topic', 'First setup', '--kind', 'update', '--owner-visible']

        with mock.patch.object(board, 'STORE', str(store)), \
                mock.patch.object(agent_messages, 'DEFAULT_PATH', default), \
                mock.patch.object(sys, 'argv', argv), \
                mock.patch.object(sys, 'stdin', io.StringIO('Setup finished.')), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, board.main())

        self.assertEqual([('First setup', 'setup', 'Setup finished.')],
                         [(t['topic'], t['last_author'], t['last_message']) for t in agent_messages.list_threads(store)])
        self.assertFalse(default.exists())


if __name__ == '__main__':
    unittest.main()
