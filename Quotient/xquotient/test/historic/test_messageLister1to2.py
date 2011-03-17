from axiom.test.historic.stubloader import StubbedTest
from xquotient.qpeople import MessageLister
from xmantissa.people import Organizer

class MessageListerUpgradeTestCase(StubbedTest):
    def testUpgrade(self):
        self.assertIdentical(self.store.findUnique(MessageLister).organizer,
                             self.store.findUnique(Organizer))
