from epsilon.extime import Time

from nevow.livetrial import testcase
from nevow import tags, loaders
from nevow.athena import expose

from axiom.store import Store
from axiom.userbase import LoginMethod
from axiom.dependency import installOn

from xmantissa.webtheme import getLoader
from xmantissa.people import Person, EmailAddress

from xquotient import compose, mimeutil, smtpout
from xquotient.inbox import Inbox
from xquotient.test.test_inbox import testMessageFactory



class _ComposeTestMixin:
    def _getComposeFragment(
            self, composeFragFactory=compose.ComposeFragment):

        s = Store()

        LoginMethod(store=s,
                    internal=False,
                    protocol=u'email',
                    localpart=u'default',
                    domain=u'host',
                    verified=True,
                    account=s)

        installOn(Inbox(store=s), s)

        smtpout.FromAddress(
            store=s,
            address=u'moe@divmod.com').setAsDefault()

        composer = compose.Composer(store=s)
        installOn(composer, s)

        composeFrag = composeFragFactory(composer)
        composeFrag.jsClass = u'Quotient.Test.ComposeController'
        composeFrag.setFragmentParent(self)
        composeFrag.docFactory = getLoader(composeFrag.fragmentName)
        return (s, composeFrag)

class ComposeTestCase(testcase.TestCase, _ComposeTestMixin):
    """
    Tests for Quotient.Compose.Controller
    """

    jsClass = u'Quotient.Test.ComposeTestCase'

    docFactory = loaders.stan(tags.div[
            tags.div(render=tags.directive('liveTest'))[
                tags.div(render=tags.directive('composer'),
                         style='visibility: hidden'),
                tags.div(id='mantissa-footer')]])

    def render_composer(self, ctx, data):
        """
        Make a bunch of people and give them email addresses
        """

        (s, composeFrag) = self._getComposeFragment()


        def makePerson(email, name):
            EmailAddress(store=s,
                         address=email,
                         person=Person(store=s,
                                       name=name))

        makePerson(u'maboulkheir@divmod.com', u'Moe Aboulkheir')
        makePerson(u'localpart@domain', u'Tobias Knight')
        makePerson(u'madonna@divmod.com', u'Madonna')
        makePerson(u'kilroy@foo', u'')
        return ctx.tag[composeFrag]


class AddrPassthroughComposeFragment(compose.ComposeFragment):
    """
    L{xquotient.compose.ComposeFragment} subclass which overrides
    L{_sendOrSave} to return a list of the flattened recipient addresses that
    were submitted via the compose form
    """

    def _sendOrSave(self, **k):
        """
        @return: sequence of C{unicode} email addresses
        """
        return [addr.pseudoFormat() for addr in k['toAddresses']]

class ComposeToAddressTestCase(testcase.TestCase, _ComposeTestMixin):
    """
    Tests for the behaviour of recipient addresses in
    L{xquotient.compose.ComposeFragment}
    """

    jsClass = u'Quotient.Test.ComposeToAddressTestCase'

    def __init__(self):
        testcase.TestCase.__init__(self)
        self.perTestData = {}

    def getComposeWidget(self, key, toAddresses):
        """
        @param key: unique identifier for the test method
        @param toAddresses: sequence of C{unicode} email addresses which
        should be wrapped in L{xquotient.mimeutil.EmailAddress} instances and
        passed to the L{ComposeFragment} constructor.  These will be used as
        the initial content of the client-side toAddresses form input when the
        fragment is rendered
        @rtype: L{AddrPassthroughComposeFragment}
        """
        def composeFragFactory(composer):
            return AddrPassthroughComposeFragment(
                        composer,
                        recipients={'to': [mimeutil.EmailAddress(e, False)
                                            for e in toAddresses]})

        (s, frag) = self._getComposeFragment(
                        composeFragFactory=composeFragFactory)
        self.perTestData[key] = (s, frag)
        return frag
    expose(getComposeWidget)



class ComposeAutoCompleteTestCase(testcase.TestCase):
    """
    Tests for compose autocomplete
    """

    jsClass = u'Quotient.Test.ComposeAutoCompleteTestCase'
