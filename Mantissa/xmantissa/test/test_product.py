from zope.interface import implements, Interface

from twisted.trial.unittest import TestCase
from twisted.python.reflect import qual

from axiom.store import Store
from axiom.item import Item
from axiom.attributes import integer

from xmantissa.product import Installation, ProductConfiguration, Product, ProductFragment

class IFoo(Interface):
    pass

class Foo(Item):
    implements(IFoo)
    powerupInterfaces = (IFoo,)
    attr = integer()

class IBaz(Interface):
    pass

class Baz(Item):
    implements(IBaz)
    powerupInterfaces = (IBaz,)
    attr = integer()

class ProductTest(TestCase):
    def setUp(self):
        """
        Create a pseudo site store and a pseudo user store in it.
        """
        self.siteStore = Store()
        self.userStore = Store()
        self.userStore.parent = self.siteStore


    def test_product(self):
        self.product = Product(store=self.siteStore)
        self.product.types = [
            n.decode('ascii') for n in [qual(Foo), qual(Baz)]]
        self.product.installProductOn(self.userStore)
        i = self.userStore.findUnique(Installation)
        self.assertEqual(i.types, self.product.types)


    def test_createProduct(self):
        """
        Verify that L{ProductConfiguration.createProduct} creates a
        correctly configured L{Product} and returns it.
        """
        conf = ProductConfiguration(store=self.userStore)
        product = conf.createProduct([Foo, Baz])
        self.assertEqual(product.types, [qual(Foo), qual(Baz)])



class InstallationTest(TestCase):

    def setUp(self):
        self.s = Store()
        self.product = Product()
        self.product.types = [n.decode('ascii') for n in [qual(Foo), qual(Baz)]]
        self.product.installProductOn(self.s)
        self.i = self.s.findUnique(Installation)


    def test_install(self):
        """
        Ensure that Installation installs instances of the types it is created with.
        """
        self.assertNotEqual(IFoo(self.s, None), None)
        self.assertNotEqual(IBaz(self.s, None), None)
        self.assertEqual(list(self.i.items), [self.s.findUnique(t) for t in [Foo, Baz]])


    def test_uninstall(self):
        """
        Ensure that Installation properly uninstalls all of the items it controls.
        """
        self.product.removeProductFrom(self.s)
        self.assertEqual(IFoo(self.s, None), None)
        self.assertEqual(IBaz(self.s, None), None)
        self.assertEqual(list(self.s.query(Installation)), [])



class StubProductConfiguration(object):
    """
    Stub implementation of L{ProductConfiguration} for testing purposes.

    @ivar createdProducts: A list containing all powerups lists passed to
    C{createProduct}.
    """
    def __init__(self, createdProducts):
        self.createdProducts = createdProducts


    def createProduct(self, powerups):
        self.createdProducts.append(powerups)



class ViewTests(TestCase):
    """
    Tests for L{ProductFragment}.
    """
    def test_coerceProduct(self):
        """
        Verify that L{ProductFragment.coerceProduct} calls C{createProduct} on
        the object it wraps and passes its arguments through.
        """
        createdProducts = []
        fragment = ProductFragment(StubProductConfiguration(createdProducts))
        fragment.coerceProduct(foo=u'bar', baz=u'quux')
        self.assertEqual(createdProducts, [[u'bar', u'quux']])


    def test_coerceProductReturn(self):
        """
        Verify that L{ProductFragment.coerceProduct} returns a string
        indicating success.
        """
        createdProducts = []
        fragment = ProductFragment(StubProductConfiguration(createdProducts))
        result = fragment.coerceProduct()
        self.assertEqual(result, u'Created.')

