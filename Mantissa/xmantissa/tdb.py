# -*- test-case-name: xmantissa.test.test_tdb -*-

"""
This module is a deprecated version of the code present in
L{xmantissa.scrolltable}.  Look there instead.
"""

import operator
import math
import warnings

from xmantissa.ixmantissa import IColumn
from xmantissa.error import Unsortable
from xmantissa.scrolltable import AttributeColumn as _STAttributeColumn

class AttributeColumn(_STAttributeColumn):
    """
    This a deprecated name for L{xmantissa.scrolltable.AttributeColumn}.  Use
    that instead.
    """

    def __init__(self, *a, **k):
        super(AttributeColumn, self).__init__(*a, **k)
        warnings.warn("tdb.AttributeColumn is deprecated.  "
                      "Use scrolltable.AttributeColumn instead.",
                      DeprecationWarning,
                      stacklevel=2)


from axiom.attributes import AND
from axiom.queryutil import AttributeTuple

class TabularDataModel:
    """
    I represent a window onto a query that can be paged backwards and forward,
    and re-sorted.

    @ivar pageNumber: the number of the current page.

    @ivar totalPages: the total number of pages accessible to the query this
    table is browsing.

    @ivar firstItem: the first visible item

    @ivar lastItem: the last visible item

    @ivar totalItems: the total number of items accessible to the query
    this table is browsing.

    @ivar absolute: whether this pagination result is definitely correct.  in
    some cases it may be necessary to approximate or estimate the total number
    of results, and the UI should reflect this.  True if the number is
    definitely correct, False otherwise.
    """
    def __init__(self, store, primaryTableClass,
                 columns,
                 baseComparison=None,
                 itemsPerPage=20,
                 defaultSortColumn=None,
                 defaultSortAscending=True):
        """@param columns: sequence of objects adaptable to
        L{xmantissa.ixmantissa.IColumn}"""

        self.store = store
        self._currentResults = []
        self.primaryTableClass = primaryTableClass
        assert columns, "You've got to pass some columns"
        cols = self.columns = {}
        for col in map(IColumn, columns):
            if defaultSortColumn is None:
                defaultSortColumn = col.attributeID
            cols[col.attributeID] = col
        self.itemsPerPage = itemsPerPage
        self.baseComparison = baseComparison
        self.isAscending = self.defaultSortAscending = defaultSortAscending
        self.resort(defaultSortColumn,
                    defaultSortAscending)

    currentSortColumn = None # this is set in __init__ by resort()
                             # so client code will never see this value

    def resort(self, attributeID, isAscending=None):
        """Sort by one of my specified columns, identified by attributeID
        """
        if isAscending is None:
            isAscending = self.defaultSortAscending

        newSortColumn = self.columns[attributeID]
        if newSortColumn.sortAttribute() is None:
            raise Unsortable('column %r has no sort attribute' % (attributeID,))
        if self.currentSortColumn == newSortColumn:
            # if this query is to be re-sorted on the same column, but in the
            # opposite direction to our last query, then use the first item in
            # the result set as the marker
            if self.isAscending == isAscending:
                offset = 0
            else:
                # otherwise use the last
                offset = -1
        else:
            offset = 0
            self.currentSortColumn = newSortColumn
        self.isAscending = isAscending
        self._updateResults(self._sortAttributeValue(offset), True)

    def currentPage(self):
        """
        Return a sequence of mappings of attribute IDs to column values, to
        display to the user.

        nextPage/prevPage will strive never to skip items whose column values
        have not been returned by this method.

        This is best explained by a demonstration.  Let's say you have a table
        viewing an item with attributes 'a' and 'b', like this:

        oid | a | b
        ----+---+--
        0   | 1 | 2
        1   | 3 | 4
        2   | 5 | 6
        3   | 7 | 8
        4   | 9 | 0

        The table has 2 items per page.  You call currentPage and receive a
        page which contains items oid 0 and oid 1.  item oid 1 is deleted.

        If the next thing you do is to call nextPage, the result of currentPage
        following that will be items beginning with item oid 2.  This is
        because although there are no longer enough items to populate a full
        page from 0-1, the user has never seen item #2 on a page, so the 'next'
        page from the user's point of view contains #2.

        If instead, at that same point, the next thing you did was to call
        currentPage, *then* nextPage and currentPage again, the first
        currentPage results would contain items #0 and #2; the following
        currentPage results would contain items #3 and #4.  In this case, the
        user *has* seen #2 already, so the user expects to see the following
        item, not the same item again.
        """

        self._updateResults(self._sortAttributeValue(0), equalToStart=True, refresh=True)
        return self._currentResults

    def _updateResults(self, primaryColumnStart=None, equalToStart=False,
                       backwards=False, refresh=False):
        results = self._performQuery(primaryColumnStart,
                                     equalToStart,
                                     backwards)
        if not refresh and len(results) == 0:
            # If we're at the end and going forwards, or at the beginning and
            # going backwards, there are no more page results.  In these cases
            # we should hang on to our previous results, because the user is
            # still looking at the same page, and will expect the next and
            # prev buttons to do the appropriate things.  Realistically
            # speaking, it is a UI bug if this case ever occurs, since the UI
            # should disable the 'next' and 'previous' buttons using the
            # hasNextPage and hasPrevPage methods.  We gracefully handle it
            # anyway simply because we expect multiple frontends for this
            # model, and multiple frontends means lots of places for bugs.
            self.totalItems = self.totalPages = self.pageNumber = 0
            return
        self._currentResults = results
        self._paginate()

    def _determineQuery(self, primaryColumnStart, equalToStart,
                        backwards, limit):
        sortAttribute = self.currentSortColumn.sortAttribute()
        switch = (self.isAscending ^ backwards)
        # if we were sorting ascendingly, or are moving backward in the result
        # set, but not both, then sort this query ascendingly
        # use storeID as a tiebreaker, as in _sortAttributeValue
        tiebreaker = sortAttribute.type.storeID
        if switch:
            sortOrder = sortAttribute.ascending, tiebreaker.ascending
        else: # otherwise not
            sortOrder = sortAttribute.descending, tiebreaker.descending

        # if we were passed a value to use as a marker indicating our position
        # in the result set (typically it would be either the first or last
        # item from the last query)
        if primaryColumnStart is not None:
            # if we want to set the threshold at values equal to the marker
            # value we were given
            if equalToStart:
                # then use <= and >=
                ltgt = operator.__le__, operator.__ge__
            else:
                # otherwise < and >
                ltgt = operator.__lt__, operator.__gt__
            # produce an axiom comparison object by comparing the sort
            # attribute and the marker value using the appropriate operator
            offsetComparison = ltgt[switch](
                AttributeTuple(sortAttribute, tiebreaker), primaryColumnStart)
            # if we were instantiated with an additional comparison, then add
            # that to the comparison object also
            if self.baseComparison is not None:
                comparisonObj = AND(self.baseComparison,
                                    offsetComparison)
            else:
                comparisonObj = offsetComparison
        else:
            # If we've never loaded a page before, start at the beginning
            comparisonObj = self.baseComparison
        return self.store.query(self.primaryTableClass,
                                comparisonObj,
                                sort=sortOrder,
                                limit=limit)

    def _performQuery(self, primaryColumnStart=None, equalToStart=False,
                      backwards=False):
        q = self._determineQuery(primaryColumnStart, equalToStart,
                                 backwards, self.itemsPerPage)
        results = []

        for eachItem in q:
            rowDict = dict(__item__=eachItem)
            for c in self.columns.itervalues():
                rowDict[c.attributeID] = c.extractValue(self, eachItem)
            results.append(rowDict)

        if backwards:
            results.reverse()
        return results

    def _sortAttributeValue(self, offset):
        """
        return the value of the sort attribute for the item at
        'offset' in the results of the last query, otherwise None.
        """
        if self._currentResults:
            pageStart = (self._currentResults[offset][
                self.currentSortColumn.attributeID],
                         self._currentResults[offset][
                    '__item__'].storeID)
        else:
            pageStart = None
        return pageStart

    def nextPage(self):
        self._updateResults(self._sortAttributeValue(-1))

    def hasNextPage(self):
        return bool(self._performQuery(self._sortAttributeValue(-1)))

    def firstPage(self):
        self._updateResults()

    def prevPage(self):
        self._updateResults(self._sortAttributeValue(0), backwards=True)

    def hasPrevPage(self):
        return bool(self._performQuery(self._sortAttributeValue(0), backwards=True))

    def lastPage(self):
        self._updateResults(backwards=True)

    def _paginate(self):
        rslts = self._currentResults
        self.totalItems = self.store.query(self.primaryTableClass,
                                           self.baseComparison).count()
        self.totalPages = int(math.ceil(float(self.totalItems) /
                                        self.itemsPerPage))
        itemsBeforeThisPage = self._determineQuery(
            self._sortAttributeValue(0),
            equalToStart=False, backwards=True, limit=None).count()
        itemsAfterThisPage = self.totalItems - len(rslts) - itemsBeforeThisPage

        self.firstItem = itemsBeforeThisPage + 1
        self.lastItem = (self.firstItem + len(rslts)) - 1

        self.pageNumber = self.totalPages - (
            int(math.ceil(float(itemsAfterThisPage) / self.itemsPerPage)))


class PaginationParameters:

    absolute = True

    def __init__(self, tdm):
        self.tdm = tdm
        self._calculate()

    def _calculate(self):
        # XXX TODO: optimize the crap out of this by pushing its implementation
        # into nextPage/prevPage etc.
        import pprint
        pprint.pprint(self.__dict__)

