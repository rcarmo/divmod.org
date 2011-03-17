from nevow.livetrial import testcase
from nevow.athena import expose

from axiom.store import Store
from axiom.userbase import LoginMethod
from axiom.dependency import installOn

from xmantissa.webtheme import getLoader

from xquotient import compose, smtpout


class FromAddressScrollTableTestCase(testcase.TestCase):
    """
    Tests for L{xquotient.smtpout.FromAddressScrollTable}
    """

    jsClass = u'Quotient.Test.FromAddressScrollTableTestCase'

    def getFromAddressScrollTable(self):
        s = Store()

        LoginMethod(store=s,
                    internal=False,
                    protocol=u'email',
                    localpart=u'default',
                    domain=u'host',
                    verified=True,
                    account=s)

        installOn(compose.Composer(store=s), s)

        smtpout.FromAddress(
            store=s,
            address=u'notdefault@host',
            smtpHost=u'host',
            smtpUsername=u'notdefault')

        f = smtpout.FromAddressScrollTable(s)
        f.setFragmentParent(self)
        f.docFactory = getLoader(f.fragmentName)
        return f
    expose(getFromAddressScrollTable)
