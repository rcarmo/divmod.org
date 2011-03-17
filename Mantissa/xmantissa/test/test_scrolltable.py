
"""
This module includes tests for the L{xmantissa.scrolltable} module.
"""

from re import escape

from epsilon.hotfix import require

require("twisted", "trial_assertwarns")

from zope.interface import implements

from twisted.trial import unittest
from twisted.trial.util import suppress as SUPPRESS

from axiom.store import Store
from axiom.item import Item
from axiom.attributes import integer, text
from axiom.dependency import installOn
from axiom.test.util import QueryCounter

from xmantissa.webapp import PrivateApplication
from xmantissa.ixmantissa import IWebTranslator, IColumn
from xmantissa.error import Unsortable


from xmantissa.scrolltable import (
    InequalityModel,
    ScrollableView,
    ScrollingFragment,
    ScrollingElement,
    SequenceScrollingFragment,
    StoreIDSequenceScrollingFragment,
    AttributeColumn,
    UnsortableColumnWrapper,
    UnsortableColumn)


_unsortableColumnSuppression = SUPPRESS(
    message=escape(
        "Use UnsortableColumnWrapper(AttributeColumn(*a, **kw)) "
        "instead of UnsortableColumn(*a, **kw)."),
    category=DeprecationWarning)



class DataThunk(Item):
    a = integer()
    b = integer()
    c = text()



class DataThunkWithIndex(Item):
    """
    Another testing utility, similar to L{DataThunk}, but with an indexed
    attribute, so that sorting complexity is independent of the number of
    instances which exist, so that performance testing can be done.
    """
    a = integer(indexed=True)



class ScrollTestMixin(object):
    def setUp(self):
        self.store = Store()
        installOn(PrivateApplication(store=self.store), self.store)
        self.six = DataThunk(a=6, b=8157, c=u'six', store=self.store)
        self.three = DataThunk(a=3, b=821375, c=u'three', store=self.store)
        self.seven = DataThunk(a=7, b=4724, c=u'seven', store=self.store)
        self.eight = DataThunk(a=8, b=61, c=u'eight', store=self.store)
        self.one = DataThunk(a=1, b=435716, c=u'one', store=self.store)
        self.two = DataThunk(a=2, b=67145, c=u'two', store=self.store)
        self.four = DataThunk(a=4, b=6327, c=u'four', store=self.store)
        self.five = DataThunk(a=5, b=91856, c=u'five', store=self.store)
        self.scrollFragment = self.getScrollFragment()


    def test_performQueryAscending(self):
        """
        Test that some simple ranges can be correctly retrieved when the sort
        order is ascending on the default column.
        """
        self.scrollFragment.isAscending = True
        for low, high in [(0, 2), (1, 3), (2, 4)]:
            self.assertEquals(
                self.scrollFragment.performQuery(low, high),
                [self.five, self.six, self.seven, self.eight][low:high])


    def test_performQueryDescending(self):
        """
        Like L{test_performQueryAscending} but for the descending sort order.
        """
        self.scrollFragment.isAscending = False
        for low, high in [(0, 2), (1, 3), (2, 4)]:
            self.assertEquals(
                self.scrollFragment.performQuery(low, high),
                [self.eight, self.seven, self.six, self.five][low:high])



class ScrollingFragmentTestCase(ScrollTestMixin,
                                unittest.TestCase):
    """
    Test cases which simulate various client behaviors to exercise the legacy
    L{ScrollingFragment}.
    """
    def getScrollFragment(self):
        sf = ScrollingFragment(
            self.store, DataThunk, DataThunk.a > 4,
            [DataThunk.b, DataThunk.c], DataThunk.a)
        sf.linkToItem = lambda ign: None
        return sf


    def testGetTwoChunks(self):
        self.assertEquals(
            self.scrollFragment.requestRowRange(0, 2),
            [{'c': u'five', 'b': 91856}, {'c': u'six', 'b': 8157}])

        self.assertEquals(
            self.scrollFragment.requestRowRange(2, 4),
            [{'c': u'seven', 'b': 4724}, {'c': u'eight', 'b': 61}])

        self.scrollFragment.resort('b')

        self.assertEquals(self.scrollFragment.requestRowRange(0, 2),
                          [{'c': u'eight', 'b': 61}, {'c': u'seven', 'b': 4724}])
        self.assertEquals(self.scrollFragment.requestRowRange(2, 4),
                          [{'c': u'six', 'b': 8157}, {'c': u'five', 'b': 91856}])


    def testSortsOnFirstSortable(self):
        """
        Test that the scrolltable sorts on the first sortable column
        """
        sf = ScrollingFragment(
                self.store, DataThunk, None,
                (UnsortableColumn(DataThunk.a),
                 DataThunk.b))
        self.assertEquals(sf.currentSortColumn, DataThunk.b)
    testSortsOnFirstSortable.suppress = [_unsortableColumnSuppression]


    def testSortsOnFirstSortable2(self):
        """
        Same as L{testSortsOnFirstSortable}, but for the case where the first
        sortable column is the first in the column list
        """
        sf = ScrollingFragment(
                self.store, DataThunk, None,
                (DataThunk.a, UnsortableColumn(DataThunk.b)))

        self.assertIdentical(sf.currentSortColumn.sortAttribute(),
                             DataThunk.a)
    testSortsOnFirstSortable2.suppress = [_unsortableColumnSuppression]


    def testTestNoSortables(self):
        """
        Test that the scrolltable can handle the case where all columns are
        unsortable
        """
        sf = ScrollingFragment(
                self.store, DataThunk, None,
                (UnsortableColumn(DataThunk.a),
                 UnsortableColumn(DataThunk.b)))

        self.assertEquals(sf.currentSortColumn, None)
    testTestNoSortables.suppress = [_unsortableColumnSuppression]


    def test_unsortableColumnType(self):
        """
        L{UnsortableColumn.getType} should return the same value as
        L{AttributeColumn.getType} for a particular attribute.
        """
        self.assertEqual(
            AttributeColumn(DataThunk.a).getType(),
            UnsortableColumn(DataThunk.a).getType())
    test_unsortableColumnType.suppress = [_unsortableColumnSuppression]


    def test_unsortableColumnDeprecated(self):
        """
        L{UnsortableColumn} is a deprecated almost-alias for
        L{UnsortableColumnWrapper}.
        """
        self.assertWarns(
            DeprecationWarning,
            "Use UnsortableColumnWrapper(AttributeColumn(*a, **kw)) "
            "instead of UnsortableColumn(*a, **kw).",
            __file__,
            lambda: UnsortableColumn(DataThunk.a))


    def testUnsortableColumnWrapper(self):
        """
        Test that an L{UnsortableColumnWrapper} wrapping an L{AttributeColumn}
        is treated the same as L{UnsortableColumn}
        """
        sf = ScrollingFragment(
                self.store, DataThunk, None,
                (UnsortableColumnWrapper(AttributeColumn(DataThunk.a)),
                 DataThunk.b))

        self.assertEquals(sf.currentSortColumn, DataThunk.b)


    def test_allUnsortableSortMetadata(self):
        """
        Test that C{getTableMetadata} is correct with respect to the
        sortability of columns
        """
        sf = ScrollingFragment(
                self.store, DataThunk, None,
                (UnsortableColumn(DataThunk.a),
                 UnsortableColumn(DataThunk.b)))

        meta = sf.getTableMetadata()
        cols = meta[1]
        self.assertEquals(cols['a'][1], False)
        self.assertEquals(cols['b'][1], False)
    test_allUnsortableSortMetadata.suppress = [_unsortableColumnSuppression]


    def test_oneSortableSortMetadata(self):
        """
        Same as L{test_allUnsortableSortMetadata}, but with one sortable column
        """
        sf = ScrollingFragment(
                self.store, DataThunk, None,
                (DataThunk.a,
                 UnsortableColumn(DataThunk.b)))

        meta = sf.getTableMetadata()
        cols = meta[1]
        self.assertEquals(cols['a'][1], True)
        self.assertEquals(cols['b'][1], False)
    test_oneSortableSortMetadata.suppress = [_unsortableColumnSuppression]



class SequenceScrollingFragmentTestCase(ScrollTestMixin, unittest.TestCase):
    """
    Run the general scrolling tests against L{SequenceScrollingFragment}.
    """
    def getScrollFragment(self):
        return SequenceScrollingFragment(
            self.store,
            [self.five, self.six, self.seven, self.eight],
            [DataThunk.b, DataThunk.c], DataThunk.a)


class StoreIDSequenceScrollingFragmentTestCase(ScrollTestMixin, unittest.TestCase):
    """
    Run the general scrolling tests against
    L{StoreIDSequenceScrollingFragmentTestCase}.
    """
    def getScrollFragment(self):
        return StoreIDSequenceScrollingFragment(
            self.store,
            [self.five.storeID, self.six.storeID,
             self.seven.storeID, self.eight.storeID],
            [DataThunk.b, DataThunk.c], DataThunk.a)



class TestableInequalityModel(InequalityModel):
    """
    Helper for InequalityModel tests which implements the row construction
    hook.
    """
    def constructRows(self, items):
        """
        Squash the given items iterator into a list and return it so it can be
        inspected by tests.
        """
        return list(items)



class InequalityModelTestCase(unittest.TestCase):
    """
    Tests for the inequality-based scrolling model implemented by
    L{InequalityModel}.
    """
    def setUp(self):
        """
        Set up an inequality model (by way of L{TestableInequalityModel}) backed by
        a user store with some sample data, and an L{IWebTranslator} powerup,
        to provide a somewhat realistic test setup.

        The data provided has some duplicates in the sort column, and it is
        intentionally inserted out of order, so that storeID order and sort
        column ordering will not coincide.
        """
        self.store = Store()
        privApp = PrivateApplication(store=self.store)
        installOn(privApp, self.store)

        self.data = []
        for a, b, c in [(9, 1928, u'nine'), (1, 983, u'one'),
                        (8, 843, u'eight'), (2, 827, u'two'),
                        # (8, 1874, u'eight (DUP)'), (2, 294, u'two (DUP)'),
                        (7, 18, u'seven'), (3, 19, u'three'),
                        (6, 218, u'six'), (4, 2198, u'four'),
                        (5, 1982, u'five'), (0, 10, u'zero')]:
            self.data.append(DataThunk(store=self.store, a=a, b=b, c=c))
        self.data.sort(key=lambda item: (item.a, item.storeID))

        self.model = TestableInequalityModel(
            self.store,
            DataThunk,
            None,
            [DataThunk.a,
             DataThunk.b,
             DataThunk.c],
            DataThunk.a,
            True)


    def test_noSortableColumns(self):
        """
        Attempting to construct a L{InequalityModel} without any sortable columns
        should result in a L{Unsortable} exception being thrown.
        """
        makeModel = lambda: InequalityModel(self.store, DataThunk, None,
                                            [UnsortableColumn(DataThunk.a)],
                                            None, True)
        self.assertRaises(Unsortable, makeModel)
    test_noSortableColumns = [_unsortableColumnSuppression]


    def test_rowsAtStart(self):
        """
        Verify that retrieving rows after the "None" value will retrieve rows at
        the start of the order.
        """
        count = 5
        expected = self.data[:count]
        self.assertEquals(self.model.rowsAfterValue(None, count),
                          expected)


    def test_rowsAtEnd(self):
        """
        Verify that retrieving rows before the "None" value will retrieve rows
        at the end of the sort order.
        """
        count = 5
        expected = self.data[-count:]
        self.assertEquals(self.model.rowsBeforeValue(None, count),
                          expected)


    def test_rowsAfterValue(self):
        """
        Verify that rows after a particular value with a particular ordering
        are returned by L{InequalityModel.rowsAfterValue}.
        """
        for count in range(1, len(self.data)):
            for value in range(len(self.data)):
                expected = self.data[value:value + count]
                self.assertEqual(
                    self.model.rowsAfterValue(value, count),
                    expected)


    def test_rowsAfterRow(self):
        """
        Verify that the exposed method, L{rowsAfterRow}, returns results comparable
        to the logical method, L{rowsAfterItem}.
        """
        args = []
        def rowsAfterItem(item, count):
            args.append((item, count))
        self.model.rowsAfterItem = rowsAfterItem
        theItem = object()
        theTranslator = FakeTranslator()
        theTranslator.fromWebID = lambda webID: theItem
        self.model.webTranslator = theTranslator
        self.model.rowsAfterRow({u'__id__': u'webid!'}, 10)
        self.assertEqual(args, [(theItem, 10)])


    def test_rowsBeforeRow(self):
        """
        Verify that the exposed method, L{rowsBeforeRow}, return results comparable
        to the logical method, L{rowsBeforeItem}.
        """
        args = []
        def rowsBeforeItem(item, count):
            args.append((item, count))
        self.model.rowsBeforeItem = rowsBeforeItem
        theItem = object()
        theTranslator = FakeTranslator()
        theTranslator.fromWebID = lambda webID: theItem
        self.model.webTranslator = theTranslator
        self.model.rowsBeforeRow({u'__id__': u'webid!'}, 10)
        self.assertEqual(args, [(theItem, 10)])


    def test_rowsAfterItem(self):
        """
        Verify that rows after a particular item with a particular ordering are
        returned by L{InequalityModel.rowsAfterItem}.
        """
        for count in range(1, len(self.data)):
            for value in range(1, len(self.data)):
                expected = self.data[value:value + count]
                self.assertEqual(
                    self.model.rowsAfterItem(self.data[value - 1], count),
                    expected)



    def test_rowsBeforeValue(self):
        """
        Like L{test_rowsAfterValue} but for data going in the opposite
        direction.
        """
        for count in range(1, len(self.data)):
            for value in range(len(self.data)):
                expected = self.data[max(value - count, 0):value]
                self.assertEqual(
                    self.model.rowsBeforeValue(value, count),
                    expected)


    def test_rowsBeforeItem(self):
        """
        Like L{test_rowsAfterItem} but for data going in the opposite
        direction.
        """
        for count in range(1, len(self.data)):
            for value in range(len(self.data)):
                expected = self.data[max(value - count, 0):value]
                self.assertEqual(
                    self.model.rowsBeforeItem(self.data[value], count),
                    expected)



class FakeTranslator:
    """
    A fake implementation of the L{IWebTranslator} interface, for tests which
    do not use this.
    """
    implements(IWebTranslator)
    def fromWebID(self, webID):
        return None
    def toWebID(self, item):
        return "none"
    def linkTo(self, storeID):
        return "none"
    def linkFrom(self, webID):
        return 0


class ScrollingElementTests(unittest.TestCase):
    """
    Test cases for the ultimate client-facing subclass, L{ScrollingElement}.
    """
    def test_deprecatedMissingWebTranslator(self):
        """
        Instantiating a L{ScrollingElement} without supplying an
        L{IWebTranslator}, either explicitly or via a store powerup, will
        emit a L{DeprecationWarning} explaining that this should not be
        done.
        """
        def makeScrollingElement():
            return ScrollingElement(
                Store(), DataThunk, None, [DataThunk.a], DataThunk.a, True)
        self.assertWarns(
            DeprecationWarning,
            "No IWebTranslator plugin when creating Scrolltable - broken "
            "configuration, now deprecated!  Try passing webTranslator "
            "keyword argument.",
            __file__,
            makeScrollingElement)


    def test_callComparableValue(self):
        """
        L{ScrollingElement} should attempt to call L{IColumn.toComparableValue} to
        translate input from JavaScript if it is provided by the sort column.
        """
        calledWithValues = []
        column = AttributeColumn(DataThunk.a)
        column.toComparableValue = lambda v: (calledWithValues.append(v), 0)[1]
        scrollingElement = ScrollingElement(
            Store(), DataThunk, None, [column], webTranslator=FakeTranslator())
        scrollingElement.rowsAfterValue(16, 10)
        self.assertEqual(calledWithValues, [16])
        calledWithValues.pop()
        scrollingElement.rowsBeforeValue(11, 10)
        self.assertEqual(calledWithValues, [11])


    def test_deprecatedNoToComparableValue(self):
        """
        If L{IColumn.toComparableValue} is I{not} provided by the sort column,
        then L{ScrollingElement} should notify the developer of a deprecation
        warning but default to using the value itself.
        """
        class FakeComparator:
            def __ge__(fc, other):
                self.shouldBeFakeValue = other
            __lt__ = __ge__
        theFakeComparator = FakeComparator()
        class FakeOldColumn:
            implements(IColumn) # but not really; we're missing something!
            attributeID = 'fake'
            def sortAttribute(self):
                return theFakeComparator

        scrollingElement = ScrollingElement(
            Store(), DataThunk, None, [FakeOldColumn()],
            webTranslator=FakeTranslator())

       # Now, completely hamstring the implementation; we are interested in
       # something very specific here, so we just want to capture one value.
       # (Passing it further on, for example to Axiom, would not result in
       # testing anything useful, since it is the individual column's
       # responsibility to yield useful values here anyway, and this test is
       # explicitly for the case where it's *not* doing that, but happened to
       # work before anyway!)

        scrollingElement.inequalityQuery = lambda a, b, c: None
        scrollingElement.constructRows = lambda nothing : ()
        for lenientMethod in [scrollingElement.rowsBeforeValue,
                              scrollingElement.rowsAfterValue]:
            fakeValue = object()
            self.assertWarns(DeprecationWarning,
                             "IColumn implementor %s.FakeOldColumn does not "
                             "implement method toComparableValue.  This is "
                             "required since Mantissa 0.6.6." % (__name__,),
                             __file__, lenientMethod, fakeValue, 10)
            self.assertIdentical(fakeValue, self.shouldBeFakeValue)


    def test_initialWidgetArguments(self):
        """
        Verify that the arguments the client widget expects: the name of the
        current sort column, a list of the available data columns, and the sort
        order.
        """
        s = Store()
        testElement = ScrollingElement(s, DataThunk, None,
                                       [DataThunk.a, DataThunk.c],
                                       DataThunk.a, True,
                                       FakeTranslator())
        self.assertEqual(testElement.getInitialArguments(),
                         [u"a",
                         [{u"name": u"a",
                           u"type": u"integer"},
                          {u"name": u"c",
                           u"type": u"text"}],
                          True])


    def test_missingTypeDefaultsToText(self):
        """
        When constructed with an L{IColumn} which returns C{None} from its
        C{getType} method, L{ScrollingElement} should use the default of
        C{text} for that column's type.
        """
        class UntypedColumn(object):
            implements(IColumn)
            attributeID = 'foo'
            def sortAttribute(self):
                return None
            def getType(self):
                return None
        column = UntypedColumn()

        scroller = ScrollingElement(
            None, None, None, [DataThunk.a, column], None,
            webTranslator=object())
        attribute, columnList, ascending = scroller.getInitialArguments()
        self.assertEqual(
            columnList,
            [{u'type': u'integer', u'name': u'a'},
             {u'type': u'text', u'name': u'foo'}])



class InequalityModelDuplicatesTestCase(unittest.TestCase):
    """
    Similar to L{InequalityModelTestCase}, but test cases where there are
    multiple rows with the same value for the sort key.
    """
    def setUp(self):
        self.store = Store()
        privApp = PrivateApplication(store=self.store)
        installOn(privApp, self.store)

        # Create some data to test with in an order which is not naturally
        # sorted in any way.

        # 4 1s, 4 0s, 4 2s
        self.data = []
        for number in [1, 0, 2, 2, 0, 1, 1, 0, 2, 0, 2, 1]:
            self.data.append(DataThunk(store=self.store, a=number))

        # But order it for the sake of simplicity while testing.
        self.data.sort(key=lambda item: (item.a, item.storeID))

        self.model = TestableInequalityModel(
            self.store,
            DataThunk,
            None,
            [DataThunk.a,
             DataThunk.b,
             DataThunk.c],
            DataThunk.a,
            True)


    def test_rowsAfterValue(self):
        """
        Test that when there are duplicate values in the sort column,
        L{InequalityModel.rowsAfterValue} returns all the rows (up to the
        indicated maximum) with the value it is passed and then any rows with
        values greater than the given value.
        """
        self.assertEqual(
            self.model.rowsAfterValue(1, 3),
            self.data[4:4+3])


    def test_rowsAfterItem(self):
        """
        Like L{test_rowsAfterValue}, but for L{InequalityModel.rowsAfterItem}
        method.
        """
        # Test that starting at the first item with a particular value and
        # crossing over to another value works properly.
        self.assertEqual(
            self.model.rowsAfterItem(self.data[0], 3),
            self.data[1:4])
        # Test that starting at an item "in the middle" of a particular value
        # and crossing over to another value works properly.
        self.assertEqual(
            self.model.rowsAfterItem(self.data[1], 3),
            self.data[2:5])
        # Test that starting at the first item with a particular value and not
        # requesting enough rows to cross into another value works properly.
        self.assertEqual(
            self.model.rowsAfterItem(self.data[0], 1),
            [self.data[1]])


    def test_rowsBeforeValue(self):
        """
        Like L{test_rowsAfterValue}, but for L{InequalityModel.rowsBeforeValue}
        """
        self.assertEqual(
            self.model.rowsBeforeValue(2, 3),
            self.data[5:8])


    def test_rowsBeforeItem(self):
        """
        Like L{test_rowsAfterItem}, but for L{InequalityModel.rowsBeforeItem}.
        """
        for x in range(len(self.data)):
            self.assertEqual(
                self.model.rowsBeforeItem(self.data[x], 20),
                self.data[:x])




class InequalityPerformanceTests(unittest.TestCase):
    """
    Tests for the complexity and runtime costs of the methods of
    L{InequalityModel}.
    """
    def setUp(self):
        self.store = Store()
        privApp = PrivateApplication(store=self.store)
        installOn(privApp, self.store)
        self.model = TestableInequalityModel(
            self.store,
            DataThunkWithIndex,
            None,
            [DataThunkWithIndex.a],
            DataThunkWithIndex.a,
            True,
            privApp)
        self.counter = QueryCounter(self.store)
        self.data = []
        for i in range(4):
            self.data.append(DataThunkWithIndex(store=self.store, a=i))


    def rowsAfterValue(self, value, count):
        return self.counter.measure(self.model.rowsAfterValue, value, count)


    def rowsAfterItem(self, item, count):
        return self.counter.measure(self.model.rowsAfterItem, item, count)


    def rowsBeforeValue(self, value, count):
        return self.counter.measure(self.model.rowsBeforeValue, value, count)


    def rowsBeforeItem(self, item, count):
        return self.counter.measure(self.model.rowsBeforeItem, item, count)


    def test_rowsAfterValue(self):
        """
        Verify that the cost of L{InequalityModel.rowsAfterValue} is
        independent of the total number of rows in the table being queried, as
        long as that number is greater than the number of rows requested.
        """
        first = self.rowsAfterValue(1, 2)
        DataThunkWithIndex(store=self.store, a=4)
        second = self.rowsAfterValue(1, 2)
        self.assertEqual(first, second)


    def test_rowsAfterValueWithDuplicatesBeforeStart(self):
        """
        Like L{test_rowsAfterValue}, but verify the behavior in the face of
        duplicate rows before the start value.
        """
        first = self.rowsAfterValue(1, 2)
        DataThunkWithIndex(store=self.store, a=0)
        second = self.rowsAfterValue(1, 2)
        self.assertEqual(first, second)


    def test_rowsAfterValueWithDuplicatesAtStart(self):
        """
        Like L{test_rowsAfterValue}, but verify the behavior in the face of
        duplicate rows exactly at the start value.
        """
        first = self.rowsAfterValue(1, 2)
        DataThunkWithIndex(store=self.store, a=1)
        second = self.rowsAfterValue(1, 2)
        self.assertEqual(first, second)


    def test_rowsAfterValueWithDuplicatesInResult(self):
        """
        Like L{test_rowsAfterValue}, but verify the behavior in the face of
        duplicate rows in the result set.
        """
        first = self.rowsAfterValue(1, 2)
        DataThunkWithIndex(store=self.store, a=2)
        second = self.rowsAfterValue(1, 2)
        self.assertEqual(first, second)


    def test_rowsAfterValueWithDuplicatesAfter(self):
        """
        Like L{test_rowsAfterValue}, but verify the behavior in the face of
        duplicate rows past the end of the result set.
        """
        first = self.rowsAfterValue(1, 2)
        DataThunkWithIndex(store=self.store, a=4)
        second = self.rowsAfterValue(1, 2)
        self.assertEqual(first, second)


    def test_rowsAfterItem(self):
        """
        Like L{test_rowsAfterValue}, but for L{InequalityModel.rowsAfterItem}.
        """
        first = self.rowsAfterItem(self.data[0], 2)
        DataThunkWithIndex(store=self.store, a=4)
        second = self.rowsAfterItem(self.data[0], 2)
        self.assertEqual(first, second)


    def test_rowsAfterItemWithDuplicatesBeforeStart(self):
        """
        Like L{test_rowsAfterValueWithDuplicatesBeforeStart}, but for
        L{InequalityModel.rowsAfterItem}.
        """
        DataThunkWithIndex(store=self.store, a=-1)
        first = self.rowsAfterItem(self.data[0], 2)
        DataThunkWithIndex(store=self.store, a=-1)
        second = self.rowsAfterItem(self.data[0], 2)
        self.assertEqual(first, second)


    def test_rowsAfterItemWithDuplicatesAtStart(self):
        """
        Like L{test_rowsAfterValueWithDuplicatesAtStart}, but for
        L{InequalityModel.rowsAfterItem}.
        """
        first = self.rowsAfterItem(self.data[0], 2)
        DataThunkWithIndex(store=self.store, a=0)
        second = self.rowsAfterItem(self.data[0], 2)
        self.assertEqual(first, second)
    test_rowsAfterItemWithDuplicatesAtStart.todo = (
        "Index scan to find appropriate storeID starting point once the "
        "value index has been used to seek to /near/ the correct starting "
        "place causes this to be O(N) on the number of rows with duplicate "
        "values.")


    def test_rowsAfterItemWithDuplicatesInResult(self):
        """
        Like L{test_rowsAfterValueWithDuplicatesInResult}, but for
        L{InequalityModel.rowsAfterItem}.
        """
        first = self.rowsAfterItem(self.data[0], 2)
        DataThunkWithIndex(store=self.store, a=1)
        second = self.rowsAfterItem(self.data[0], 2)
        self.assertEqual(first, second)


    def test_rowsAfterItemWithDuplicatesAfter(self):
        """
        Like L{test_rowsAfterValueWithDuplicatesAfter}, but for
        L{InequalityModel.rowsAfterItem}.
        """
        first = self.rowsAfterItem(self.data[0], 2)
        DataThunkWithIndex(store=self.store, a=3)
        second = self.rowsAfterItem(self.data[0], 2)
        self.assertEqual(first, second)


    def test_rowsBeforeValue(self):
        """
        Like L{test_rowsAfterValue}, but for
        L{InequalityModel.rowsBeforeValue}.
        """
        first = self.rowsBeforeValue(2, 2)
        DataThunkWithIndex(store=self.store, a=-1)
        second = self.rowsBeforeValue(2, 2)
        self.assertEqual(first, second)


    def test_rowsBeforeValueWithDuplicatesBeforeStart(self):
        """
        Like L{test_rowsAfterValueWithDuplicatesBeforeStart}, but for
        L{InequalityModel.rowsBeforeValue}.
        """
        first = self.rowsBeforeValue(2, 2)
        DataThunkWithIndex(store=self.store, a=3)
        second = self.rowsBeforeValue(2, 2)
        self.assertEqual(first, second)


    def test_rowsBeforeValueWithDuplicatesAtStart(self):
        """
        Like L{test_rowsAfterValueWithDuplicatesAtStart}, but for
        L{InequalityModel.rowsBeforeValue}.
        """
        first = self.rowsBeforeValue(2, 2)
        DataThunkWithIndex(store=self.store, a=2)
        second = self.rowsBeforeValue(2, 2)
        self.assertEqual(first, second)


    def test_rowsBeforeValueWithDuplicatesInResult(self):
        """
        Like L{test_rowsAfterValueWithDuplicatesInResult}, but for
        L{InequalityModel.rowsBeforeValue}.
        """
        first = self.rowsBeforeValue(2, 2)
        DataThunkWithIndex(store=self.store, a=1)
        second = self.rowsBeforeValue(2, 2)
        self.assertEqual(first, second)


    def test_rowsBeforeValueWithDuplicatesAfter(self):
        """
        Like L{test_rowsAfterValueWithDuplicatesAfter}, but for
        L{InequalityModel.rowsBeforeValue}.
        """
        first = self.rowsBeforeValue(2, 2)
        DataThunkWithIndex(store=self.store, a=0)
        second = self.rowsBeforeValue(2, 2)
        self.assertEqual(first, second)


    def test_rowsBeforeItem(self):
        """
        Like L{test_rowsAfterItem}, but for L{InequalityModel.rowsBeforeItem}.
        """
        first = self.rowsBeforeItem(self.data[3], 2)
        DataThunkWithIndex(store=self.store, a=-1)
        second = self.rowsBeforeItem(self.data[3], 2)
        self.assertEqual(first, second)


    def test_rowsBeforeItemWithDuplicatesBeforeStart(self):
        """
        Like L{test_rowsAfterItemWithDuplicatesBeforeStart}, but for
        L{InequalityModel.rowsBeforeItem}.
        """
        DataThunkWithIndex(store=self.store, a=4)
        first = self.rowsBeforeItem(self.data[3], 2)
        DataThunkWithIndex(store=self.store, a=4)
        second = self.rowsBeforeItem(self.data[3], 2)
        self.assertEqual(first, second)


    def test_rowsBeforeItemWithDuplicatesAtStart(self):
        """
        Like L{test_rowsAfterItemWithDuplicatesAtStart}, but for
        L{Inequality.rowsBeforeItem}.
        """
        first = self.rowsBeforeItem(self.data[3], 2)
        DataThunkWithIndex(store=self.store, a=3)
        second = self.rowsBeforeItem(self.data[3], 2)
        self.assertEqual(first, second)
    test_rowsBeforeItemWithDuplicatesAtStart.todo = (
        "Index scan to find appropriate storeID starting point once the "
        "value index has been used to seek to /near/ the correct starting "
        "place causes this to be O(N) on the number of rows with duplicate "
        "values.")


    def test_rowsBeforeItemWithDuplicatesInResult(self):
        """
        Like L{test_rowsAfterItemWithDuplicatesInResult}, but for
        L{Inequality.rowsBeforeItem}.
        """
        first = self.rowsBeforeItem(self.data[3], 2)
        DataThunkWithIndex(store=self.store, a=2)
        second = self.rowsBeforeItem(self.data[3], 2)
        self.assertEqual(first, second)


    def test_rowsBeforeItemWithDuplicatesAfter(self):
        """
        Like L{test_rowsAfterItemWithDuplicatesAfter}, but for
        L{InequalityModel.rowsBeforeItem}.
        """
        first = self.rowsBeforeItem(self.data[3], 2)
        DataThunkWithIndex(store=self.store, a=0)
        second = self.rowsBeforeItem(self.data[3], 2)
        self.assertEqual(first, second)




class UnsortableColumnWrapperTestCase(unittest.TestCase):
    """
    Tests for L{UnsortableColumnWrapper}
    """

    def test_unsortableColumnWrapper(self):
        attr = DataThunk.a
        col = AttributeColumn(attr)
        unsortableCol = UnsortableColumnWrapper(col)

        item = DataThunk(store=Store(), a=26)

        value = unsortableCol.extractValue(None, item)
        self.assertEquals(value, item.a)
        self.assertEquals(value, col.extractValue(None, item))

        typ = unsortableCol.getType()
        self.assertEquals(typ, 'integer')
        self.assertEquals(typ, col.getType())

        self.assertEquals(unsortableCol.sortAttribute(), None)
