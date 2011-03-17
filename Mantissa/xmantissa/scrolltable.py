# -*- test-case-name: xmantissa.test.test_scrolltable -*-

"""
Scrollable tabular data-display area.

This module provides an API for displaying data from a Twisted server in a
Nevow Athena front-end.
"""

import inspect
import warnings

from zope.interface import implements

from twisted.python.components import registerAdapter
from twisted.python.reflect import qual

from epsilon.extime import Time

from nevow.athena import LiveElement, expose

from axiom.attributes import timestamp, SQLAttribute, AND

from xmantissa.ixmantissa import IWebTranslator, IColumn
from xmantissa.error import Unsortable



TYPE_FRAGMENT = 'fragment'
TYPE_WIDGET = 'widget'



class AttributeColumn(object):
    """
    Implement a mapping between Axiom attributes and the scrolltable-based
    L{IColumn}.
    """
    implements(IColumn)

    def __init__(self, attribute, attributeID=None):
        """
        Create an L{AttributeColumn} from an Axiom attribute.

        @param attribute: an axiom L{SQLAttribute} subclass.

        @param attributeID: an optional client-side identifier for this
        attribute.  Normally this will be this attribute's name; it isn't
        visible to the user on the client, it's simply the client-side internal
        identifier.
        """
        self.attribute = attribute
        if attributeID is None:
            attributeID = attribute.attrname
        self.attributeID = attributeID


    def extractValue(self, model, item):
        """
        Extract a simple value for this column from a given item, suitable for
        serialization via Athena's client-communication layer.

        @param model: The scrollable view object requesting the value.
        Unfortunately due to the long history of this code, this has no clear
        interface, and might be a L{ScrollingElement}, L{ScrollingFragment}, or
        L{xmantissa.tdb.TabularDataModel}, depending on which type this
        L{AttributeColumn} was passed to.

        @param item: An instance of the class that this L{AttributeColumn}'s
        L{attribute} was taken from, to retrieve the value from.

        @return: a value of an attribute of C{item}, of a type dependent upon
        this L{AttributeColumn}'s L{attribute}.
        """
        return self.attribute.__get__(item)


    def sortAttribute(self):
        """
        @return: an L{axiom.attributes.Comparable} that can be used to adjust an
        axiom query to sort the table by this column, or None, if this column
        cannot be sorted by.
        """
        return self.attribute


    def getType(self):
        """
        @return: a string to identify the browser-side type of this column to the
        JavaScript code in Mantissa.ScrollTable.ScrollTable.__init__.
        @rtype: L{str}
        """
        sortattr = self.sortAttribute()
        if sortattr is not None:
            return sortattr.__class__.__name__


    def toComparableValue(self, value):
        """
        Convert C{value} into something that can be compared like-for-like with
        L{sortAttribute}.
        """
        return value



registerAdapter(AttributeColumn, SQLAttribute, IColumn)



# these objects aren't for view junk - they allow the model
# to inform the javascript controller about which columns are
# sortable, as well as supporting non-attribute columns

class TimestampAttributeColumn(AttributeColumn):
    """
    Timestamps are a special case; we need to get the posix timestamp so we can
    send the attribute value to javascript.  we don't register an adapter for
    attributes.timestamp because the TDB model uses IColumn.extractValue() to
    determine the value of the query pivot, and so it needs an extime.Time
    instance, not a float.
    """
    def extractValue(self, model, item):
        val = AttributeColumn.extractValue(self, model, item)
        if val is None:
            raise AttributeError("%r was None" % (self.attribute,))
        return val.asPOSIXTimestamp()


    def getType(self):
        return 'timestamp'


    def toComparableValue(self, value):
        """
        Override L{AttributeColumn}'s implementation to return a L{Time} instance.
        """
        return Time.fromPOSIXTimestamp(value)



class UnsortableColumnWrapper(object):
    """
    Wraps an L{AttributeColumn} and makes it unsortable

    @ivar column: L{AttributeColumn}
    """
    implements(IColumn)

    def __init__(self, column):
        self.column = column
        self.attribute = column.attribute
        self.attributeID = column.attributeID


    def extractValue(self, model, item):
        """
        Delegate to the wrapped column's value extraction method.
        """
        return self.column.extractValue(model, item)


    def sortAttribute(self):
        """
        Prevent sorting on this column by ignoring the wrapped column's sort
        attribute and always returning C{None}.
        """
        return None


    def getType(self):
        """
        Return the wrapped column's type.
        """
        return self.column.getType()



class UnsortableColumn(AttributeColumn):
    """
    An axiom attribute column which does not allow server-side sorting for
    policy or performance reasons.
    """
    def __init__(self, *a, **kw):
        warnings.warn(
            category=DeprecationWarning,
            message=(
                "Use UnsortableColumnWrapper(AttributeColumn(*a, **kw)) instead "
                "of UnsortableColumn(*a, **kw)."),
            stacklevel=2)
        AttributeColumn.__init__(self, *a, **kw)


    def sortAttribute(pelf):
        """
        UnsortableColumns are not sortable, so this will always return L{None}.
        See L{AttributeColumn.sortAttribute}.
        """
        return None


    def getType(self):
        """
        Clobber the inherited implementation to work around the fact that
        sortAttribute returns None so that a useful value is still returned.
        """
        return self.attribute.__class__.__name__



class _ScrollableBase(object):
    """
    _ScrollableBase is an internal base class holding logic for dealing with
    lists of L{xmantissa.ixmantissa.IColumn}s, sorting, and link generation.

    This logic is shared by two quite different implementations of
    client-server communication about rows: L{InequalityModel}, which uses
    techniques specific to the performance characteristics of Axiom queries,
    and L{IndexingModel}, which uses simple indexing logic suitable for
    sequences.
    """
    currentSortColumn = None
    def __init__(self, webTranslator, columns, defaultSortColumn,
                 defaultSortAscending):
        self.webTranslator = webTranslator
        self.columns = {}
        self.columnNames = []
        for col in columns:
            # see comment in TimestampAttributeColumn
            if isinstance(col, timestamp):
                col = TimestampAttributeColumn(col)
            else:
                col = IColumn(col)

            if defaultSortColumn is None:
                defaultSortColumn = col.sortAttribute()
            if (defaultSortColumn is not None
                and col.sortAttribute() is defaultSortColumn):
                self.currentSortColumn = col

            attributeID = unicode(col.attributeID, 'ascii')
            self.columns[attributeID] = col
            self.columnNames.append(attributeID)
        self.isAscending = defaultSortAscending
        if self.currentSortColumn is None:
            self._cannotDetermineSort(defaultSortColumn)


    def _cannotDetermineSort(self, defaultSortColumn):
        """
        This is an internal method designed to be overridden *only* by the classes
        in this module.

        It will be called if:

            * No explicit sort column was specified, and none of the columns
              specified is sortable, or,

            * An explicit sort column was specified, but it is not present in
              the list of columns specified.

        In other words, this method is called when there is no consistent sort
        that can be performed based on the caller's input to the constructor.
        In the default case of the inequality-based model, nothing can be done
        about this, and an exception is raised.  In the old index-based
        scrolltable, certain implicit sorts will appear to work, so those
        continue to work for those tables.  However, Users are advised to avoid
        the index-based scrolltable in general, and this subtly broken implicit
        behavior specifically.

        @param defaultSortColumn: something adaptable to L{IColumn}, or None,
        which subclasses may use to accept a sort that is not related to any
        extant columns in this table.

        @raise: L{Unsortable}, always.  Some subclasses can deal with this case
        better.
        """
        raise Unsortable('you must provide a sortable column')


    def resort(self, columnName):
        """
        Re-sort the table.

        @param columnName: the name of the column to sort by.  This is a string
        because it is passed from the browser.
        """
        csc = self.currentSortColumn
        newSortColumn = self.columns[columnName]
        if newSortColumn is None:
            raise Unsortable('column %r has no sort attribute' % (columnName,))
        if csc is newSortColumn:
            self.isAscending = not self.isAscending
        else:
            self.currentSortColumn = newSortColumn
            self.isAscending = True
        return self.isAscending
    expose(resort)


    def linkToItem(self, item):
        """
        Return a URL that the row for C{item} should link to, by asking the
        L{xmantissa.ixmantissa.IWebTranslator} in C{self.store}

        @return: C{unicode} URL
        """
        return unicode(self.webTranslator.toWebID(item), 'ascii')


    def itemFromLink(self, link):
        """
        Inverse of L{linkToItem}.

        @rtype: L{axiom.item.Item}
        """
        return self.webTranslator.fromWebID(link)



def _webTranslator(store, fallback):
    """
    Discover a web translator based on an Axiom store and a specified default.
    Prefer the specified default.

    This is an implementation detail of various initializers in this module
    which require an L{IWebTranslator} provider.  Some of those initializers
    did not previously require a webTranslator, so this function will issue a
    L{UserWarning} if no L{IWebTranslator} powerup exists for the given store
    and no fallback is provided.

    @param store: an L{axiom.store.Store}
    @param fallback: a provider of L{IWebTranslator}, or None

    @return: 'fallback', if it is provided, or the L{IWebTranslator} powerup on
    'store'.
    """
    if fallback is None:
        fallback = IWebTranslator(store, None)
        if fallback is None:
            warnings.warn(
                "No IWebTranslator plugin when creating Scrolltable - broken "
                "configuration, now deprecated!  Try passing webTranslator "
                "keyword argument.", category=DeprecationWarning,
                stacklevel=4)
    return fallback



class InequalityModel(_ScrollableBase):
    """
    This is a utility base class for things which want to communicate about
    large sets of Axiom items with a remote client.

    The first such implementation is L{ScrollingElement}, which communicates
    with a Nevow Athena JavaScript client.

    @ivar webTranslator: A L{IWebTranslator} provider for resolving and
    creating web links for items.

    @ivar columns: A mapping of attribute identifiers to L{IColumn}
    providers.

    @ivar columnNames: A list of attribute identifiers.

    @ivar isAscending: A boolean indicating the current order of the sort.

    @ivar currentSortColumn: An L{IColumn} representing the current
    sort key.
    """

    def __init__(self, store, itemType, baseConstraint, columns,
                 defaultSortColumn, defaultSortAscending,
                 webTranslator=None):
        """
        Create a new InequalityModel.

        @param store: the store to perform queries against when the client asks
        for data.
        @type store: L{axiom.store.Store}

        @param itemType: the type of item that will be returned by this
        L{InequalityModel}.
        @type itemType: a subclass of L{axiom.item.Item}.

        @param baseConstraint: an L{IQuery} provider that specifies the set of
        rows within this model.

        @param columns: a list of L{IColumn} providers listing the columns to
        be sent to the client.

        @param defaultSortColumn: an element of the C{columns} argument to sort
        by, by default.

        @param defaultSortAscending: is the sort ascending?  XXX: this is not
        implemented and may not even be a good idea to implement.

        @param webTranslator: an L{IWebTranslator} provider used to generate
        IDs for the client from the C{itemType}'s storeID.
        """
        super(InequalityModel, self).__init__(
            _webTranslator(store, webTranslator), columns,
             defaultSortColumn, defaultSortAscending)
        self.store = store
        self.itemType = itemType
        self.baseConstraint = baseConstraint


    def inequalityQuery(self, constraint, count, isAscending):
        """
        Perform a query to obtain some rows from the table represented
        by this model, at the behest of a networked client.

        @param constraint: an additional constraint to apply to the
        query.
        @type constraint: L{axiom.iaxiom.IComparison}.

        @param count: the maximum number of rows to return.
        @type count: C{int}

        @param isAscending: a boolean describing whether the query
        should be yielding ascending or descending results.
        @type isAscending: C{bool}

        @return: an query which will yield some results from this
        model.
        @rtype: L{axiom.iaxiom.IQuery}
        """
        if self.baseConstraint is not None:
            if constraint is not None:
                constraint = AND(self.baseConstraint, constraint)
            else:
                constraint = self.baseConstraint
        # build the sort
        currentSortAttribute = self.currentSortColumn.sortAttribute()
        if isAscending:
            sort = (currentSortAttribute.ascending,
                    self.itemType.storeID.ascending)
        else:
            sort = (currentSortAttribute.descending,
                    self.itemType.storeID.descending)
        return self.store.query(self.itemType, constraint, sort=sort,
                                limit=count).distinct()


    def rowsAfterValue(self, value, count):
        """
        Retrieve some rows at or after a given sort-column value.

        @param value: Starting value in the index for the current sort column
        at which to start returning results.  Rows with a column value for the
        current sort column which is greater than or equal to this value will
        be returned.

        @type value: Some type compatible with the current sort column, or
        None, to specify the beginning of the data.

        @param count: The maximum number of rows to return.
        @type count: C{int}

        @return: A list of row data, ordered by the current sort column,
        beginning at C{value} and containing at most C{count} elements.
        """
        if value is None:
            query = self.inequalityQuery(None, count, True)
        else:
            pyvalue = self._toComparableValue(value)
            currentSortAttribute = self.currentSortColumn.sortAttribute()
            query = self.inequalityQuery(currentSortAttribute >= pyvalue, count, True)
        return self.constructRows(query)
    expose(rowsAfterValue)


    def rowsAfterItem(self, item, count):
        """
        Retrieve some rows after a given item, not including the given item.

        @param item: then L{Item} to request something after.
        @type item: this L{InequalityModel}'s L{itemType} attribute.

        @param count: The maximum number of rows to return.
        @type count: L{int}

        @return: A list of row data, ordered by the current sort column,
        beginning immediately after C{item}.
        """
        currentSortAttribute = self.currentSortColumn.sortAttribute()
        value = currentSortAttribute.__get__(item, type(item))
        firstQuery = self.inequalityQuery(
            AND(currentSortAttribute == value,
                self.itemType.storeID > item.storeID),
            count, True)
        results = self.constructRows(firstQuery)
        count -= len(results)
        if count:
            secondQuery = self.inequalityQuery(
                currentSortAttribute > value,
                count, True)
            results.extend(self.constructRows(secondQuery))
        return results


    def rowsAfterRow(self, rowObject, count):
        """
        Wrapper around L{rowsAfterItem} which accepts the web ID for a item
        instead of the item itself.

        @param rowObject: a dictionary mapping strings to column values, sent
        from the client.  One of those column values must be C{__id__} to
        uniquely identify a row.

        @param count: an integer, the number of rows to return.
        """
        webID = rowObject['__id__']
        return self.rowsAfterItem(
            self.webTranslator.fromWebID(webID),
            count)
    expose(rowsAfterRow)


    def rowsBeforeRow(self, rowObject, count):
        """
        Wrapper around L{rowsBeforeItem} which accepts the web ID for a item
        instead of the item itself.

        @param rowObject: a dictionary mapping strings to column values, sent
        from the client.  One of those column values must be C{__id__} to
        uniquely identify a row.

        @param count: an integer, the number of rows to return.
        """
        webID = rowObject['__id__']
        return self.rowsBeforeItem(
            self.webTranslator.fromWebID(webID),
            count)
    expose(rowsBeforeRow)


    def _toComparableValue(self, value):
        """
        Trivial wrapper which takes into account the possibility that our sort
        column might not have defined the C{toComparableValue} method.

        This can probably serve as a good generic template for some
        infrastructure to deal with arbitrarily-potentially-missing methods
        from certain versions of interfaces, but we didn't take it any further
        than it needed to go for this system's fairly meagre requirements.
        *Please* feel free to refactor upwards as necessary.
        """
        if hasattr(self.currentSortColumn, 'toComparableValue'):
            return self.currentSortColumn.toComparableValue(value)
        # Retrieve the location of the class's definition so that we can alert
        # the user as to where they need to insert their implementation.
        classDef = self.currentSortColumn.__class__
        filename = inspect.getsourcefile(classDef)
        lineno = inspect.findsource(classDef)[1]
        warnings.warn_explicit(
            "IColumn implementor " + qual(self.currentSortColumn.__class__) + " "
            "does not implement method toComparableValue.  This is required since "
            "Mantissa 0.6.6.",
            DeprecationWarning, filename, lineno)
        return value


    def rowsBeforeValue(self, value, count):
        """
        Retrieve display data for rows with sort-column values less than the
        given value.

        @type value: Some type compatible with the current sort column.
        @param value: Starting value in the index for the current sort column
        at which to start returning results.  Rows with a column value for the
        current sort column which is less than this value will be returned.

        @type count: C{int}
        @param count: The number of rows to return.

        @return: A list of row data, ordered by the current sort column, ending
        at C{value} and containing at most C{count} elements.
        """
        if value is None:
            query = self.inequalityQuery(None, count, False)
        else:
            pyvalue = self._toComparableValue(value)
            currentSortAttribute = self.currentSortColumn.sortAttribute()
            query = self.inequalityQuery(
                currentSortAttribute < pyvalue, count, False)
        return self.constructRows(query)[::-1]
    expose(rowsBeforeValue)


    def rowsBeforeItem(self, item, count):
        """
        The inverse of rowsAfterItem.

        @param item: then L{Item} to request rows before.
        @type item: this L{InequalityModel}'s L{itemType} attribute.

        @param count: The maximum number of rows to return.
        @type count: L{int}

        @return: A list of row data, ordered by the current sort column,
        beginning immediately after C{item}.
        """
        currentSortAttribute = self.currentSortColumn.sortAttribute()
        value = currentSortAttribute.__get__(item, type(item))
        firstQuery = self.inequalityQuery(
            AND(currentSortAttribute == value,
                self.itemType.storeID < item.storeID),
            count, False)
        results = self.constructRows(firstQuery)
        count -= len(results)
        if count:
            secondQuery = self.inequalityQuery(currentSortAttribute < value,
                                               count, False)
            results.extend(self.constructRows(secondQuery))
        return results[::-1]



class IndexingModel(_ScrollableBase):
    """
    Mixin for "model" implementations of an in-browser scrollable list of
    elements.

    @ivar webTranslator: A L{IWebTranslator} provider for resolving and
    creating web links for items.

    @ivar columns: A mapping of attribute identifiers to L{IColumn}
    providers.

    @ivar columnNames: A list of attribute identifiers.

    @ivar isAscending: A boolean indicating the current order of the sort.

    @ivar currentSortColumn: An L{IColumn} representing the current
    sort key.
    """
    def requestRowRange(self, rangeBegin, rangeEnd):
        """
        Retrieve display data for the given range of rows.

        @type rangeBegin: C{int}
        @param rangeBegin: The index of the first row to retrieve.

        @type rangeEnd: C{int}
        @param rangeEnd: The index of the last row to retrieve.

        @return: A C{list} of C{dict}s giving row data.
        """
        return self.constructRows(self.performQuery(rangeBegin, rangeEnd))
    expose(requestRowRange)


    # The rest takes care of responding to requests from the client.
    def getTableMetadata(self):
        """
        Retrieve a description of the various properties of this scrolltable.

        @return: A sequence containing 5 elements.  They are, in order, a
        list of the names of the columns present, a mapping of column names
        to two-tuples of their type and a boolean indicating their
        sortability, the total number of rows in the scrolltable, the name
        of the default sort column, and a boolean indicating whether or not
        the current sort order is ascending.
        """
        coltypes = {}
        for (colname, column) in self.columns.iteritems():
            sortable = column.sortAttribute() is not None
            coltype = column.getType()
            if coltype is not None:
                coltype = unicode(coltype, 'ascii')
            coltypes[colname] = (coltype, sortable)

        if self.currentSortColumn:
            csc = unicode(self.currentSortColumn.sortAttribute().attrname, 'ascii')
        else:
            csc = None

        return [self.columnNames, coltypes, self.requestCurrentSize(),
                csc, self.isAscending]
    expose(getTableMetadata)


    def requestCurrentSize(self):
        return self.performCount()
    expose(requestCurrentSize)


    def performAction(self, name, rowID):
        method = getattr(self, 'action_' + name)
        item = self.itemFromLink(rowID)
        return method(item)
    expose(performAction)


    # Override these two in a subclass
    def performCount(self):
        """
        Override this in a subclass.

        @rtype: C{int}
        @return: The total number of elements in this scrollable.
        """
        raise NotImplementedError()


    def performQuery(self, rangeBegin, rangeEnd):
        """
        Override this in a subclass.

        @rtype: C{list}
        @return: Elements from C{rangeBegin} to C{rangeEnd} of the
        underlying data set, as ordered by the value of
        C{currentSortColumn} sort column in the order indicated by
        C{isAscending}.
        """
        raise NotImplementedError()

Scrollable = IndexingModel      # The old (deprecated) name of this class.

class ScrollableView(object):
    """
    Mixin for structuring model data in the way expected by
    Mantissa.ScrollTable.ScrollingWidget.

    Subclasses must also mix in L{_ScrollableBase} to provide required attributes
    and methods.
    """

    jsClass = u'Mantissa.ScrollTable.ScrollingWidget'
    fragmentName = 'scroller'

    def constructRows(self, items):
        """
        Build row objects that are serializable using Athena for sending to the
        client.

        @param items: an iterable of objects compatible with my columns'
        C{extractValue} methods.

        @return: a list of dictionaries, where each dictionary has a string key
        for each column name in my list of columns.
        """
        rows = []
        for item in items:
            row = dict((colname, col.extractValue(self, item))
                       for (colname, col) in self.columns.iteritems())
            link = self.linkToItem(item)
            if link is not None:
                row[u'__id__'] = link
            rows.append(row)

        return rows



class ItemQueryScrollingFragment(IndexingModel, ScrollableView, LiveElement):
    """
    An L{ItemQueryScrollingFragment} is an Athena L{LiveElement} that can
    display an Axiom query using an inefficient, but precise, method for
    counting rows and getting data at given offsets when requested.

    New code which wants to display a scrollable list of data should probably
    use L{ScrollingElement} instead.
    """
    def __init__(self, store, itemType, baseConstraint, columns,
                 defaultSortColumn=None, defaultSortAscending=True,
                 webTranslator=None,
                 *a, **kw):
        self.store = store
        self.itemType = itemType
        self.baseConstraint = baseConstraint
        IndexingModel.__init__(
            self,
            _webTranslator(store, webTranslator),
            columns,
            defaultSortColumn,
            defaultSortAscending)
        LiveElement.__init__(self, *a, **kw)


    def _cannotDetermineSort(self, defaultSortColumn):
        """
        In this old, index-based way of doing things, we can do even more implicit
        horrible stuff to determine the sort column, or even give up completely
        and accept an implicit sort.  NB: this is still terrible behavior, but
        lots of old code relied on it, and since this class is legacy anyway it
        won't be deprecated or removed.

        We can also accept a sort column in this table that is not actually
        displayed or sent to the client at all.
        """
        if defaultSortColumn is not None:
            self.currentSortColumn = IColumn(defaultSortColumn)


    def getInitialArguments(self):
        return [self.getTableMetadata()]


    def performCount(self):
        return self.store.query(self.itemType, self.baseConstraint).count()


    def performQuery(self, rangeBegin, rangeEnd):
        if self.isAscending:
            sort = self.currentSortColumn.sortAttribute().ascending
        else:
            sort = self.currentSortColumn.sortAttribute().descending
        return list(self.store.query(self.itemType,
                                     self.baseConstraint,
                                     offset=rangeBegin,
                                     limit=rangeEnd - rangeBegin,
                                     sort=sort))
ScrollingFragment = ItemQueryScrollingFragment



class SequenceScrollingFragment(IndexingModel, ScrollableView, LiveElement):
    """
    Scrolltable implementation backed by any Python L{axiom.item.Item}
    sequence.
    """
    def __init__(self, store, elements, columns,
                 defaultSortColumn=None,
                 defaultSortAscending=True,
                 webTranslator=None, *a, **kw):
        IndexingModel.__init__(
            self,
            _webTranslator(store, webTranslator),
            columns,
            defaultSortColumn,
            defaultSortAscending)

        LiveElement.__init__(self, *a, **kw)
        self.store = store
        self.elements = elements


    def _cannotDetermineSort(self, defaultSortColumn):
        """
        Since this model back-ends to a fixed-index sequence anyway, we won't be
        sorting by anything and the default sort column will always be None.
        """


    def getInitialArguments(self):
        return [self.getTableMetadata()]


    def performCount(self):
        return len(self.elements)


    def performQuery(self, rangeBegin, rangeEnd):
        step = 1
        if not self.isAscending:
            # The ranges are from the end, not the beginning.
            rangeBegin = max(0, len(self.elements) - rangeBegin - 1)

            # Python is so very very confusing:
            # s[1:0:-1] == []
            # s[1:None:-1] == [s[0]]
            # s[1:-1:-1] == some crazy thing you don't even want to know
            rangeEnd = max(-1, len(self.elements) - rangeEnd - 1)
            if rangeEnd == -1:
                rangeEnd = None
            step = -1
        result = self.elements[rangeBegin:rangeEnd:step]
        return result



class StoreIDSequenceScrollingFragment(SequenceScrollingFragment):
    """
    Scrolltable implementation like L{SequenceScrollingFragment} but which is
    backed by a sequence of Item storeID values rather than Items themselves.
    """
    def performQuery(self, rangeBegin, rangeEnd):
        return map(
            self.store.getItemByID,
            super(
                StoreIDSequenceScrollingFragment,
                self).performQuery(rangeBegin, rangeEnd))


class SearchResultScrollingFragment(SequenceScrollingFragment):
    """
    Scrolltable implementation like L{SequenceScrollingFragment} but which is
    backed by a sequence of L{_PyLuceneHitWrapper} instances.

    XXX _PyLuceneHitWrapper should probably implement IFulltextIndexable instead
    of a subtly different interface.
    """
    def performQuery(self, rangeBegin, rangeEnd):
        results = SequenceScrollingFragment.performQuery(
            self, rangeBegin, rangeEnd)
        return [
            self.store.getItemByID(int(hit.uniqueIdentifier))
            for hit
            in results]



class ScrollingElement(InequalityModel, ScrollableView, LiveElement):
    """
    Element for scrolling lists of items, which uses L{InequalityModel}.
    """
    jsClass = u'Mantissa.ScrollTable.ScrollTable'
    fragmentName = 'inequality-scroller'

    def __init__(self, store, itemType, baseConstraint, columns,
                 defaultSortColumn=None, defaultSortAscending=True,
                 webTranslator=None,
                 *a, **kw):
        InequalityModel.__init__(
            self, store, itemType, baseConstraint, columns,
            defaultSortColumn, defaultSortAscending, webTranslator)
        LiveElement.__init__(self, *a, **kw)


    def _getColumnList(self):
        """
        Get a list of serializable objects that describe the interesting
        columns on our item type.  Columns which report having no type will be
        treated as having the type I{text}.

        @rtype: C{list} of C{dict}
        """
        columnList = []
        for columnName in self.columnNames:
            column = self.columns[columnName]
            type = column.getType()
            if type is None:
                type = 'text'
            columnList.append(
                {u'name': columnName,
                 u'type': type.decode('ascii')})
        return columnList


    def getInitialArguments(self):
        """
        Return the constructor arguments required for the JavaScript client class,
        Mantissa.ScrollTable.ScrollTable.

        @return: a 3-tuple of::

          - The unicode attribute ID of my current sort column
          - A list of dictionaries with 'name' and 'type' keys which are
            strings describing the name and type of all the columns in this
            table.
          - A bool indicating whether the sort direction is initially
            ascending.
        """
        ic = IColumn(self.currentSortColumn)
        return [ic.attributeID.decode('ascii'),
                self._getColumnList(),
                self.isAscending]
