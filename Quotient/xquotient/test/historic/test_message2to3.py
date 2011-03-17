from axiom.test.historic import stubloader
from xquotient.test.historic.stub_message1to2 import attrs
from xquotient.exmess import Message, EVER_DEFERRED_STATUS
from xquotient.mimestorage import Part

ignored = object()

class MessageUpgradeTest(stubloader.StubbedTest):
    def testUpgrade(self):
        m = self.store.findUnique(Message)
        for (k, v) in attrs.iteritems():
            newv = getattr(m, k, ignored)
            if newv is not ignored:
                self.assertEquals(v, newv)
        self.assertIdentical(self.store.findUnique(Part), m.impl)
        self.failIf(m.hasStatus(EVER_DEFERRED_STATUS))
