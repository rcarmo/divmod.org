from nevow.livetrial.testcase import TestCase
from nevow import tags

from xquotient.renderers import ButtonRenderingMixin

class ShowNodeAsDialogTestCase(TestCase):
    """
    Tests for Quotient.Common.Util.showNodeAsDialog
    """

    jsClass = u'Quotient.Test.ShowNodeAsDialogTestCase'



class ButtonTogglerTestCase(TestCase, ButtonRenderingMixin):
    """
    Tests for Quotient.Common.ButtonToggler
    """

    jsClass = u'Quotient.Test.ButtonTogglerTestCase'

    def getWidgetDocument(self):
        return tags.div(render=tags.directive('button'))[
                    tags.a(href='#')['A link']]



class ShowSimpleWarningDialogTestCase(TestCase):
    """
    Tests for Quotient.Common.Util.showSimpleWarningDialog
    """

    jsClass = u'Quotient.Test.ShowSimpleWarningDialogTestCase'
