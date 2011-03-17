from axiom.test.historic import stubloader
from xmantissa.publicweb import FrontPage

class FrontPageTest(stubloader.StubbedTest):
    """
    Upgrader test for L{xmantissa.publicweb.FrontPage}.
    """
    def testUpgrade(self):
        """
        All the attributes of L{xmantissa.publicweb.FrontPage} are
        present after upgrading.
        """
        fp = self.store.findUnique(FrontPage)
        self.assertEqual(fp.publicViews, 17)
        self.assertEqual(fp.privateViews, 42)
        self.assertEqual(fp.prefixURL, u'')
        self.assertEqual(fp.defaultApplication, None)

