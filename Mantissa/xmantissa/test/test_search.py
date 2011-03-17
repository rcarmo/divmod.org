from zope.interface import implements

from twisted.internet import defer

from axiom.store import Store
from axiom.item import Item
from axiom import attributes
from axiom.dependency import installOn

from nevow.testutil import renderLivePage, FragmentWrapper, AccumulatingFakeRequest
from nevow import loaders
from nevow.athena import LiveFragment

from twisted.trial import unittest

from xmantissa import search, ixmantissa
from xmantissa.webtheme import getLoader


class QueryParseTestCase(unittest.TestCase):
    def testPlainTerm(self):
        """
        Test that a regular boring search query with nothing special is parsed
        as such.
        """
        self.assertEquals(search.parseSearchTerm(u"foo"), (u"foo", None))
        self.assertEquals(search.parseSearchTerm(u"foo bar"), (u"foo bar", None))


    def testKeywordTerm(self):
        """
        Test keywords in a search query are found and returned.
        """
        self.assertEquals(
            search.parseSearchTerm(u"foo:bar"),
            (u"", {u"foo": u"bar"}))
        self.assertEquals(
            search.parseSearchTerm(u"foo bar:baz"),
            (u"foo", {u"bar": u"baz"}))
        self.assertEquals(
            search.parseSearchTerm(u"foo bar baz:quux"),
            (u"foo bar", {u"baz": u"quux"}))
        self.assertEquals(
            search.parseSearchTerm(u"foo bar:baz quux"),
            (u"foo quux", {u"bar": u"baz"}))
        self.assertEquals(
            search.parseSearchTerm(u"foo bar:baz quux foobar:barbaz"),
            (u"foo quux", {u"bar": u"baz", u"foobar": u"barbaz"}))


    def testBadlyFormedKeywordTerm(self):
        """
        Test that a keyword search that isn't quite right gets cleaned up.
        """
        self.assertEquals(
            search.parseSearchTerm(u"foo:"),
            (u"foo", None))

        self.assertEquals(
            search.parseSearchTerm(u":foo"),
            (u"foo", None))

        self.assertEquals(
            search.parseSearchTerm(u":"),
            (u"", None))


class TrivialSearchProvider(Item):
    implements(ixmantissa.ISearchProvider)

    z = attributes.integer()
    powerupInterfaces = (ixmantissa.ISearchProvider,)

    def search(self, term, keywords=None, count=None, offset=0, sortAscending=True):
        class TrivialResultsFragment(LiveFragment):
            docFactory = loaders.stan('This is a search result')
        return defer.succeed(TrivialResultsFragment())


class ArgumentPassthroughSearchProvider(Item):
    implements(ixmantissa.ISearchProvider)
    powerupInterfaces = (ixmantissa.ISearchProvider,)
    z = attributes.integer()


    def search(self, *a, **k):
        return defer.succeed((a, k))


class DecodingTestCase(unittest.TestCase):
    """
    Tests for encoding of search terms
    """

    def _renderAggregateSearch(self, charset, term):
        """
        Set up a store, and render an aggregate search, with charset
        C{charset} and search term {term}

        @return: deferred firing with string render result
        """
        s = Store()

        installOn(TrivialSearchProvider(store=s), s)

        agg = search.SearchAggregator(store=s)
        installOn(agg, s)

        f = search.AggregateSearchResults(agg)
        f.docFactory = getLoader(f.fragmentName)

        page = FragmentWrapper(f)

        req = AccumulatingFakeRequest()
        req.args = dict(_charset_=[charset], term=[term])

        result = renderLivePage(page, reqFactory=lambda: req)
        return result

    def testRenderingQueryOK(self):
        """
        Check that a rendered aggregate search yields results if given a valid
        charset and encoded term
        """
        def gotResult(res):
            self.assertIn('This is a search result', res)

        return self._renderAggregateSearch('utf-8', 'r\xc3\xb4').addCallback(gotResult)

    def testRenderingQueryBad(self):
        """
        Check that a rendered aggregate search doesn't contain any results if
        the charset is unknown
        """
        def gotResult(res):
            self.assertIn('Your browser sent', res)

        return self._renderAggregateSearch('divmod-27', 'yeah').addCallback(gotResult)


class AggregatorTestCase(unittest.TestCase):
    """
    Test that the behaviour of L{xmantissa.search.SearchAggregator} conforms
    to L{xmantissa.ixmantissa.ISearchAggregator}
    """

    def test_argsForwarded(self):
        """
        Test that the search aggregator forwards arguments given to C{search}
        to L{xmantissa.ixmantissa.ISearchProvider}s
        """

        s = Store()

        installOn(ArgumentPassthroughSearchProvider(store=s), s)

        agg = search.SearchAggregator(store=s)
        installOn(agg, s)

        args = (((u'foo', {u'bar': u'baz'}), {'sortAscending': False}),
                ((u'bar', {u'foo': u'oof'}), {'sortAscending': True}),
                ((u'', {}), {'sortAscending': True, 'count': 5, 'offset': 1}))

        def checkArgs(gotArgs):
            for ((success, gotArgset), expectedArgset) in zip(gotArgs, args):
                self.assertEquals(gotArgset[0], expectedArgset)

        dl = defer.DeferredList([agg.search(*a[0], **a[1]) for a in args])
        dl.addCallback(checkArgs)
        return dl
