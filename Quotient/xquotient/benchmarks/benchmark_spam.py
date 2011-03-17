
"""
Run a message through the Quotient spam classification interface a large number
of times.
"""

import StringIO

from epsilon.scripts import benchmark

from axiom import store, userbase

from xquotient import spam


class Message(object):
    def __init__(self):
        self.trained = False

    impl = property(lambda self: self)
    source = property(lambda self: self)

    def open(self):
        return StringIO.StringIO(
            'Hello world\r\n'
            'Goodbye.\r\n')

def main():
    s = store.Store("spam.axiom")
    # DSPAM requires a Store with a parent, since the parent has the global
    # training state.
    s.parent = s

    # xquotient.dspam requires an account name to work at all.
    account = userbase.LoginAccount(store=s)
    userbase.LoginMethod(store=s,
                         account=account,
                         localpart=u"testuser",
                         domain=u"example.com",
                         verified=True,
                         internal=False,
                         protocol=userbase.ANY_PROTOCOL)

    classifier = spam.Filter(store=s)
    # Don't install it because there's no MessageSource: it won't install,
    # but it works well enough like this for the benchmark.
    classifier.installedOn = s
    dspam = spam.DSPAMFilter(store=s).installOn(classifier)

    def process():
        for i in xrange(10000):
            classifier.processItem(Message())
    benchmark.start()
    s.transact(process)
    benchmark.stop()


if __name__ == '__main__':
    main()
