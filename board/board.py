import sys

import agent_messages

STORE = '/workspace/.agent-board/messages.jsonl'


def main() -> int:
    sys.argv[1:1] = ['--store', STORE]
    return agent_messages.main()


if __name__ == '__main__': raise SystemExit(main())
