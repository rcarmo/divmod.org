from nevow.livetrial.testcase import TestCase
from nevow.athena import expose

from axiom.store import Store
from axiom.dependency import installOn

from xmantissa.webtheme import getLoader

from xquotient import grabber

class AddGrabberTestCase(TestCase):
    """
    Tests for the add grabber liveform
    """

    jsClass = u'Quotient.Test.AddGrabberTestCase'

    def getWidgetDocument(self):
        s = Store()

        grabberConfig = grabber.GrabberConfiguration(store=s)
        installOn(grabberConfig, s)

        f = grabber.GrabberConfigFragment(grabberConfig)
        f.setFragmentParent(self)
        f.docFactory = getLoader(f.fragmentName)
        return f

class GrabberListTestCase(TestCase):
    """
    Tests for the grabber list/scrolltable
    """

    jsClass = u'Quotient.Test.GrabberListTestCase'

    def getWidgetDocument(self):
        s = Store()

        grabberConfig = grabber.GrabberConfiguration(store=s)
        installOn(grabberConfig, s)

        self.grabber = grabber.POP3Grabber(
                            store=s,
                            config=grabberConfig,
                            username=u'foo',
                            domain=u'bar',
                            password=u'baz')

        f = grabber.GrabberConfigFragment(grabberConfig)
        f.setFragmentParent(self)
        f.docFactory = getLoader(f.fragmentName)
        return f

    def deleteGrabber(self):
        self.grabber.deleteFromStore()
    expose(deleteGrabber)
