from axiom.test.historic import stubloader
from xmantissa.signup import Ticket
from xmantissa.product import Product
from xmantissa.webadmin import AdministrativeBenefactor
class TicketTestCase(stubloader.StubbedTest):
    def testTicket1to2(self):
        """
        Make sure Ticket upgrades OK and has a Product corresponding
        to the old AdministrativeBenefactor.
        """
        t = self.store.findUnique(Ticket)
        self.failUnless(isinstance(t.product, Product))
        self.assertEqual(t.product.types,
                         AdministrativeBenefactor.powerupNames)
