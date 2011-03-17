from epsilon.scripts.benchmark import start, stop

from xquotient.inbox import InboxScreen
from xquotient.benchmarks.inbox_tools import N_LOOKUPS, VIEWS, createInboxWithManyMessages

def main():
    inbox = createInboxWithManyMessages()
    screen = InboxScreen(inbox)

    start()
    for i in xrange(N_LOOKUPS):
        for v in VIEWS:
            screen.changeView(v)
            screen.getLastMessage()
    stop()


if __name__ == '__main__':
    main()
