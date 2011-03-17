# -*- test-case-name: xmantissa.test.test_search -*-

from __future__ import division

from zope.interface import implements

from twisted.internet import defer
from twisted.python import log, components

from nevow import inevow, athena, tags

from axiom import attributes, item
from axiom.upgrade import registerDeletionUpgrader

from xmantissa import ixmantissa


class SearchResult(item.Item):
    """
    A temporary, in-database object associated with a particular search (ie,
    one time that one guy typed in that one search phrase) and a single item
    which was found in that search.  These live in the database to make it easy
    to display and sort them, but they are deleted when they get kind of
    oldish.

    These are no longer used.  The upgrader to version 2 unconditionally
    deletes them.
    """
    schemaVersion = 2

    indexedItem = attributes.reference()

    identifier = attributes.integer()

registerDeletionUpgrader(SearchResult, 1, 2)



class SearchAggregator(item.Item):
    implements(ixmantissa.ISearchAggregator, ixmantissa.INavigableElement)

    powerupInterfaces = (ixmantissa.ISearchAggregator, ixmantissa.INavigableElement)
    schemaVersion = 1
    typeName = 'mantissa_search_aggregator'

    installedOn = attributes.reference()
    searches = attributes.integer(default=0)

    # INavigableElement
    def getTabs(self):
        return []


    # ISearchAggregator
    def providers(self):
        return list(self.store.powerupsFor(ixmantissa.ISearchProvider))


    def count(self, term):
        def countedHits(results):
            total = 0
            for (success, result) in results:
                if success:
                    total += result
                else:
                    log.err(result)
            return total

        return defer.DeferredList([
            provider.count(term)
            for provider
            in self.providers()], consumeErrors=True).addCallback(countedHits)


    def search(self, *a, **k):
        self.searches += 1

        d = defer.DeferredList([
            provider.search(*a, **k)
            for provider in self.providers()
            ], consumeErrors=True)

        def searchCompleted(results):
            allSearchResults = []
            for (success, result) in results:
                if success:
                    allSearchResults.append(result)
                else:
                    log.err(result)
            return allSearchResults
        d.addCallback(searchCompleted)

        return d



def parseSearchTerm(term):
    """
    Turn a string search query into a two-tuple of a search term and a
    dictionary of search keywords.
    """
    terms = []
    keywords = {}
    for word in term.split():
        if word.count(':') == 1:
            k, v = word.split(u':')
            if k and v:
                keywords[k] = v
            elif k or v:
                terms.append(k or v)
        else:
            terms.append(word)
    term = u' '.join(terms)
    if keywords:
        return term, keywords
    return term, None



class AggregateSearchResults(athena.LiveFragment):
    fragmentName = 'search'

    def __init__(self, aggregator):
        super(AggregateSearchResults, self).__init__()
        self.aggregator = aggregator


    def head(self):
        return None


    def render_search(self, ctx, data):
        req = inevow.IRequest(ctx)
        term = req.args.get('term', [None])[0]
        charset = req.args.get('_charset_')[0]
        if term is None:
            return ''
        try:
            term = term.decode(charset)
        except LookupError:
            log.err('Unable to decode search query encoded as %s.' % charset)
            return tags.div[
                "Your browser sent your search query in an encoding that we do not understand.",
                tags.br,
                "Please set your browser's character encoding to 'UTF-8' (under the View menu in Firefox)."]
        term, keywords = parseSearchTerm(term)
        d = self.aggregator.search(term, keywords)
        def gotSearchResultFragments(fragments):
            for f in fragments:
                f.setFragmentParent(self)
            return fragments
        d.addCallback(gotSearchResultFragments)
        return d

components.registerAdapter(AggregateSearchResults, SearchAggregator, ixmantissa.INavigableFragment)
