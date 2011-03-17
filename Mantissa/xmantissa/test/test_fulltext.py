

from zope.interface import implements

from twisted.trial import unittest
from twisted.application.service import IService
from twisted.internet.defer import gatherResults

from axiom import iaxiom, store, batch, item, attributes
from axiom.userbase import LoginSystem
from axiom.dependency import installOn
from axiom.errors import SQLError

from xmantissa import ixmantissa, fulltext


def identifiersFrom(hits):
    """
    Convert iterable of hits into list of integer unique identifiers.
    """
    return [int(h.uniqueIdentifier) for h in hits]


class IndexableThing(item.Item):
    implements(ixmantissa.IFulltextIndexable)

    _uniqueIdentifier = attributes.bytes()

    _textParts = attributes.inmemory()
    _keywordParts = attributes.inmemory()
    _documentType = attributes.inmemory()

    def uniqueIdentifier(self):
        return self._uniqueIdentifier


    def textParts(self):
        return self._textParts


    def keywordParts(self):
        return self._keywordParts


    def documentType(self):
        return self._documentType


    def sortKey(self):
        return self.uniqueIdentifier()



class FakeMessageSource(item.Item):
    """
    Stand-in for an item type returned from L{axiom.batch.processor}.  Doesn't
    actually act as a source of anything, just used to test that items are kept
    track of properly.
    """
    anAttribute = attributes.text(doc="""
    Nothing.  Axiom requires at least one attribute per item-type.
    """)

    added = attributes.inmemory()
    removed = attributes.inmemory()

    def activate(self):
        self.added = []
        self.removed = []


    def addReliableListener(self, what, style):
        self.added.append((what, style))


    def removeReliableListener(self, what):
        self.removed.append(what)



class IndexerTestsMixin:
    def createIndexer(self):
        raise NotImplementedError()


    def openWriteIndex(self):
        try:
            return self.indexer.openWriteIndex()
        except NotImplementedError, e:
            raise unittest.SkipTest(str(e))


    def openReadIndex(self):
        try:
            return self.indexer.openReadIndex()
        except NotImplementedError, e:
            raise unittest.SkipTest(str(e))


    def setUp(self):
        self.path = u'index'
        self.store = store.Store(filesdir=self.mktemp())
        self.indexer = self.createIndexer()



class FulltextTestsMixin(IndexerTestsMixin):
    """
    Tests for any IFulltextIndexer provider.
    """

    def testSources(self):
        """
        Test that multiple IBatchProcessors can be added to a RemoteIndexer and
        that an indexer can be reset, with respect to input from its sources.
        """
        firstSource = FakeMessageSource(store=self.store)
        secondSource = FakeMessageSource(store=self.store)
        self.indexer.addSource(firstSource)
        self.indexer.addSource(secondSource)

        self.assertEquals(firstSource.added, [(self.indexer, iaxiom.REMOTE)])
        self.assertEquals(secondSource.added, [(self.indexer, iaxiom.REMOTE)])

        self.assertEquals(
            list(self.indexer.getSources()),
            [firstSource, secondSource])

        firstSource.added = []
        secondSource.added = []

        self.indexer.reset()
        self.assertEquals(firstSource.removed, [self.indexer])
        self.assertEquals(secondSource.removed, [self.indexer])
        self.assertEquals(firstSource.added, [(self.indexer, iaxiom.REMOTE)])
        self.assertEquals(secondSource.added, [(self.indexer, iaxiom.REMOTE)])


    def test_emptySearch(self):
        """
        Test that a search with no term and no keywords returns an empty result
        set.
        """
        writer = self.openWriteIndex()
        writer.add(IndexableThing(
                _documentType=u'thing',
                _uniqueIdentifier='7',
                _textParts=[u'apple', u'banana'],
                _keywordParts={}))
        writer.add(IndexableThing(
                _documentType=u'thing',
                _uniqueIdentifier='21',
                _textParts=[u'cherry', u'drosophila melanogaster'],
                _keywordParts={}))
        writer.close()

        reader  = self.openReadIndex()
        results = list(reader.search(u'', {}))
        self.assertEquals(results, [])


    def testSimpleSerializedUsage(self):
        writer = self.openWriteIndex()
        writer.add(IndexableThing(
                _documentType=u'thing',
                _uniqueIdentifier='7',
                _textParts=[u'apple', u'banana'],
                _keywordParts={}))
        writer.add(IndexableThing(
                _documentType=u'thing',
                _uniqueIdentifier='21',
                _textParts=[u'cherry', u'drosophila melanogaster'],
                _keywordParts={}))
        writer.close()

        reader = self.openReadIndex()

        results = identifiersFrom(reader.search(u'apple'))
        self.assertEquals(results, [7])

        results = identifiersFrom(reader.search(u'banana'))
        self.assertEquals(results, [7])

        results = identifiersFrom(reader.search(u'cherry'))
        self.assertEquals(results, [21])

        results = identifiersFrom(reader.search(u'drosophila'))
        self.assertEquals(results, [21])

        results = identifiersFrom(reader.search(u'melanogaster'))
        self.assertEquals(results, [21])

        reader.close()


    def testWriteReadWriteRead(self):
        writer = self.openWriteIndex()
        writer.add(IndexableThing(
                _documentType=u'thing',
                _uniqueIdentifier='1',
                _textParts=[u'apple', u'banana'],
                _keywordParts={}))
        writer.close()

        reader = self.openReadIndex()
        results = identifiersFrom(reader.search(u'apple'))
        self.assertEquals(results, [1])
        results = identifiersFrom(reader.search(u'banana'))
        self.assertEquals(results, [1])
        reader.close()

        writer = self.openWriteIndex()
        writer.add(IndexableThing(
                _documentType=u'thing',
                _uniqueIdentifier='2',
                _textParts=[u'cherry', u'drosophila melanogaster'],
                _keywordParts={}))
        writer.close()

        reader = self.openReadIndex()
        results = identifiersFrom(reader.search(u'apple'))
        self.assertEquals(results, [1])
        results = identifiersFrom(reader.search(u'banana'))
        self.assertEquals(results, [1])

        results = identifiersFrom(reader.search(u'cherry'))
        self.assertEquals(results, [2])
        results = identifiersFrom(reader.search(u'drosophila'))
        self.assertEquals(results, [2])
        results = identifiersFrom(reader.search(u'melanogaster'))
        self.assertEquals(results, [2])
        reader.close()


    def testReadBeforeWrite(self):
        reader = self.openReadIndex()
        results = identifiersFrom(reader.search(u'apple'))
        self.assertEquals(results, [])


    def test_remove(self):
        """
        Test that the L{remove} method of an indexer successfully removes
        the item it is given from its index.
        """
        item = IndexableThing(
            _documentType=u'thing',
            _uniqueIdentifier='50',
            _textParts=[u'apple', u'banana'],
            _keywordParts={})
        writer = self.openWriteIndex()
        writer.add(item)
        writer.close()

        self.indexer.remove(item)
        self.indexer._flush()

        reader = self.openReadIndex()
        self.assertEqual(
            identifiersFrom(reader.search(u'apple')), [])


    def test_removalFromReadIndex(self):
        """
        Add a document to an index and then remove it, asserting that it no
        longer appears once it has been removed.
        """
        writer = self.openWriteIndex()
        writer.add(IndexableThing(
                _documentType=u'thing',
                _uniqueIdentifier='50',
                _textParts=[u'apple', u'banana'],
                _keywordParts={}))
        writer.close()

        reader = self.openReadIndex()
        reader.remove(u'50')
        reader.close()

        reader = self.openReadIndex()
        self.assertEqual(
            identifiersFrom(reader.search(u'apple')), [])


    def testKeywordIndexing(self):
        """
        Test that an L{IFulltextIndexable}'s keyword parts can be searched for.
        """
        writer = self.openWriteIndex()
        writer.add(IndexableThing(
                _documentType=u'thing',
                _uniqueIdentifier='50',
                _textParts=[u'apple', u'banana'],
                _keywordParts={u'subject': u'fruit'}))
        writer.close()

        reader = self.openReadIndex()
        self.assertEquals(
            identifiersFrom(reader.search(u'airplane')), [])
        self.assertEquals(
            identifiersFrom(reader.search(u'fruit')), [])
        self.assertEquals(
            identifiersFrom(reader.search(u'apple')), [50])
        self.assertEquals(
            identifiersFrom(reader.search(u'apple', {u'subject': u'fruit'})), [50])
        self.assertEquals(
            identifiersFrom(reader.search(u'', {u'subject': u'fruit'})), [50])


    def test_typeRestriction(self):
        """
        Test that the type of an IFulltextIndexable is automatically found when
        indexing and searching for items of a particular type limits the
        results appropriately.
        """
        writer = self.openWriteIndex()
        writer.add(IndexableThing(
                _documentType=u'first',
                _uniqueIdentifier='1',
                _textParts=[u'apple', u'banana'],
                _keywordParts={}))
        writer.add(IndexableThing(
                _documentType=u'second',
                _uniqueIdentifier='2',
                _textParts=[u'apple', u'banana'],
                _keywordParts={}))
        writer.close()

        reader = self.openReadIndex()
        self.assertEquals(
            identifiersFrom(reader.search(u'apple', {'documentType': u'first'})),
            [1])
        self.assertEquals(
            identifiersFrom(reader.search(u'apple', {'documentType': u'second'})),
            [2])
        self.assertEquals(
            identifiersFrom(reader.search(u'apple', {'documentType': u'three'})),
            [])


    def testKeywordTokenization(self):
        """
        Keyword values should be tokenized just like text parts.
        """
        writer = self.openWriteIndex()
        writer.add(IndexableThing(
                _documentType=u'thing',
                _uniqueIdentifier='50',
                _textParts=[u'apple', u'banana'],
                _keywordParts={u'subject': u'list of fruit things'}))
        writer.close()

        reader = self.openReadIndex()
        self.assertEquals(
            identifiersFrom(reader.search(u'pear')), [])
        self.assertEquals(
            identifiersFrom(reader.search(u'fruit')), [])
        self.assertEquals(
            identifiersFrom(reader.search(u'apple')), [50])
        self.assertEquals(
            identifiersFrom(reader.search(u'apple', {u'subject': u'fruit'})), [50])
        self.assertEquals(
            identifiersFrom(reader.search(u'', {u'subject': u'fruit'})), [50])
        self.assertEquals(
            identifiersFrom(reader.search(u'', {u'subject': u'list'})), [50])
        self.assertEquals(
            identifiersFrom(reader.search(u'', {u'subject': u'things'})), [50])


    def testKeywordCombination(self):
        """
        Multiple keyword searches should be AND'ed
        """
        writer = self.openWriteIndex()
        def makeIndexable(uniqueIdentifier, **k):
            writer.add(IndexableThing(
                         _documentType=u'thing',
                         _uniqueIdentifier=str(uniqueIdentifier),
                         _textParts=[],
                         _keywordParts=dict((unicode(k), unicode(v))
                                                for (k, v) in k.iteritems())))

        makeIndexable(50, name='john', car='honda')
        makeIndexable(51, name='john', car='mercedes')
        writer.close()

        reader = self.openReadIndex()

        self.assertEquals(
            identifiersFrom(reader.search(u'', {u'car': u'honda'})), [50])
        self.assertEquals(
            identifiersFrom(reader.search(u'', {u'car': u'mercedes'})), [51])
        self.assertEquals(
            identifiersFrom(reader.search(u'', {u'name': u'john'})), [50, 51])
        self.assertEquals(
            identifiersFrom(reader.search(u'', {u'name': u'john', u'car': u'honda'})), [50])
        self.assertEquals(
            identifiersFrom(reader.search(u'', {u'name': u'john', u'car': u'mercedes'})), [51])


    def testKeywordValuesInPhrase(self):
        """
        Keyword values should return results when included in the main phrase
        """
        writer = self.openWriteIndex()
        writer.add(IndexableThing(
                    _documentType=u'thing',
                    _uniqueIdentifier='50',
                    _textParts=[u'my name is jack'],
                    _keywordParts={u'car': u'honda'}))
        writer.close()

        reader = self.openReadIndex()

        self.assertEquals(
            identifiersFrom(reader.search(u'honda', {})), [])
        self.assertEquals(
            identifiersFrom(reader.search(u'jack', {})), [50])
        self.assertEquals(
            identifiersFrom(reader.search(u'', {u'car': u'honda'})), [50])
        self.assertEquals(
            identifiersFrom(reader.search(u'', {u'car': u'jack'})), [])

    def testDigitSearch(self):
        """
        Should get results if we search for digits that appear in indexed
        documents
        """
        writer = self.openWriteIndex()
        writer.add(IndexableThing(
                    _documentType=u'thing',
                    _uniqueIdentifier='50',
                    _textParts=[u'123 456'],
                    _keywordParts={}))
        writer.close()

        reader = self.openReadIndex()

        self.assertEquals(
            identifiersFrom(reader.search(u'123', {})), [50])
        self.assertEquals(
            identifiersFrom(reader.search(u'456', {})), [50])

    def testSorting(self):
        """
        Index some stuff with out of order sort keys and ensure that
        they come back ordered by sort key.
        """

        writer = self.openWriteIndex()
        keys = (5, 20, 6, 127, 2)

        for k in keys:
            writer.add(IndexableThing(
                    _documentType=u'thing',
                    _uniqueIdentifier=str(k),
                    _textParts=[u'ok'],
                    _keywordParts={}))
        writer.close()

        reader = self.openReadIndex()

        self.assertEquals(identifiersFrom(reader.search(u'ok')),
                          list(sorted(keys)))

    def testSortAscending(self):
        """
        Test that the C{sortAscending} parameter to C{search} is observed
        """
        writer = self.openWriteIndex()

        for i in xrange(5):
            writer.add(IndexableThing(
                        _documentType=u'thing',
                        _uniqueIdentifier=str(i),
                        _textParts=[u'ok'],
                        _keywordParts={}))
        writer.close()

        reader = self.openReadIndex()

        self.assertEquals(identifiersFrom(reader.search(u'ok')), range(5))
        self.assertEquals(identifiersFrom(reader.search(u'ok', sortAscending=True)), range(5))
        self.assertEquals(identifiersFrom(reader.search(u'ok', sortAscending=False)), range(4, -1, -1))


class CorruptionRecoveryMixin(IndexerTestsMixin):
    def corruptIndex(self):
        raise NotImplementedError()


    def testRecoveryAfterFailure(self):
        """
        Create an indexer, attach some sources to it, let it process some
        messages, corrupt the database, let it try to clean things up, then
        make sure the index is in a reasonable state.
        """
        # Try to access the indexer directly first so that if it is
        # unavailable, the test will be skipped.
        self.openReadIndex().close()

        service = batch.BatchProcessingService(self.store, iaxiom.REMOTE)
        task = service.step()

        source = batch.processor(IndexableThing)(store=self.store)
        self.indexer.addSource(source)

        things = [
            IndexableThing(store=self.store,
                           _documentType=u'thing',
                           _uniqueIdentifier='100',
                           _textParts=[u'apple', u'banana'],
                           _keywordParts={}),
            IndexableThing(store=self.store,
                           _documentType=u'thing',
                           _uniqueIdentifier='200',
                           _textParts=[u'cherry'],
                           _keywordParts={})]

        for i in xrange(len(things)):
            task.next()

        self.indexer.suspend()

        # Sanity check - make sure both items come back from a search before
        # going on with the real core of the test.
        reader = self.openReadIndex()
        self.assertEquals(identifiersFrom(reader.search(u'apple')), [100])
        self.assertEquals(identifiersFrom(reader.search(u'cherry')), [200])
        self.assertEquals(identifiersFrom(reader.search(u'drosophila')), [])
        reader.close()

        self.corruptIndex()
        self.indexer.resume()

        things.append(
            IndexableThing(store=self.store,
                           _documentType=u'thing',
                           _uniqueIdentifier='300',
                           _textParts=[u'drosophila', u'melanogaster'],
                           _keywordParts={}))

        # Step it once so that it notices the index has been corrupted.
        task.next()
        self.indexer.suspend()

        # At this point, the index should have been deleted, so any search
        # should turn up no results.
        reader = self.openReadIndex()
        self.assertEquals(identifiersFrom(reader.search(u'apple')), [])
        self.assertEquals(identifiersFrom(reader.search(u'cherry')), [])
        self.assertEquals(identifiersFrom(reader.search(u'drosophila')), [])
        reader.close()

        self.indexer.resume()

        # Step it another N so that each thing gets re-indexed.
        for i in xrange(len(things)):
            task.next()

        self.indexer.suspend()

        reader = self.openReadIndex()
        self.assertEquals(identifiersFrom(reader.search(u'apple')), [100])
        self.assertEquals(identifiersFrom(reader.search(u'cherry')), [200])
        self.assertEquals(identifiersFrom(reader.search(u'drosophila')), [300])
        reader.close()



class HypeTestsMixin:
    def createIndexer(self):
        return fulltext.HypeIndexer(store=self.store, indexDirectory=self.path)



class HypeFulltextTestCase(HypeTestsMixin, FulltextTestsMixin, unittest.TestCase):
    skip = "These tests don't actually pass - and I don't even care."



class PyLuceneTestsMixin:
    def createIndexer(self):
        return fulltext.PyLuceneIndexer(store=self.store, indexDirectory=self.path)


class PyLuceneFulltextTestCase(PyLuceneTestsMixin, FulltextTestsMixin, unittest.TestCase):
    def testAutomaticClosing(self):
        """
        Test that if we create a writer and call the close-helper function,
        the writer gets closed.
        """
        writer = self.openWriteIndex()
        fulltext._closeIndexes()
        self.failUnless(writer.closed, "Writer should have been closed.")


    def testRepeatedClosing(self):
        """
        Test that if for some reason a writer is explicitly closed after the
        close-helper has run, nothing untoward occurs.
        """
        writer = self.openWriteIndex()
        fulltext._closeIndexes()
        writer.close()
        self.failUnless(writer.closed, "Writer should have stayed closed.")

    def test_resultSlicing(self):
        """
        Test that the wrapper object return by the pylucene index correctly
        handles slices
        """

        writer = self.openWriteIndex()
        identifiers = range(20)
        for i in identifiers:
            writer.add(IndexableThing(
                        _documentType=u'thing',
                        _uniqueIdentifier=str(i),
                        _textParts=[u'e'],
                        _keywordParts={}))
        writer.close()

        reader = self.openReadIndex()

        results = reader.search(u'e')

        self.assertEquals(identifiersFrom(results), identifiers)
        self.assertEquals(identifiersFrom(results[0:None:2]), identifiers[0:None:2])
        self.assertEquals(identifiersFrom(results[0:5:1]), identifiers[0:5:1])
        self.assertEquals(identifiersFrom(results[15:0:-1]), identifiers[15:0:-1])
        self.assertEquals(identifiersFrom(results[15:None:-1]), identifiers[15:None:-1])
        self.assertEquals(identifiersFrom(results[0:24:2]), identifiers[0:24:2])
        self.assertEquals(identifiersFrom(results[24:None:-1]), identifiers[24:None:-1])


    def test_hitWrapperAttributes(self):
        """
        Test that L{xmantissa.fulltext._PyLuceneHitWrapper}'s attributes are
        set correctly
        """
        class Indexable:
            implements(ixmantissa.IFulltextIndexable)

            def keywordParts(self):
                return {u'foo': u'bar', u'baz': u'quux'}

            def uniqueIdentifier(self):
                return 'indexable'

            def documentType(self):
                return 'the indexable type'

            def sortKey(self):
                return 'foo'

            def textParts(self):
                return [u'my', u'text']

        indexable = Indexable()
        writer = self.openWriteIndex()
        writer.add(indexable)
        writer.close()

        reader = self.openReadIndex()
        (wrapper,) = reader.search(u'text')

        self.assertEquals(wrapper.keywordParts, indexable.keywordParts())
        self.assertEquals(wrapper.uniqueIdentifier, indexable.uniqueIdentifier())
        self.assertEquals(wrapper.documentType, indexable.documentType())
        self.assertEquals(wrapper.sortKey, indexable.sortKey())


class PyLuceneCorruptionRecoveryTestCase(PyLuceneTestsMixin, CorruptionRecoveryMixin, unittest.TestCase):
    def corruptIndex(self):
        """
        Cause a PyLucene index to appear corrupted.
        """
        for ch in self.store.newFilePath(self.path).children():
            ch.setContent('hello, world')


    def testFailureDetectionFromWriter(self):
        """
        Fulltext indexes are good at two things: soaking up I/O bandwidth and
        corrupting themselves.  For the latter case, we need to be able to
        detect the condition before we can make any response to it.
        """
        writer = self.openWriteIndex()
        writer.add(IndexableThing(
                _documentType=u'thing',
                _uniqueIdentifier='10',
                _textParts=[u'apple', u'banana'],
                _keywordParts={}))
        writer.close()
        self.corruptIndex()
        self.assertRaises(fulltext.IndexCorrupt, self.openWriteIndex)
        self.assertRaises(fulltext.IndexCorrupt, self.openReadIndex)


    def testFailureDetectionFromReader(self):
        """
        Like testFailureDetectionFromWriter, but opens a reader after
        corrupting the index and asserts that it also raises the appropriate
        exception.
        """
        writer = self.openWriteIndex()
        writer.add(IndexableThing(
                _documentType=u'thing',
                _uniqueIdentifier='10',
                _textParts=[u'apple', u'banana'],
                _keywordParts={}))
        writer.close()
        self.corruptIndex()
        self.assertRaises(fulltext.IndexCorrupt, self.openReadIndex)
        self.assertRaises(fulltext.IndexCorrupt, self.openWriteIndex)



class PyLuceneLockedRecoveryTestCase(PyLuceneTestsMixin, CorruptionRecoveryMixin, unittest.TestCase):
    def setUp(self):
        CorruptionRecoveryMixin.setUp(self)
        self.corruptedIndexes = []


    def corruptIndex(self):
        """
        Loosely simulate filesystem state following a SIGSEGV or power
        failure.
        """
        self.corruptedIndexes.append(self.openWriteIndex())



class PyLuceneObjectLifetimeTestCase(unittest.TestCase):
    def test_hitsWrapperClosesIndex(self):
        """
        Test that when L{_PyLuceneHitsWrapper} is GC'd, the index which backs
        its C{Hits} object gets closed.
        """
        class TestIndex(object):
            closed = False
            def close(self):
                self.closed = True

        index = TestIndex()
        wrapper = fulltext._PyLuceneHitsWrapper(index, None)
        self.failIf(index.closed)
        del wrapper
        self.failUnless(index.closed)


class IndexerAPISearchTestsMixin(IndexerTestsMixin):
    """
    Test ISearchProvider search API on indexer objects
    """

    def setUp(self):
        """
        Make a store, an account/substore, an indexer, and call startService()
        on the superstore's IService so the batch process interactions that
        happen in fulltext.py work
        """
        self.dbdir = self.mktemp()
        self.path = u'index'

        superstore = store.Store(self.dbdir)

        loginSystem = LoginSystem(store=superstore)
        installOn(loginSystem, superstore)

        account = loginSystem.addAccount(u'testuser', u'example.com', None)
        substore = account.avatars.open()

        self.store = substore
        self.indexer = self.createIndexer()

        self.svc = IService(superstore)
        self.svc.startService()

        # Make sure the indexer is actually available
        writer = self.openWriteIndex()
        writer.close()

    def tearDown(self):
        """
        Stop the service we started in C{setUp}
        """
        return self.svc.stopService()

    def _indexSomeItems(self):
        writer = self.openWriteIndex()
        for i in xrange(5):
            writer.add(IndexableThing(
                        _documentType=u'thing',
                        _uniqueIdentifier=str(i),
                        _textParts=[u'text'],
                        _keywordParts={}))
        writer.close()

    def testIndexerSearching(self):
        """
        Test calling search() on the indexer item directly
        """
        def gotResult(res):
            self.assertEquals(identifiersFrom(res), range(5))
        self._indexSomeItems()
        return self.indexer.search(u'text').addCallback(gotResult)

    def testIndexerSearchingCount(self):
        """
        Test calling search() on the indexer item directly, with a count arg
        """
        def gotResult(res):
            self.assertEquals(identifiersFrom(res), [0])
        self._indexSomeItems()
        return self.indexer.search(u'text', count=1).addCallback(gotResult)

    def testIndexerSearchingOffset(self):
        """
        Test calling search() on the indexer item directly, with an offset arg
        """
        def gotResult(res):
            self.assertEquals(identifiersFrom(res), [1, 2, 3, 4])
        self._indexSomeItems()
        return self.indexer.search(u'text', offset=1).addCallback(gotResult)

    def testIndexerSearchingCountOffset(self):
        """
        Test calling search() on the indexer item directly, with count & offset args
        """
        def gotResult(res):
            self.assertEquals(identifiersFrom(res), [1, 2, 3])
        self._indexSomeItems()
        return self.indexer.search(u'text', count=3, offset=1)


    def test_DifficultTokens(self):
        """
        Test searching for fragments of phone numbers, email
        addresses, and urls.
        """
        writer = self.openWriteIndex()
        specimens = [u"trevor 718-555-1212", u"bob rjones@moddiv.com",
                     u"atop http://divmod.org/projects/atop"]
        for i, txt in enumerate(specimens):
            writer.add(IndexableThing(
                        _documentType=u'thing',
                        _uniqueIdentifier=str(i),
                        _textParts=[txt],
                        _keywordParts={}))
        writer.close()
        def gotResult(res):
            return identifiersFrom(res)
        def testResults(results):
            self.assertEqual(results, [[0], [1], [2],
                                       [0], [1], [2]])
        return gatherResults(
            [self.indexer.search(u'718').addCallback(gotResult),
             self.indexer.search(u'moddiv').addCallback(gotResult),
             self.indexer.search(u'divmod').addCallback(gotResult),
             self.indexer.search(u'718-555').addCallback(gotResult),
             self.indexer.search(u'rjones@moddiv').addCallback(gotResult),
             self.indexer.search(u'divmod.org').addCallback(gotResult),
             ]
            ).addCallback(testResults)

    def test_unicodeSearch(self):
        return self.indexer.search(u'\N{WHITE SMILING FACE}')



class PyLuceneIndexerAPISearchTestCase(PyLuceneTestsMixin, IndexerAPISearchTestsMixin, unittest.TestCase):
    pass



class HypeIndexerAPISearchTestCase(HypeTestsMixin, IndexerAPISearchTestsMixin, unittest.TestCase):
    skip = "These tests don't actually pass - and I don't even care."



def _hasFTS3():
    s = store.Store()
    try:
        s.createSQL('CREATE VIRTUAL TABLE fts USING fts3')
    except SQLError:
        return False
    else:
        return True



class SQLiteTestsMixin(object):
    """
    Mixin for tests for the SQLite indexer.
    """
    if not _hasFTS3():
        skip = 'No FTS3 support'


    def createIndexer(self):
        """
        Create the SQLite indexer.
        """
        return fulltext.SQLiteIndexer(store=self.store, indexDirectory=self.path)



class SQLiteFulltextTestCase(SQLiteTestsMixin, FulltextTestsMixin, unittest.TestCase):
    """
    Tests for SQLite fulltext indexing.
    """
    def _noKeywords(self):
        raise unittest.SkipTest('Keywords are not implemented')


    testKeywordCombination = _noKeywords
    testKeywordIndexing = _noKeywords
    testKeywordTokenization = _noKeywords
    testKeywordValuesInPhrase = _noKeywords
    test_typeRestriction = _noKeywords



class SQLiteIndexerAPISearchTestCase(SQLiteTestsMixin, IndexerAPISearchTestsMixin, unittest.TestCase):
    """
    Tests for SQLite indexing through the indexer service.
    """
    def test_DifficultTokens(self):
        raise unittest.SkipTest("SQLite tokenizer can't handle all of these")
