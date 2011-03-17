
"""
Create a axiom database configured with Quotient, a user with a POP3 grabber
and simulate a large number of downloaded messages.  Then test a large number
of UIDs to determine if they should be downloaded or not.
"""

import time

from epsilon import extime
from epsilon.scripts import benchmark

from xquotient import grabber
from xquotient.benchmarks import benchmark_initialize

class Message(object):
    sentWhen = extime.Time()
    archived = False

FACTOR = 1

def main():
    s, userStore = benchmark_initialize.initializeStore()

    g = grabber.POP3Grabber(
        store=userStore,
        username=u'testuser',
        password=u'password',
        domain=u'127.0.0.1',
        port=12345)

    def createPOP3UIDs():
        msg = Message()
        for i in xrange(10000 * FACTOR):
            g.markSuccess(str(i), msg)
    userStore.transact(createPOP3UIDs)

    def filterPOP3UIDs():
        for i in xrange(20000 * FACTOR / 100):
            r = xrange(i * 100, i * 100 + 100)
            g.shouldRetrieve(list(enumerate(map(str, r))))
    benchmark.start()
    userStore.transact(filterPOP3UIDs)
    benchmark.stop()


if __name__ == '__main__':
    main()
