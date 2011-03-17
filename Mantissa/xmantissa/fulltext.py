# -*- test-case-name: xmantissa.test.test_fulltext -*-

"""
General functionality re-usable by various concrete fulltext indexing systems.
"""

import atexit, os, weakref, warnings

from zope.interface import implements

from twisted.python import log, reflect
from twisted.internet import defer

from epsilon.structlike import record
from epsilon.view import SlicedView

from axiom import item, attributes, iaxiom, batch
from axiom.upgrade import registerUpgrader, registerAttributeCopyingUpgrader
from axiom.store import Store, AttributeQuery
from axiom.attributes import AttributeValueComparison, SimpleOrdering

from xmantissa import ixmantissa

HYPE_INDEX_DIR = u'hype.index'
XAPIAN_INDEX_DIR = u'xap.index'
LUCENE_INDEX_DIR = u'lucene.index'

VERBOSE = True

class IndexCorrupt(Exception):
    """
    An attempt was made to open an index which has had unrecoverable data
    corruption.
    """



class _IndexerInputSource(item.Item):
    """
    Tracks L{IBatchProcessor}s which have had an indexer added to them as a
    listener.
    """
    indexer = attributes.reference(doc="""
    The indexer item with which this input source is associated.
    """, whenDeleted=attributes.reference.CASCADE)

    source = attributes.reference(doc="""
    The L{IBatchProcessor} which acts as the input source.
    """, whenDeleted=attributes.reference.CASCADE)



class _RemoveDocument(item.Item):
    """
    Tracks a document deletion which should occur before the next search is
    performed.
    """
    indexer = attributes.reference(doc="""
    The indexer item with which this deletion is associated.
    """, whenDeleted=attributes.reference.CASCADE)

    documentIdentifier = attributes.bytes(doc="""
    The identifier, as returned by L{IFulltextIndexable.uniqueIdentifier},
    for the document which should be removed from the index.
    """, allowNone=False)



class RemoteIndexer(object):
    """
    Implements most of a full-text indexer.

    This uses L{axiom.batch} to perform indexing out of process and presents an
    asynchronous interface to in-process searching of that indexing.
    """
    implements(iaxiom.IReliableListener, ixmantissa.ISearchProvider, ixmantissa.IFulltextIndexer)


    def installOn(self, other):
        super(RemoteIndexer, self).installOn(other)
        other.powerUp(self, ixmantissa.IFulltextIndexer)


    def openReadIndex(self):
        """
        Return an object usable to search this index.

        Subclasses should implement this.
        """
        raise NotImplementedError


    def openWriteIndex(self):
        """
        Return an object usable to add documents to this index.

        Subclasses should implement this.
        """
        raise NotImplementedError


    def __finalizer__(self):
        d = self.__dict__
        id = self.storeID
        s = self.store
        def finalize():
            idx = d.get('_index', None)
            if idx is not None:
                if VERBOSE:
                    log.msg("Closing %r from finalizer of %s/%d" % (idx, s, id))
                idx.close()
        return finalize


    def activate(self):
        assert not hasattr(self, '_index')
        self._index = None
        if VERBOSE:
            log.msg("Activating %s/%d with null index" % (self.store, self.storeID))


    def addSource(self, itemSource):
        """
        Add the given L{IBatchProcessor} as a source of input for this indexer.
        """
        _IndexerInputSource(store=self.store, indexer=self, source=itemSource)
        itemSource.addReliableListener(self, style=iaxiom.REMOTE)


    def getSources(self):
        return self.store.query(_IndexerInputSource, _IndexerInputSource.indexer == self).getColumn("source")


    def reset(self):
        """
        Process everything all over again.
        """
        self.indexCount = 0
        indexDir = self.store.newDirectory(self.indexDirectory)
        if indexDir.exists():
            indexDir.remove()
        for src in self.getSources():
            src.removeReliableListener(self)
            src.addReliableListener(self, style=iaxiom.REMOTE)


    def _closeIndex(self):
        if VERBOSE:
            log.msg("%s/%d closing index" % (self.store, self.storeID))
        if self._index is not None:
            if VERBOSE:
                log.msg("%s/%d *really* closing index" % (self.store, self.storeID))
            self._index.close()
            self._index = None


    # IFulltextIndexer
    def add(self, item):
        if self._index is None:
            try:
                self._index = self.openWriteIndex()
            except IndexCorrupt:
                self.reset()
                return

            if VERBOSE:
                log.msg("Opened %s %s/%d for writing" % (self._index, self.store, self.storeID))

        if VERBOSE:
            log.msg("%s/%d indexing document" % (self.store, self.storeID))
        self._index.add(ixmantissa.IFulltextIndexable(item))
        self.indexCount += 1


    def remove(self, item):
        identifier = ixmantissa.IFulltextIndexable(item).uniqueIdentifier()
        if VERBOSE:
            log.msg("%s/%d scheduling %r for removal." % (self.store, self.storeID, identifier))
        _RemoveDocument(store=self.store,
                        indexer=self,
                        documentIdentifier=identifier)



    def _flush(self):
        """
        Deal with pending result-affecting things.

        This should always be called before issuing a search.
        """
        remove = self.store.query(_RemoveDocument)
        documentIdentifiers = list(remove.getColumn("documentIdentifier"))
        if VERBOSE:
            log.msg("%s/%d removing %r" % (self.store, self.storeID, documentIdentifiers))
        reader = self.openReadIndex()
        map(reader.remove, documentIdentifiers)
        reader.close()
        remove.deleteFromStore()


    # IReliableListener
    def suspend(self):
        self._flush() # Make sure any pending deletes are processed.
        if VERBOSE:
            log.msg("%s/%d suspending" % (self.store, self.storeID))
        self._closeIndex()
        return defer.succeed(None)


    def resume(self):
        if VERBOSE:
            log.msg("%s/%d resuming" % (self.store, self.storeID))
        return defer.succeed(None)


    def processItem(self, item):
        return self.add(item)


    # ISearchProvider
    def search(self, aString, keywords=None, count=None, offset=0,
               sortAscending=True, retry=3):
        ident = "%s/%d" % (self.store, self.storeID)
        b = iaxiom.IBatchService(self.store)
        if VERBOSE:
            log.msg("%s issuing suspend" % (ident,))
        d = b.suspend(self.storeID)

        def reallySearch(ign):
            if VERBOSE:
                log.msg("%s getting reader index" % (ident,))
            idx = self.openReadIndex()

            if VERBOSE:
                log.msg("%s searching for %s" % (
                    ident, aString.encode('utf-8')))
            results = idx.search(aString, keywords, sortAscending)
            if VERBOSE:
                log.msg("%s found %d results" % (ident, len(results)))

            if count is None:
                end = None
            else:
                end = offset + count

            results = results[offset:end]

            if VERBOSE:
                log.msg("%s sliced from %s to %s, leaving %d results" % (
                        ident, offset, end, len(results)))
            return results

        d.addCallback(reallySearch)

        def resumeIndexing(results):
            if VERBOSE:
                log.msg("%s issuing resume" % (ident,))
            b.resume(self.storeID).addErrback(log.err)
            return results
        d.addBoth(resumeIndexing)

        def searchFailed(err):
            log.msg("Search failed somehow:")
            log.err(err)
            if retry:
                log.msg("Re-issuing search")
                return self.search(aString, keywords, count, offset, retry=retry-1)
            else:
                log.msg("Wow, lots of failures searching.  Giving up and "
                        "returning (probably wrong!) no results to user.")
                return []
        d.addErrback(searchFailed)
        return d



try:
    import hype
except ImportError:
    hype = None

class _HypeIndex(object):
    def __init__(self, index):
        self.index = index
        self.close = index.close


    def add(self, message):
        doc = hype.Document()
        for (k, v) in message.valueParts():
            doc.add_hidden_text(v.encode('utf-8'))
        doc['@uri'] = message.uniqueIdentifier()

        for part in message.textParts():
            doc.add_text(part.encode('utf-8'))

        self.index.put_doc(doc)


    def search(self, term, keywords=None, sortAscending=True):
        return [int(d.uri) for d in self.index.search(term)]



class HypeIndexer(RemoteIndexer, item.Item):

    schemaVersion = 3

    indexCount = attributes.integer(default=0)
    installedOn = attributes.reference()
    indexDirectory = attributes.text(default=HYPE_INDEX_DIR)

    _index = attributes.inmemory()

    if hype is None:
        def openReadIndex(self):
            raise NotImplementedError("hype is unavailable")


        def openWriteIndex(self):
            raise NotImplementedError("hype is unavailable")
    else:
        def openReadIndex(self):
            hypedir = self.store.newDirectory(self.indexDirectory)
            return _HypeIndex(hype.Database(hypedir.path, hype.ESTDBREADER | hype.ESTDBLCKNB | hype.ESTDBCREAT))


        def openWriteIndex(self):
            hypedir = self.store.newDirectory(self.indexDirectory)
            return _HypeIndex(hype.Database(hypedir.path, hype.ESTDBWRITER | hype.ESTDBCREAT))


class XapianIndexer(RemoteIndexer, item.Item):
    """
    The remnants of an indexer based on Xapian (by way of Xapwrap).  This
    indexing back end is no longer supported.  This item remains defined for
    schema compatibility only.  It should be upgraded out of existence
    eventually and then the class deleted.
    """

    schemaVersion = 3

    indexCount = attributes.integer(default=0)
    installedOn = attributes.reference()
    indexDirectory = attributes.text(default=XAPIAN_INDEX_DIR)

    _index = attributes.inmemory()

    def openReadIndex(self):
        raise NotImplementedError("xapian is no longer supported")


    def openWriteIndex(self):
        raise NotImplementedError("xapian is no longer supported")



try:
    import PyLucene
except ImportError:
    PyLucene = None


_hitsWrapperWeakrefs = weakref.WeakKeyDictionary()

class _PyLuceneHitsWrapper(record('index hits')):
    """
    Container for a C{Hits} instance and the L{_PyLuceneIndex} from which it
    came.  This gives the C{Hits} instance a sequence-like interface and when a
    _PyLuceneHitsWrapper is garbage collected, it closes the L{_PyLuceneIndex}
    it has a reference to.
    """
    def __init__(self, *a, **kw):
        super(_PyLuceneHitsWrapper, self).__init__(*a, **kw)

        def close(ref, index=self.index):
            log.msg("Hits wrapper expiring, closing index.")
            index.close()
        _hitsWrapperWeakrefs[self] = weakref.ref(self, close)


    def __len__(self):
        return len(self.hits)


    def __getitem__(self, index):
        """
        Retrieve the storeID field of the requested hit, converting it to an
        integer before returning it.  This handles integer indexes as well as
        slices.
        """
        if isinstance(index, slice):
            return SlicedView(self, index)
        if index >= len(self.hits):
            raise IndexError(index)
        return _PyLuceneHitWrapper(self.hits[index])


class _PyLuceneHitWrapper:
    """
    Wrapper around a single pylucene hit

    @ivar keywordParts: dictionary mapping keyword names to values.  should be the
    same as the result of calling the L{IFulltextIndexable.keywordParts} on
    the item corresponding to the hit
    @ivar documentType: the document type.  return value of
    L{IFulltextIndexable.documentType} called on the item corresponding to the
    hit
    @ivar uniqueIdentifier: an opaque unique identifier.  return value of
    L{IFulltextIndexable.uniqueIdentifier} called on the item corresponding to
    the hit
    @ivar sortKey: the key to sort on.  return value of
    L{IFulltextIndexable.sortKey} called on the item corresponding to the hit
    """
    def __init__(self, hit):
        self.keywordParts = self._getKeywords(hit)
        self.documentType = hit['documentType']
        self.uniqueIdentifier = hit['storeID']
        self.sortKey = hit['sortKey']

    def _getKeywords(self, hit):
        keywords = {}
        systemKeywords = set(('storeID', 'documentType', 'sortKey'))
        for field in hit.fields():
            if field.name() not in systemKeywords:
                keywords[field.name()] = hit[field.name()]
        return keywords

    def __int__(self):
        warnings.warn(
            '_PyLuceneHitWrapper is not an integer',
            DeprecationWarning)
        return int(self.uniqueIdentifier)

    def __cmp__(self, other):
        warnings.warn(
            '_PyLuceneHitWrapper is not an integer',
            DeprecationWarning)
        return int(self).__cmp__(other)


class _PyLuceneBase(object):
    closed = False

    def __init__(self, fsdir, analyzer):
        _closeObjects.append(self)
        self.fsdir = fsdir
        self.analyzer = analyzer


    def close(self):
        if not self.closed:
            self._reallyClose()
            self.fsdir.close()
        self.closed = True
        try:
            _closeObjects.remove(self)
        except ValueError:
            pass



_closeObjects = []
def _closeIndexes():
    """
    Helper for _PyLuceneIndex to make sure FSDirectory and IndexWriter
    instances always get closed.  This gets registered with atexit and
    closes any _PyLuceneIndex objects still in _closeObjects when it gets
    run.
    """
    while _closeObjects:
        _closeObjects[-1].close()
atexit.register(_closeIndexes)



class _PyLuceneReader(_PyLuceneBase):
    """
    Searches and deletes from a Lucene index.
    """
    def __init__(self, fsdir, analyzer, reader, searcher):
        self.reader = reader
        self.searcher = searcher
        super(_PyLuceneReader, self).__init__(fsdir, analyzer)


    def _reallyClose(self):
        self.reader.close()
        self.searcher.close()


    def remove(self, documentIdentifier):
        self.reader.deleteDocuments(
            PyLucene.Term('storeID', documentIdentifier))


    def search(self, phrase, keywords=None, sortAscending=True):
        if not phrase and not keywords:
            return []

        # XXX Colons in phrase will screw stuff up.  Can they be quoted or
        # escaped somehow?  Probably by using a different QueryParser.
        if keywords:
            fieldPhrase = u' '.join(u':'.join((k, v)) for (k, v) in keywords.iteritems())
            if phrase:
                phrase = phrase + u' ' + fieldPhrase
            else:
                phrase = fieldPhrase
        phrase = phrase.translate({ord(u'@'): u' ', ord(u'-'): u' ',
                                   ord(u'.'): u' '})
        qp = PyLucene.QueryParser('text', self.analyzer)
        qp.setDefaultOperator(qp.Operator.AND)
        query = qp.parseQuery(phrase)

        sort = PyLucene.Sort(PyLucene.SortField('sortKey', not sortAscending))

        try:
            hits = self.searcher.search(query, sort)
        except PyLucene.JavaError, err:
            if 'no terms in field sortKey' in str(err):
                hits = []
            else:
                raise
        return _PyLuceneHitsWrapper(self, hits)



class _PyLuceneWriter(_PyLuceneBase):
    """
    Adds documents to a Lucene index.
    """
    def __init__(self, fsdir, analyzer, writer):
        self.writer = writer
        super(_PyLuceneWriter, self).__init__(fsdir, analyzer)


    def _reallyClose(self):
        self.writer.close()


    def add(self, message):
        doc = PyLucene.Document()
        for part in message.textParts():
            doc.add(
                PyLucene.Field('text',
                               part.translate({
                ord(u'@'): u' ', ord(u'-'): u' ',
                ord(u'.'): u' '}).encode('utf-8'),
                               PyLucene.Field.Store.NO,
                               PyLucene.Field.Index.TOKENIZED))

        for (k, v) in message.keywordParts().iteritems():
            doc.add(
                PyLucene.Field(k, v.translate({
                ord(u'@'): u' ', ord(u'-'): u' ',
                ord(u'.'): u' '}).encode('utf-8'),
                            PyLucene.Field.Store.YES,
                            PyLucene.Field.Index.TOKENIZED))
        doc.add(
            PyLucene.Field('documentType', message.documentType(),
                           PyLucene.Field.Store.YES,
                           PyLucene.Field.Index.TOKENIZED))

        doc.add(
            PyLucene.Field('storeID',
                           message.uniqueIdentifier(),
                           PyLucene.Field.Store.YES,
                           PyLucene.Field.Index.UN_TOKENIZED))
        doc.add(
            PyLucene.Field('sortKey',
                           message.sortKey(),
                           PyLucene.Field.Store.YES,
                           PyLucene.Field.Index.UN_TOKENIZED))
        # Deprecated. use Field(name, value, Field.Store.YES, Field.Index.UN_TOKENIZED) instead

        self.writer.addDocument(doc)



class PyLuceneIndexer(RemoteIndexer, item.Item):

    schemaVersion = 5

    indexCount = attributes.integer(default=0)
    installedOn = attributes.reference()
    indexDirectory = attributes.text(default=LUCENE_INDEX_DIR)

    _index = attributes.inmemory()
    _lockfile = attributes.inmemory()


    def reset(self):
        """
        In addition to the behavior of the superclass, delete any dangling
        lockfiles which may prevent this index from being opened.  With the
        tested version of PyLucene (something pre-2.0), this appears to not
        actually be necessary: deleting the entire index directory but
        leaving the lockfile in place seems to still allow the index to be
        recreated (perhaps because when the directory does not exist, we
        pass True as the create flag when opening the FSDirectory, I am
        uncertain).  Nevertheless, do this anyway for now.
        """
        RemoteIndexer.reset(self)
        if hasattr(self, '_lockfile'):
            os.remove(self._lockfile)
            del self._lockfile


    def _analyzer(self):
        return PyLucene.StandardAnalyzer([])


    if PyLucene is None:
        def openReadIndex(self):
            raise NotImplementedError("PyLucene is unavailable")


        def openWriteIndex(self):
            raise NotImplementedError("PyLucene is unavailable")
    else:
        def openReadIndex(self):
            luceneDir = self.store.newDirectory(self.indexDirectory)


            if not luceneDir.exists():
                self.openWriteIndex().close()

            fsdir = PyLucene.FSDirectory.getDirectory(luceneDir.path, False)
            try:
                searcher = PyLucene.IndexSearcher(fsdir)
            except PyLucene.JavaError, e:
                raise IndexCorrupt()
            try:
                reader = PyLucene.IndexReader.open(fsdir)
            except PyLucene.JavaError, e:
                raise IndexCorrupt()
            return _PyLuceneReader(fsdir, self._analyzer(), reader, searcher)


        def openWriteIndex(self):
            luceneDir = self.store.newDirectory(self.indexDirectory)

            create = not luceneDir.exists()

            analyzer = self._analyzer()

            fsdir = PyLucene.FSDirectory.getDirectory(luceneDir.path, create)
            try:
                writer = PyLucene.IndexWriter(fsdir, analyzer, create)
            except PyLucene.JavaError, e:
                lockTimeout = u'Lock obtain timed out: Lock@'
                msg = e.getJavaException().getMessage()
                if msg.startswith(lockTimeout):
                    self._lockfile = msg[len(lockTimeout):]
                raise IndexCorrupt()
            return _PyLuceneWriter(fsdir, analyzer, writer)



def remoteIndexer1to2(oldIndexer):
    """
    Previously external application code was responsible for adding a
    RemoteListener to a batch work source as a reliable listener.  This
    precluded the possibility of the RemoteListener resetting itself
    unilaterally.  With version 2, RemoteListener takes control of adding
    itself as a reliable listener and keeps track of the sources with which it
    is associated.  This upgrader creates that tracking state.
    """
    newIndexer = oldIndexer.upgradeVersion(
        oldIndexer.typeName, 1, 2,
        indexCount=oldIndexer.indexCount,
        installedOn=oldIndexer.installedOn,
        indexDirectory=oldIndexer.indexDirectory)

    listeners = newIndexer.store.query(
        batch._ReliableListener,
        batch._ReliableListener.listener == newIndexer)

    for listener in listeners:
        _IndexerInputSource(
            store=newIndexer.store,
            indexer=newIndexer,
            source=listener.processor)

    return newIndexer

def remoteIndexer2to3(oldIndexer):
    """
    The documentType keyword was added to all indexable items.  Indexes need to
    be regenerated for this to take effect.  Also, PyLucene no longer stores
    the text of messages it indexes, so deleting and re-creating the indexes
    will make them much smaller.
    """
    newIndexer = oldIndexer.upgradeVersion(
        oldIndexer.typeName, 2, 3,
        indexCount=oldIndexer.indexCount,
        installedOn=oldIndexer.installedOn,
        indexDirectory=oldIndexer.indexDirectory)
    # the 3->4 upgrader for PyLuceneIndexer calls reset(), so don't do it
    # here.  also, it won't work because it's a DummyItem
    if oldIndexer.typeName != PyLuceneIndexer.typeName:
        newIndexer.reset()
    return newIndexer


def _declareLegacyIndexerItem(typeClass, version):
    item.declareLegacyItem(typeClass.typeName, version,
                           dict(indexCount=attributes.integer(),
                                installedOn=attributes.reference(),
                                indexDirectory=attributes.text()))

for cls in [HypeIndexer, XapianIndexer, PyLuceneIndexer]:
    _declareLegacyIndexerItem(cls, 2)

    registerUpgrader(
        remoteIndexer1to2,
        item.normalize(reflect.qual(cls)),
        1,
        2)
    registerUpgrader(
        remoteIndexer2to3,
        item.normalize(reflect.qual(cls)),
        2,
        3)
del cls

_declareLegacyIndexerItem(PyLuceneIndexer, 3)

# Copy attributes.  Rely on pyLuceneIndexer4to5 to reset the index due to
# sorting changes.
registerAttributeCopyingUpgrader(PyLuceneIndexer, 3, 4)

_declareLegacyIndexerItem(PyLuceneIndexer, 4)

def pyLuceneIndexer4to5(old):
    """
    Copy attributes, reset index due because information about deleted
    documents has been lost, and power up for IFulltextIndexer so other code
    can find this item.
    """
    new = old.upgradeVersion(PyLuceneIndexer.typeName, 4, 5,
                             indexCount=old.indexCount,
                             installedOn=old.installedOn,
                             indexDirectory=old.indexDirectory)
    new.reset()
    new.store.powerUp(new, ixmantissa.IFulltextIndexer)
    return new

registerUpgrader(pyLuceneIndexer4to5, PyLuceneIndexer.typeName, 4, 5)



class _SQLiteResultWrapper(object):
    """
    Trivial wrapper around SQLite FTS search results.
    """
    def __init__(self, docId):
        self.uniqueIdentifier = docId



class _SQLiteIndex(object):
    """
    FTS3 index interface.
    """

    addSQL = """
    INSERT INTO fts (docid, content) VALUES (?, ?)
    """

    removeSQL = """
    DELETE FROM fts WHERE docid = ?
    """

    searchSQL = """
    SELECT docid
    FROM fts
    WHERE content MATCH ?
    ORDER BY docid %s
    """

    def __init__(self, store):
        self.store = store
        self.close = self.store.close


    def add(self, document):
        """
        Add a document to the database.
        """
        docid = int(document.uniqueIdentifier())
        text = u' '.join(document.textParts())

        self.store.executeSQL(self.addSQL, (docid, text))


    def remove(self, docid):
        """
        Remove a document from the database.
        """
        docid = int(docid)
        self.store.executeSQL(self.removeSQL, (docid,))


    def search(self, term, keywords=None, sortAscending=True):
        """
        Search the database.
        """
        if sortAscending:
            direction = 'ASC'
        else:
            direction = 'DESC'

        return [_SQLiteResultWrapper(r[0]) for r in
                self.store.querySQL(self.searchSQL % (direction,), (term,))]



class SQLiteIndexer(RemoteIndexer, item.Item):
    """
    Indexer implementation using SQLite FTS3.

    XXX: Keywords are currently not supported; see #2877
    """
    indexCount = attributes.integer(default=0)
    indexDirectory = attributes.text(default=u'sqlite.index')

    _index = attributes.inmemory()

    schemaSQL = """
    CREATE VIRTUAL TABLE fts
    USING fts3(content)
    """

    def _getStore(self):
        """
        Get the Store used for FTS.

        If it does not exist, it is created and initialised.
        """
        storeDir = self.store.newDirectory(self.indexDirectory)
        if not storeDir.exists():
            store = Store(storeDir)
            self._initStore(store)
            return store
        else:
            return Store(storeDir)


    def _initStore(self, store):
        """
        Initialise a store for FTS use.
        """
        store.createSQL('CREATE VIRTUAL TABLE fts USING fts3')


    def openReadIndex(self):
        return self.openWriteIndex()


    def openWriteIndex(self):
        return _SQLiteIndex(self._getStore())
