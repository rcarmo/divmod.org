
from twisted.trial import unittest

from axiom import store, userbase
from axiom.dependency import installOn

from xquotient import spam
from xquotient.test.test_dspam import MessageCreationMixin


class SpambayesFilterTestCase(unittest.TestCase, MessageCreationMixin):

    def setUp(self):
        dbdir = self.mktemp()
        self.store = s = store.Store(dbdir)
        ls = userbase.LoginSystem(store=s)
        installOn(ls, s)
        acc = ls.addAccount('username', 'dom.ain', 'password')
        ss = acc.avatars.open()
        self.df = spam.SpambayesFilter(store=ss)
        installOn(self.df, ss)
        self.f = self.df.filter

    def testMessageClassification(self):
        self.f.processItem(self._message())

    def testMessageTraining(self):
        m = self._message()
        self.df.classify(m)
        self.df.train(True, m)

    def test_messageRetraining(self):
        """
        Test that removing the training data and rebuilding it succeeds.
        """
        self.testMessageTraining()
        self.df.forgetTraining()

