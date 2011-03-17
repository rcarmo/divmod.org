from axiom.test.historic import stubloader
from xquotient.test.historic.stub_message1to2 import attrs
from xquotient.exmess import Message, DEFERRED_STATUS
from xquotient.mimestorage import Part

ignore = object()

class MessageUpgradeTest(stubloader.StubbedTest):
    def testUpgrade(self):
        m = self.store.findUnique(Message)
        for (k, v) in attrs.iteritems():
            new = getattr(m, k, ignore)
            if new is not ignore:
                self.assertEquals(v, new)
        self.assertIdentical(self.store.findUnique(Part), m.impl)
        self.failIf(m.hasStatus(DEFERRED_STATUS))
