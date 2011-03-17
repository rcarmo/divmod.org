
from zope.interface import implements

from twisted.application.service import IService
from twisted.trial.unittest import TestCase, SkipTest

from axiom.store import Store
from axiom.item import Item
from axiom.attributes import reference, inmemory

from nevow.testutil import renderLivePage

from xmantissa import ixmantissa
from xmantissa.fulltext import PyLuceneIndexer

from xquotient.quotientapp import MessageSearchProvider
from xquotient.exmess import Message, splitAddress
from xquotient.test.util import (MIMEReceiverMixin, PartMaker,
                                 ThemedFragmentWrapper)
from xquotient.extract import ExtractPowerup

def _checkForPyLucene(indexer):
    """
    Raise L{SkipTest} if PyLucene isn't available.
    """
    try:
        writer = indexer.openWriteIndex()
    except NotImplementedError:
        raise SkipTest("PyLucene not available")
    else:
        writer.close()


class MsgSearchTestCase(TestCase, MIMEReceiverMixin):
    def setUp(self):
        self.mimeReceiver = self.setUpMailStuff(
                             (MessageSearchProvider,))

        self.indexer = self.mimeReceiver.store.findUnique(PyLuceneIndexer)
        _checkForPyLucene(self.indexer)

    def _indexSomething(self, thing):
        writer = self.indexer.openWriteIndex()
        writer.add(thing)
        writer.close()

    def _makeSimpleMsg(self, bodyText):
        return self.mimeReceiver.feedStringNow(
                    PartMaker('text/plain', bodyText).make()).message

    def testBodySearch(self):
        """
        Test that we can search for tokens that appear in the body of an
        indexed message and get a meaningful result
        """
        msg = self._makeSimpleMsg(u'hello world')

        self._indexSomething(msg)

        reader = self.indexer.openReadIndex()
        self.assertEqual(list(reader.search(u'hello')), [msg.storeID])

    def testKeywordValuesInBodySearch(self):
        """
        Test that we can search for tokens that appear as the values of
        keywords of indexed messages, without specifying the keyword name, and
        get meaningful results
        """
        msg = self._makeSimpleMsg(u'')

        msg.subject = u'hello world'

        self._indexSomething(msg)

        reader = self.indexer.openReadIndex()
        self.assertEqual(list(reader.search(u'hello')), [msg.storeID])

    def testEmailAddressSplitter(self):
        """
        Ensure that we take an email address and break it on non-alphanumeric
        characters for indexing.
        """
        splitted = splitAddress('john.smith@alum.mit.edu')
        self.assertEqual(splitted, ['john', 'smith', 'alum', 'mit', 'edu'])

    def test_keywordSearch(self):
        """
        Test that we get the expected results when searching for messages by
        keyword name and value
        """
        msg = self._makeSimpleMsg(u'')

        msg.subject = u'hello world'
        msg.sender = u'foo@jethro.org'
        msg.senderDisplay = u'Fred Oliver Osgood'

        self._indexSomething(msg)

        reader = self.indexer.openReadIndex()
        self.assertEqual(list(reader.search(u'', {u'subject': u'world'})),
                         [msg.storeID])
        self.assertEqual(list(reader.search(u'', {u'from': u'foo'})),
                         [msg.storeID])
        self.assertEqual(list(reader.search(u'', {u'from': u'jethro'})),
                         [msg.storeID])
        self.assertEqual(list(reader.search(u'', {u'from': u'osgood'})),
                         [msg.storeID])



class ViewTestCase(TestCase, MIMEReceiverMixin):
    def setUp(self):
        self.mimeReceiver = self.setUpMailStuff(
            (MessageSearchProvider,), self.mktemp(), True)
        self.indexer = self.mimeReceiver.store.findUnique(PyLuceneIndexer)
        _checkForPyLucene(self.indexer)


    def testNoResults(self):
        """
        Test that the string 'no results' appears in the flattened HTML
        response to a search on an empty index
        """
        service = IService(self.indexer.store.parent)
        service.startService()

        def gotSearchResult((fragment,)):
            deferred = renderLivePage(ThemedFragmentWrapper(fragment))
            def rendered(res):
                self.assertIn('no results', res.lower())
                return service.stopService()
            return deferred.addCallback(rendered)

        s = self.indexer.store
        deferred = ixmantissa.ISearchAggregator(s).search(u'hi', {}, None, None)
        return deferred.addCallback(gotSearchResult)



class DummyIndexer(Item):
    """
    Stub L{ixmantissa,IFulltextIndexer} provider used to test that
    L{ixmantissa.IFulltextIndexer}s receive the appropriate notification if
    various events.
    """
    implements(ixmantissa.IFulltextIndexer)

    removed = inmemory()
    installedOn = reference()

    def activate(self):
        self.removed = []


    def remove(self, item):
        self.removed.append(item)



class DeletionTestCase(TestCase):
    """
    Tests for the interaction between message deletion and the indexer.
    """
    def setUp(self):
        """
        Create a Store with a Message in it.
        """
        self.store = Store()
        self.message = Message(store=self.store)


    def test_deletionNotification(self):
        """
        Test that when a Message is deleted, all L{ixmantissa.IFulltextIndexer}
        powerups on that message's store are notified of the event.
        """
        indexers = []
        for i in range(2):
            indexers.append(DummyIndexer(store=self.store))
            self.store.powerUp(indexers[-1], ixmantissa.IFulltextIndexer)
            self.assertEqual(indexers[-1].removed, [])

        self.message.deleteFromStore()

        for i in range(2):
            self.assertEqual(indexers[i].removed, [self.message])


    def test_deletionWithoutIndexers(self):
        """
        Test that deletion of a message can succeed even if there are no
        L{ixmantissa.IFulltextIndexer} powerups on the message's store.
        """
        self.message.deleteFromStore()
        self.assertEqual(list(self.store.query(Message)), [])
