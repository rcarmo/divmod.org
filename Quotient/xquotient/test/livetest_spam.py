
from nevow.livetrial.testcase import TestCase
from nevow.athena import expose
from nevow.tags import div, directive
from nevow.loaders import stan

from axiom.store import Store

from xquotient.spam import Filter, HamFilterFragment

class PostiniConfigurationTestCase(TestCase):
    """
    Tests for configuring Postini-related behavior.
    """
    jsClass = u'Quotient.Test.PostiniConfigurationTestCase'

    def setUp(self):
        self.store = Store()
        self.filter = Filter(store=self.store)
        self.widget = HamFilterFragment(self.filter)
        self.widget.setFragmentParent(self)
        return self.widget;
    expose(setUp)
        

    def checkConfiguration(self):
        """
        Test that postini filtering has been turned on and that the threshhold
        has been set to 5.0.
        """
        self.failUnless(self.filter.usePostiniScore)
        self.assertEquals(self.filter.postiniThreshhold, 5.0)
    expose(checkConfiguration)
