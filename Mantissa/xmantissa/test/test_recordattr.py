
"""
Tests for xmantissa._recordattr module.
"""

from twisted.trial.unittest import TestCase

from epsilon.structlike import record

from axiom.item import Item

from axiom.attributes import text, integer

from axiom.store import Store

from xmantissa._recordattr import RecordAttribute, WithRecordAttributes

class Sigma(record('left right')):
    """
    A simple record type which composes two attributes.
    """
    def getLeft(self):
        """
        Return the left attribute.
        """
        return self.left

    def getRight(self):
        """
        Return the right attribute.
        """
        return self.right


class RecordAttributeTestItem(Item):
    """
    An item for testing record attributes.
    """

    alpha = text()
    beta = integer()
    sigma = RecordAttribute(Sigma, [alpha, beta])


class RecordAttributeRequired(Item, WithRecordAttributes):
    """
    An item for testing record attributes with mandatory attributes.
    """
    alpha = text(allowNone=False)
    beta = integer(allowNone=False)
    sigma = RecordAttribute(Sigma, [alpha, beta])



class ItemWithRecordAttributeTest(TestCase):
    """
    An item with a RecordAttribute attribute ought to return and store its
    attributes.
    """

    def eitherWay(self, thunk, T, **kw):
        """
        Run the given 'thunk' with an item not inserted into a store, then one
        inserted into a store after the fact, then one inserted into a store in
        its constructor.
        """
        ra1 = T(**kw)
        thunk(ra1)
        s = Store()
        ra2 = T(**kw)
        ra2.store = s
        thunk(ra2)
        ra3 = T(store=s, **kw)
        thunk(ra3)


    def test_getAttribute(self):
        """
        Retrieving a L{RecordAttribute} whose component attributes are set
        normally should yield a record instance of the appropriate type with
        the values set.
        """
        def check(rati):
            self.assertEqual(rati.sigma.getLeft(), u'one')
            self.assertEqual(rati.sigma.getRight(), 2)
        self.eitherWay(check, RecordAttributeTestItem, alpha=u'one', beta=2)


    def test_initialize(self):
        """
        Initializing an item with a record attribute set to something should
        set its underlying attributes.
        """
        def check(rati):
            self.assertEqual(rati.alpha, u'five')
            self.assertEqual(rati.beta, 6)
        self.eitherWay(check, RecordAttributeTestItem,
                       sigma=Sigma(left=u'five', right=6))


    def test_initializeNoNones(self):
        """
        Initializing an item with a record attribute set to something should
        set its underlying attributes in the case where the underlying item
        does not work.
        """
        def check(rati):
            self.assertEqual(rati.alpha, u'seven')
            self.assertEqual(rati.beta, 8)
        self.eitherWay(check, RecordAttributeRequired.create,
                       sigma=Sigma(left=u'seven', right=8))


    def test_setAttribute(self):
        """
        Setting a L{RecordAttribute} should set all of its component
        attributes.
        """
        def check(rati):
            rati.sigma = Sigma(left=u'three', right=4)
            self.assertEqual(rati.alpha, u'three')
            self.assertEqual(rati.beta, 4)
        self.eitherWay(check, RecordAttributeTestItem)


    def test_queryComparisons(self):
        """
        Querying with an inequality on a L{RecordAttribute} should yield the
        same results as querying on its AND'ed component attributes.
        """
        s = Store()

        RARc = RecordAttributeRequired.create
        x = RARc(store=s, sigma=Sigma(left=u'x', right=1))
        y = RARc(store=s, sigma=Sigma(left=u'y', right=2))
        z = RARc(store=s, sigma=Sigma(left=u'z', right=3))
        a = RARc(store=s, sigma=Sigma(left=u'a', right=4))

        self.assertEqual(list(s.query(
                    RecordAttributeRequired,
                    RecordAttributeRequired.sigma == Sigma(u'z', 3))),
                         [z])
        self.assertEqual(list(s.query(
                    RecordAttributeRequired,
                    RecordAttributeRequired.sigma == Sigma(u'z', 9))),
                         [])
        self.assertEqual(list(s.query(
                    RecordAttributeRequired,
                    RecordAttributeRequired.sigma != Sigma(u'y', 2),
                    sort=RecordAttributeRequired.storeID.ascending)),
                         [x, z, a])



