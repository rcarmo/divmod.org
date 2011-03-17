from axiom.test.historic import stubloader
from xquotient.spam import Filter
from xquotient.mail import MessageSource
from xquotient.exmess import _TrainingInstructionSource

class FilterTest(stubloader.StubbedTest):
    def testUpgrade(self):
        f = self.store.findUnique(Filter)
        self.failUnless(isinstance(f.messageSource, MessageSource))
        self.failUnless(isinstance(f.tiSource, _TrainingInstructionSource))
