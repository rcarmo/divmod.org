
from epsilon.hotfix import require

require("twisted", "trial_assertwarns")

from axiom.store import Store
from axiom.item import Item
from axiom.attributes import integer, text, AND
from twisted.trial import unittest

from xmantissa import tdb, scrolltable

class X(Item):
    typeName = 'test_tdb_model_dummy'
    schemaVersion = 1

    number = integer()
    textNumber = text()
    phoneticDigits = text()

digits = ['zero',
          'one',
          'two',
          'three',
          'four',
          'five',
          'six',
          'seven',
          'eight',
          'nine']

def breakdown(x):
    for c in x:
        yield digits[int(c)]


class UnsortableColumn(scrolltable.AttributeColumn):
    def sortAttribute(self):
        return None


class DeprecatedNamesTest(unittest.TestCase):
    """
    Verify that deprecated names in the 'tdb' module warn appropriately.
    """

    def test_attributeColumn(self):
        """
        Verify that using the AttributeColumn name imported from 'tdb' will warn
        the user when it is instantiated.
        """
        def function():
            attrcol = tdb.AttributeColumn(X.number)
        self.assertWarns(
            DeprecationWarning,
            "tdb.AttributeColumn is deprecated.  "
            "Use scrolltable.AttributeColumn instead.",
            __file__, function)



class ModelTest(unittest.TestCase):

    def setUp(self):
        self.store = Store()
        def _():
            for x in range(107):
                X(store=self.store,
                number=x,
                textNumber=unicode(x),
                phoneticDigits=u' '.join(breakdown(str(x))))
        self.store.transact(_)

    def assertNumbersAre(self, tdm, seq):
        self.assertEquals(list(x.get('number') for x in tdm.currentPage()), seq)

    def testUniformValues(self):
        for x in self.store.query(X):
            x.number = 1

        tdm = tdb.TabularDataModel(self.store,
                X, [X.number],
                itemsPerPage=15)

        self.failUnless(tdm.hasNextPage(), 'expected there to be a next page')


    def testDeleteEverything(self):
        tdm = tdb.TabularDataModel(self.store,
                X, [X.number,
                    X.textNumber,
                    X.phoneticDigits],
                itemsPerPage=15)

        self.assertNumbersAre(tdm, range(15))
        for item in self.store.query(X):
            item.deleteFromStore()
        self.assertNumbersAre(tdm, [])

    def testOnePage(self):
        tdm = tdb.TabularDataModel(self.store,
                X, [X.number,
                    X.textNumber,
                    X.phoneticDigits],
                AND(X.number >= 17,
                    X.number < 94),
                itemsPerPage=15)

        _assertNumbersAre = lambda seq: self.assertNumbersAre(tdm, seq)

        _assertNumbersAre(range(17, 17+15))
        tdm.nextPage()
        _assertNumbersAre(range(17+15, 17+30))
        tdm.firstPage()
        _assertNumbersAre(range(17, 17+15))

    def testLeafing(self):
        tdm = tdb.TabularDataModel(self.store,
                X, [X.number,
                    X.textNumber,
                    X.phoneticDigits],
                itemsPerPage=15)

        _assertNumbersAre = lambda seq: self.assertNumbersAre(tdm, seq)

        _assertNumbersAre(range(15))
        tdm.nextPage()
        _assertNumbersAre(range(15, 30))
        tdm.prevPage()
        _assertNumbersAre(range(15))
        tdm.lastPage()
        # This next assert is kind of weak, because it is valid to have only a
        # few results on the last page, but right now the strategy is to
        # always keep the page full of results.  No matter what though, the
        # last page should contain the last value.
        self.assertEquals(list(tdm.currentPage())[-1]['number'],
                          106)
        tdm.firstPage()
        _assertNumbersAre(range(15))

    def testLeafingAndSorting(self):
        tdm = tdb.TabularDataModel(self.store,
                X, [X.number,
                    X.textNumber,
                    X.phoneticDigits],
                itemsPerPage=15)

        _assertNumbersAre = lambda seq: self.assertNumbersAre(tdm, seq)

        _assertNumbersAre(range(15))
        tdm.lastPage()
        _assertNumbersAre(range(107-15, 107))
        tdm.prevPage()
        _assertNumbersAre(range(107-30, 107-15))
        tdm.firstPage()
        _assertNumbersAre(range(15))
        tdm.resort('number', False)
        tdm.firstPage()
        _assertNumbersAre(list(reversed(range(107-15, 107))))
        tdm.lastPage()
        _assertNumbersAre(list(reversed(range(15))))

    def testPageUnderrun(self):
        tdm = tdb.TabularDataModel(self.store,
                X, [X.number,
                    X.textNumber,
                    X.phoneticDigits],
                itemsPerPage=15)
        _assertNumbersAre = lambda seq: self.assertNumbersAre(tdm, seq)

        _assertNumbersAre(range(15))
        # go to the pre-penultimate page
        for i in xrange(5):
            tdm.nextPage()
        _assertNumbersAre(range(15*5, (15*5)+15))
        tdm.nextPage()
        lastFullSet = range(15*6, (15*6)+15)
        _assertNumbersAre(lastFullSet)
        tdm.nextPage()
        lastSet = [105, 106]
        _assertNumbersAre(lastSet)

    def testItemUnderrun(self):
        tdm = tdb.TabularDataModel(self.store,
                X, [X.number,
                    X.textNumber,
                    X.phoneticDigits],
                itemsPerPage=110)

        assertFirstPage = lambda: self.assertNumbersAre(tdm, range(107))

        assertFirstPage()
        tdm.nextPage()
        assertFirstPage()
        tdm.prevPage()
        assertFirstPage()
        tdm.lastPage()
        assertFirstPage()
        tdm.firstPage()
        assertFirstPage()

    def testTwoPageNextLastEquality(self):
        tdm = tdb.TabularDataModel(self.store,
                                   X, [X.number],
                                   itemsPerPage=100)

        assertFirstPage = lambda: self.assertNumbersAre(tdm, range(100))
        assertSecondPage = lambda: self.assertNumbersAre(tdm, range(100, 107))

        assertFirstPage()
        tdm.nextPage()
        assertSecondPage()
        tdm.firstPage()
        assertFirstPage()
        tdm.lastPage()
        assertSecondPage()
    testTwoPageNextLastEquality.todo = 'is this a bug?  it seems like one to me'

    def testPagination(self):
        tdm = tdb.TabularDataModel(self.store,
                                   X, [X.number,
                                       X.textNumber,
                                       X.phoneticDigits],
                                   itemsPerPage=15)
        self.assertEquals(tdm.pageNumber, 1)
        self.assertEquals(tdm.totalItems, 107)
        self.assertEquals(tdm.totalPages, 8)

        tdm.nextPage()
        self.assertEquals(tdm.pageNumber, 2)
        self.assertEquals(tdm.totalItems, 107)
        self.assertEquals(tdm.totalPages, 8)
        tdm.nextPage()
        self.assertEquals(tdm.pageNumber, 3)
        self.assertEquals(tdm.totalItems, 107)
        self.assertEquals(tdm.totalPages, 8)
        tdm.nextPage()
        self.assertEquals(tdm.pageNumber, 4)
        self.assertEquals(tdm.totalItems, 107)
        self.assertEquals(tdm.totalPages, 8)
        tdm.nextPage()
        self.assertEquals(tdm.pageNumber, 5)
        self.assertEquals(tdm.totalItems, 107)
        self.assertEquals(tdm.totalPages, 8)
        tdm.nextPage()
        self.assertEquals(tdm.pageNumber, 6)
        self.assertEquals(tdm.totalItems, 107)
        self.assertEquals(tdm.totalPages, 8)
        tdm.nextPage()
        self.assertEquals(tdm.pageNumber, 7)
        self.assertEquals(tdm.totalItems, 107)
        self.assertEquals(tdm.totalPages, 8)
        tdm.nextPage()
        self.assertEquals(tdm.pageNumber, 8)
        self.assertEquals(tdm.totalItems, 107)
        self.assertEquals(tdm.totalPages, 8)

        tdm.lastPage()
        self.assertEquals(tdm.pageNumber, 8)
        self.assertEquals(tdm.totalPages, 8)
        self.assertEquals(tdm.totalItems, 107)
        tdm.firstPage()
        self.assertEquals(tdm.pageNumber, 1)
        self.assertEquals(tdm.totalPages, 8)
        self.assertEquals(tdm.totalItems, 107)




    def testSortItemUnderrun(self):
        tdm = tdb.TabularDataModel(self.store,
                X, [X.number,
                    X.textNumber,
                    X.phoneticDigits],
                itemsPerPage=110)

        assertFirstPage = lambda: self.assertNumbersAre(tdm, range(107))

        assertFirstPage()
        tdm.resort(tdm.currentSortColumn.attributeID)
        assertFirstPage()
        tdm.resort(tdm.currentSortColumn.attributeID, False)
        self.assertNumbersAre(tdm, list(reversed(range(107))))
        tdm.resort(tdm.currentSortColumn.attributeID)
        assertFirstPage()
        tdm.resort(tdm.currentSortColumn.attributeID, True)
        assertFirstPage()

    def testChangeSortColumnItemUnderrun(self):
        tdm = tdb.TabularDataModel(self.store,
                X, [X.number,
                    X.textNumber,
                    X.phoneticDigits],
                itemsPerPage=110)

        assertFirstPage = lambda: self.assertNumbersAre(tdm, range(107))

        assertFirstPage()
        tdm.resort(tdm.currentSortColumn.attributeID, True)
        assertFirstPage()
        # change sort direction, keep column
        tdm.resort(tdm.currentSortColumn.attributeID, False)
        self.assertNumbersAre(tdm, list(reversed(range(107))))
        # change sort column and direction
        tdm.resort('phoneticDigits', True)
        # switch back to previous sort column & direction
        tdm.resort('number', False)
        self.assertNumbersAre(tdm, list(reversed(range(107))))
        msg = 'itemsPerPage > totalItems, should only have one page'
        self.failIf(tdm.hasPrevPage(), msg)
        self.failIf(tdm.hasNextPage(), msg)

    def testOnePageHasNextPrev(self):
        bigtdm = tdb.TabularDataModel(self.store,
                X, [X.number,
                    X.textNumber,
                    X.phoneticDigits],
                    itemsPerPage=200)
        bigtdm.nextPage()
        bigtdm.nextPage()
        self.failIf(bigtdm.hasNextPage())
        self.failIf(bigtdm.hasPrevPage())

    def testMultiPageHasNextPrev(self):
        tdm = tdb.TabularDataModel(self.store,
                X, [X.number,
                    X.textNumber,
                    X.phoneticDigits],
                itemsPerPage=15)
        self.failIf(tdm.hasPrevPage())
        self.failUnless(tdm.hasNextPage())
        tdm.nextPage()
        self.failUnless(tdm.hasNextPage())
        self.failUnless(tdm.hasPrevPage())
        tdm.prevPage()
        self.failIf(tdm.hasPrevPage())
        self.failUnless(tdm.hasNextPage())
        tdm.lastPage()
        self.failIf(tdm.hasNextPage())
        self.failUnless(tdm.hasPrevPage())
        tdm.prevPage()
        self.failUnless(tdm.hasNextPage())
        self.failUnless(tdm.hasPrevPage())
        tdm.firstPage()
        for x in range(6):
            tdm.nextPage()
        self.failUnless(tdm.hasPrevPage())
        self.failUnless(tdm.hasNextPage())
        tdm.nextPage()
        self.failUnless(tdm.hasPrevPage())
        self.failIf(tdm.hasNextPage())

    def testCurrentPageDoesntChange(self):
        tdm = tdb.TabularDataModel(self.store,
                                   X, [X.number,
                                       X.textNumber,
                                       X.phoneticDigits],
                                   itemsPerPage=15)
        for y in range(3):
            tdm.nextPage()
            example = tdm.currentPage()
            for x in range(3):
                self.assertEquals(example, tdm.currentPage())


    def testDeleteItems(self):
        tdm = tdb.TabularDataModel(self.store,
                                   X, [X.number,
                                       X.textNumber,
                                       X.phoneticDigits],
                                   itemsPerPage=15)
        r = tdm.currentPage()
        r0 = r[0]['__item__']
        r0.deleteFromStore()
        rx = tdm.currentPage()
        r1 = rx[0]['__item__']
        self.failIf(r1._Item__deleting,
                    "First item in current page was deleted!")
        r1.deleteFromStore()
        tdm.nextPage()
        self.assertNumbersAre(tdm, range(16, 16+15))
        tdm.prevPage()
        self.assertNumbersAre(tdm, range(2, 2+15))

        # The distinction between this test and the nextPage test above is
        # important: we never "skip" items when paging.  The current results of
        # the TDM represent *what the user has seen*.  In the previous case, we
        # have never called currentPage and received a result with #16 in it
        # before calling nextPage.  In this case, assertNumbersAre(2,...) has
        # "seen" the page with #16 on it, so we are (correctly) taken to the
        # next item after that to begin the next page.
        tdm.nextPage()
        self.assertNumbersAre(tdm, range(17, 17+15))

    def testSorting(self):
        tdm = tdb.TabularDataModel(self.store,
                X, [X.number,
                    X.textNumber,
                    X.phoneticDigits],
                itemsPerPage=15)

        _assertNumbersAre = lambda seq: self.assertNumbersAre(tdm, seq)
        tdm.resort('number', True)
        _assertNumbersAre(range(15))
        tdm.resort('number', False)
        _assertNumbersAre(list(reversed(range(15))))
        _assertNumbersAre(list(reversed(range(15))))
        tdm.nextPage()
        _assertNumbersAre(list(reversed(range(15))))

    def testUnsortableColumns(self):
        tdm = tdb.TabularDataModel(self.store,
                X, [X.number,
                    UnsortableColumn(X.textNumber),
                    UnsortableColumn(X.phoneticDigits)],
                itemsPerPage=15)

        self.assertNumbersAre(tdm, range(15))
        self.assertRaises(scrolltable.Unsortable,
                          lambda: tdm.resort('textNumber'))
        self.assertRaises(scrolltable.Unsortable,
                          lambda: tdm.resort('phoneticDigits'))
        # check to see if the last valid state remains
        self.assertNumbersAre(tdm, range(15))

