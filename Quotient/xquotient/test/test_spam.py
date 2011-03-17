
from decimal import Decimal

from zope.interface import implements

from twisted.trial.unittest import TestCase

from axiom.store import Store
from axiom.item import Item
from axiom.attributes import boolean, inmemory, integer
from axiom.dependency import installOn

from xquotient.iquotient import IHamFilter
from xquotient.spam import Filter
from xquotient.mimestorage import Part
from xquotient.exmess import (Message, _TrainingInstruction, SPAM_STATUS,
                              TRAINED_STATUS, CLEAN_STATUS)

from xquotient.test.test_workflow import FakeScheduler
from xquotient.test.util import DummyMessageImplementation




class TestFilter(Item):
    """
    Ultra stupid classifier.  Always classifies every message as whatever you
    tell it to at creation time.
    """
    implements(IHamFilter)

    powerupInterfaces = (IHamFilter,)

    result = boolean(default=False, allowNone=False)
    test = inmemory()

    forgotTraining = boolean(default=False)

    trainCount = integer(default=0)

    def classify(self, item):
        return self.result, 0

    def forgetTraining(self):
        self.forgotTraining = True

    def train(self, spam, message):
        self.trainCount += 1
        # We're only ever called in the context of retraining, so let's make
        # sure that what we're being told matches the message that we've been
        # given.
        if spam:
            self.test.failUnless(message.hasStatus(SPAM_STATUS))
        else:
            self.test.failUnless(message.hasStatus(CLEAN_STATUS))
        self.test.failUnless(message.hasStatus(TRAINED_STATUS))

def _spamState(messageObject, spamFlag, trainFlag):
    """
    Call methods to train or classify as spam or clean based on a pair of flags.

    @param spamFlag: a flag indicating whether this message

    @param trainFlag: a flag, true if the message should be trained, false if
    it should be classified.
    """
    # XXX the fact that I needed to write this method worries me... It bothers
    # me that such a method was necessary, but it only seems helpful from the
    # tests.  In the actual application code I found I did want to use the
    # separate methods provided.  If we start running into that use-case in
    # application code we should revisit it.  There's no ticket yet because
    # it's not clear that cleaning this up is necessary or desirable. --glyph

    methodName = ''
    if trainFlag:
        methodName += 'train'
    else:
        methodName += 'classify'
    if spamFlag:
        methodName += 'Spam'
    else:
        methodName += 'Clean'
    getattr(messageObject, methodName)()

class FilterTestCase(TestCase):

    def fakeSchedule(self, runnable, when):
        pass


    def setUp(self):
        self.store = Store()
        self.scheduler = FakeScheduler(store=self.store, test=self)
        installOn(self.scheduler, self.store)

    def test_postiniHeaderParsing(self):
        """
        Test that Postini's spam levels header can be parsed and structured
        data extracted from it.
        """
        f = Filter()
        self.assertEquals(
            f._parsePostiniHeader(
                '(S:99.9000 R:95.9108 P:91.9078 M:100.0000 C:96.6797 )'),
            {'S': Decimal('99.9'),
             'R': Decimal('95.9108'),
             'P': Decimal('91.9078'),
             'M': Decimal('100'),
             'C': Decimal('96.6797')})
        self.assertEquals(
            f._parsePostiniHeader(
                '(S: 0.0901 R:95.9108 P:95.9108 M:99.5542 C:79.5348 )'),
            {'S': Decimal('.0901'),
             'R': Decimal('95.9108'),
             'P': Decimal('95.9108'),
             'M': Decimal('99.5542'),
             'C': Decimal('79.5348')})
        self.assertEquals(
            f._parsePostiniHeader(
            '(S:99.90000/99.90000 R:95.9108 P:95.9108 M:97.0282 C:98.6951 )'),
            {'S': Decimal('99.9'),
             'R': Decimal('95.9108'),
             'P': Decimal('95.9108'),
             'M': Decimal('97.0282'),
             'C': Decimal('98.6951')})

    def test_retrain(self):
        """
        Verify that retraining a few messages will tell our new test filter to
        learn about a bunch of new messages.
        """
        f = Filter(store=self.store)
        installOn(f, self.store)
        tf = TestFilter(store=self.store, test=self)
        installOn(tf, self.store)
        COUNT = 10
        for j in range(2):
            for x in range(COUNT):
                msg = Message.createIncoming(
                    self.store,
                    DummyMessageImplementation(store=self.store),
                    u'test://retrain')
                _spamState(msg, (x % 2), j)

        # This isn't quite correct.  We're relying on the fact that the batch
        # processor is supposed to run in a subprocess (which isn't going) so
        # the callback is only going to be triggered for our set of messages
        # during the test.  Bleah.

        def _(ign):
            self.assertEquals(tf.trainCount, COUNT)
        return f.retrain().addCallback(_)

    def test_reclassify(self):
        """
        Verify that reclassification will start classifying from the beginning
        of the inbox again.
        """
        # Didn't write a test for this because I wasn't changing the code, but
        # I did notice it wasn't covered.
        self.fail()

    test_reclassify.todo = "Write a test for this."

    def test_postiniHeaderWithWhitespace(self):
        """
        Test that a Postini header with leading or trailing whitespace can
        also be parsed correctly.  Headers like this probably shouldn't ever
        show up, but investigation of old messages indicates they seem to
        sometimes.
        """
        f = Filter()
        self.assertEquals(
            f._parsePostiniHeader(
                '  (S:99.9000 R:95.9108 P:91.9078 M:100.0000 C:96.6797 )  \r'),
            {'S': Decimal('99.9'),
             'R': Decimal('95.9108'),
             'P': Decimal('91.9078'),
             'M': Decimal('100'),
             'C': Decimal('96.6797')})


    def _messageWithPostiniHeader(self, header):
        part = Part()
        part.addHeader(u'X-pstn-levels', unicode(header))
        msg = Message(store=self.store)
        # part._addToStore(self.store, msg, None)
        part.associateWithMessage(msg)
        msg.impl = part
        return msg


    def test_postiniHeaderSpamFiltering(self):
        """
        Test that if a message has a low enough spam level in a Postini
        C{X-pstn-levels} header and the Filter has been configured to use it,
        it is classified as spam.
        """
        msg = self._messageWithPostiniHeader(
            u'(S: 0.9000 R:95.9108 P:91.9078 M:100.0000 C:96.6797 )')
        f = Filter(usePostiniScore=True, postiniThreshhold=1.0)
        f.processItem(msg)
        self.failUnless(msg.hasStatus(SPAM_STATUS))


    def test_postiniHeaderHamFiltering(self):
        """
        Test that if a message has a high enough spam level in a Postini
        C{X-pstn-levels} header and the Filter has been configured to use it,
        it is classified as ham.
        """
        msg = self._messageWithPostiniHeader(
            u'(S:90.9000 R:95.9108 P:91.9078 M:100.0000 C:96.6797 )')
        f = Filter(store=self.store, usePostiniScore=True, postiniThreshhold=1.0)
        installOn(f, self.store)
        f.processItem(msg)
        self.failIf(msg.hasStatus(SPAM_STATUS))


    def test_disablePostiniSpamFiltering(self):
        """
        Test that if C{usePostiniScore} is False the header is ignored and
        another filter is consulted.
        """
        msg = self._messageWithPostiniHeader(
            u'(S:90.9000 R:95.9108 P:91.9078 M:100.0000 C:96.6797 )')
        f = Filter(store=self.store, usePostiniScore=False, postiniThreshhold=None)
        tf = TestFilter(store=self.store, result=True)
        installOn(tf, self.store)
        f.processItem(msg)
        self.failUnless(msg.hasStatus(SPAM_STATUS))


    def test_disablePostiniHamFiltering(self):
        """
        Test that if C{usePostiniScore} is False the header is ignored and
        another filter is consulted.
        """
        msg = self._messageWithPostiniHeader(
            u'(S: 0.9000 R:95.9108 P:91.9078 M:100.0000 C:96.6797 )')
        f = Filter(store=self.store, usePostiniScore=False, postiniThreshhold=None)
        installOn(TestFilter(store=self.store, result=False), self.store)
        f.processItem(msg)
        self.failIf(msg.hasStatus(SPAM_STATUS))


    def test_postiniRespectsTraining(self):
        """
        If a user trains a message as ham or spam, the postini code should not
        clobber that value, even though postini is not really trainable itself.
        """
        msg = self._messageWithPostiniHeader(
            u'(S:99.9000 R:95.9108 P:91.9078 M:100.0000 C:96.6797 )')
        msg.trainSpam()
        f = Filter(store=self.store, usePostiniScore=True, postiniThreshhold=1.0)
        f.processItem(msg)
        self.failUnless(msg.hasStatus(SPAM_STATUS))
        self.failIf(msg.shouldBeClassified)


    def test_processTrainingInstructions(self):
        """
        When a user trains a message, a _TrainingInstruction item gets
        created to signal the batch processor to do the training. Make
        that gets run OK.
        """
        f = Filter(store=self.store, usePostiniScore=True, postiniThreshhold=1.0)
        ti = _TrainingInstruction(store=self.store, spam=True)
        f.processItem(ti)


    def test_postiniWithoutHeaderSpamFiltering(self):
        """
        Check that when postini filtering is enabled but a message has no
        postini header then the other filter is consulted.
        """
        msg = Message.createIncoming(
            self.store,
            Part(),
            u'test://postiniWithoutHeaderSpamFiltering')
        f = Filter(store=self.store, usePostiniScore=True, postiniThreshhold=1.0)
        tf = TestFilter(store=self.store, result=True)
        installOn(tf, self.store)
        self.failUnlessEquals(len(list(f._filters())),  1)
        f.processItem(msg)
        self.assertIn(SPAM_STATUS, list(msg.iterStatuses()))


    def test_postiniWithoutHeaderHamFiltering(self):
        """
        Check that when postini filtering is enabled but a message has no
        postini header then the other filter is consulted.
        """
        msg = Message.createIncoming(
            self.store,
            Part(),
            u'test://postiniWithoutHeaderHamFiltering')
        f = Filter(store=self.store, usePostiniScore=True, postiniThreshhold=1.0)
        installOn(TestFilter(store=self.store, result=False), self.store)
        f.processItem(msg)
        self.assertNotIn(SPAM_STATUS, list(msg.iterStatuses()))
