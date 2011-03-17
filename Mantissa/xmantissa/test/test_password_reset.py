import email

from twisted.trial.unittest import TestCase

from nevow.url import URL
from nevow.flat import flatten
from nevow.inevow import IResource
from nevow.testutil import FakeRequest, renderPage

from axiom.store import Store
from axiom import userbase
from axiom.dependency import installOn
from axiom.plugins.mantissacmd import Mantissa

from xmantissa import ixmantissa
from xmantissa.web import SiteConfiguration
from xmantissa.webapp import PrivateApplication
from xmantissa.signup import PasswordResetResource, _PasswordResetAttempt


class PasswordResetTestCase(TestCase):
    def setUp(self):
        """
        Set up a fake objects and methods for the password reset tests.
        """
        siteStore = Store(filesdir=self.mktemp())
        Mantissa().installSite(siteStore, u"divmod.com", u"", False)
        self.loginSystem = siteStore.findUnique(userbase.LoginSystem)
        self.site = siteStore.findUnique(SiteConfiguration)

        la = self.loginSystem.addAccount(
            u'joe', u'divmod.com', u'secret', internal=True)

        la.addLoginMethod(
            u'joe', u'external.com',
            protocol=u'zombie dance',
            verified=False,
            internal=False)

        # create an account with no external mail address
        account = self.loginSystem.addAccount(
            u'jill', u'divmod.com', u'secret', internal=True)

        account.addLoginMethod(
            u'jill', u'divmod.com',
            protocol=u'zombie dance',
            verified=True,
            internal=True)

        self.siteStore = siteStore

        # Set up the user store to have all the elements necessary to redirect
        # in the case where the user is already logged in.
        substore = la.avatars.open()
        installOn(PrivateApplication(store=substore), substore)

        self.userStore = substore
        self.loginAccount = la
        self.nonExternalAccount = account
        self.reset = PasswordResetResource(self.siteStore)


    def test_reset(self):
        """
        Test a password reset, as it might happen for a user
        """
        self.reset.resetPassword(
            self.reset.newAttemptForUser(u'joe@divmod.com'),
            u'more secret')

        self.assertEqual(self.loginAccount.password, u'more secret')
        self.assertEqual(
            self.siteStore.query(_PasswordResetAttempt).count(), 0)


    def test_attemptByKey(self):
        """
        Test that L{xmantissa.signup.PasswordResetResource.attemptByKey}
        knows the difference between valid and invalid keys
        """
        self.failUnless(self.reset.attemptByKey(
                self.reset.newAttemptForUser(u'joe@divmod.com').key))
        self.failIf(self.reset.attemptByKey(u'not really a key'))


    def test_accountByAddress(self):
        """
        Test that L{xmantissa.signup.PasswordResetResource.accountByAddress}
        behaves similarly to L{axiom.userbase.LoginSystem.accountByAddress}
        """
        self.assertEqual(
            self.reset.accountByAddress(u'joe@divmod.com'),
            self.loginSystem.accountByAddress(u'joe', u'divmod.com'))


    def test_handleRequest(self):
        """
        Check that handling a password reset request for a user sends email
        appropriately.
        """
        def myFunc(url, attempt, email):
            myFunc.emailsSent += 1
            myFunc.url = url
            myFunc.attempt = attempt
            myFunc.email = email
        url = 'http://oh.no/reset.html'
        myFunc.emailsSent = 0
        self.reset.sendEmail=myFunc

        # positive case. User exists. Email should be sent
        self.reset.handleRequestForUser(u'joe@divmod.com', url)
        self.assertEquals(myFunc.emailsSent, 1)
        self.assertEquals(myFunc.url, 'http://oh.no/reset.html')
        self.assertEquals(myFunc.attempt.username, u'joe@divmod.com')
        self.assertEquals(myFunc.email, 'joe@external.com')

        # Negative case. User does not exist. Email should not be sent
        self.reset.handleRequestForUser(u'no_joe@divmod.com', url)
        self.assertEquals(myFunc.emailsSent, 1)

        # Negative case. User exists, but has no external mail. Email should not
        # be sent.
        self.reset.handleRequestForUser(u'jill@divmod.com', url)
        self.assertEquals(myFunc.emailsSent, 1)


    def test_sendEmail(self):
        """
        L{PasswordResetResource.sendEmail} should format a meaningful password
        reset email.
        """
        resetAddress = 'reset@example.org'
        resetURI = URL.fromString('http://example.org/resetPassword')
        userAddress = 'joe@divmod.com'

        resetAttempt = self.reset.newAttemptForUser(userAddress.decode('ascii'))
        _sentEmail = []
        self.reset.sendEmail(resetURI, resetAttempt, userAddress,
                             _sendEmail=lambda *args: _sentEmail.append(args))

        self.assertEquals(len(_sentEmail), 1)
        [(sentFrom, sentTo, sentText)] = _sentEmail
        self.assertEquals(sentFrom, resetAddress)
        self.assertEquals(sentTo, userAddress)

        msg = email.message_from_string(sentText)
        [headerFrom] = msg.get_all('from')
        [headerTo] = msg.get_all('to')
        [headerDate] = msg.get_all('date')
        # Python < 2.5 compatibility
        try:
            from email import utils
        except ImportError:
            from email import Utils as utils
        self.assertEquals(utils.parseaddr(headerFrom)[1], resetAddress)
        self.assertEquals(utils.parseaddr(headerTo)[1], userAddress)
        self.assertTrue(utils.parsedate_tz(headerDate) is not None,
                        '%r is not a RFC 2822 date' % headerDate)

        self.assertTrue(not msg.is_multipart())
        self.assertIn(flatten(resetURI.child(resetAttempt.key)),
                      msg.get_payload())


    def test_redirectToSettingsWhenLoggedIn(self):
        """
        When a user is already logged in, navigating to /resetPassword should
        redirect to the settings page, since the user can change their password
        from there.
        """
        self.assertNotIdentical(self.userStore.parent, None) # sanity check
        prefPage = ixmantissa.IPreferenceAggregator(self.userStore)
        urlPath = ixmantissa.IWebTranslator(self.userStore).linkTo(prefPage.storeID)
        request = FakeRequest(headers={"host": "example.com"})
        app = IResource(self.userStore)
        rsc = IResource(app.locateChild(request, ("resetPassword",))[0])
        d = renderPage(rsc, reqFactory=lambda : request)
        def rendered(result):
            self.assertEquals(
                'http://example.com' + urlPath,
                request.redirected_to)
        d.addCallback(rendered)
        return d


    def test_getExternalEmail(self):
        """
        Test that we can accurately retrieve an external email address from an
        attempt.
        """
        email = self.reset.getExternalEmail(self.loginAccount)
        self.assertEquals(email, 'joe@external.com')


    def test_noExternalEmail(self):
        """
        Test that C{getExternalEmail} returns C{None} if there is no external
        email address for that account.
        """
        email = self.reset.getExternalEmail(self.nonExternalAccount)
        self.assertEquals(email, None)


    def test_nothingSpecified(self):
        """
        Submitting an empty form should redirect the user back to the form.
        """
        self.reset.handleRequestForUser = lambda *args: self.fail(args)

        _request = FakeRequest(
            headers={'host': 'example.org'},
            uri='/resetPassword',
            currentSegments=['resetPassword'],
            args={'username': [''], 'email': ['']})
        _request.method = 'POST'

        d = renderPage(self.reset, reqFactory=lambda: _request)
        def rendered(_):
            self.assertEquals(_request.redirected_to,
                              'http://example.org/resetPassword')
        d.addCallback(rendered)
        return d


    def test_onlyUsernameSpecified(self):
        """
        Test that if the user only supplies the local part of their username
        then the password resetter will still find the correct user.
        """
        hostname = self.site.hostname.encode('ascii')

        def handleRequest(username, url):
            handleRequest.attempt = self.reset.newAttemptForUser(username)
            handleRequest.username = username

        class Request(FakeRequest):
            method = 'POST'

            def __init__(self, *a, **kw):
                FakeRequest.__init__(self, *a, **kw)
                self.args = {'username': ['joe'],
                             'email': ['']}
                self.received_headers['host'] = hostname

        self.reset.handleRequestForUser = handleRequest
        d = renderPage(self.reset, reqFactory=Request)
        d.addCallback(lambda _: self.assertEquals(handleRequest.username,
                                                  'joe@' + hostname))
        return d


    def test_emailAddressSpecified(self):
        """
        If an email address and no username is specified, then the password
        resetter should still find the correct user.
        """
        requests = []
        def handleRequest(username, url):
            requests.append((username, url))

        class Request(FakeRequest):
            method = 'POST'
            def __init__(self, *a, **k):
                FakeRequest.__init__(self, *a, **k)
                self.args = {'username': [''],
                             'email': ['joe@external.com']}

        self.reset.handleRequestForUser = handleRequest
        d = renderPage(self.reset, reqFactory=Request)
        def completedRequest():
            self.assertEqual(len(requests), 1)
            self.assertEqual(requests[0][0], 'joe@divmod.com')
        d.addCallback(lambda ign: completedRequest())
        return d


    def specifyBogusEmail(self, bogusEmail):
        """
        If an email address (which is not present in the system) and no
        username is specified, then the password reset should still ask the
        user to check their email.  No distinction is provided to discourage
        "oafish attempts at hacking", as duncan poetically put it.
        """
        requests = []
        def handleRequest(username, url):
            requests.append((username, url))

        class Request(FakeRequest):
            method = 'POST'
            def __init__(self, *a, **k):
                FakeRequest.__init__(self, *a, **k)
                self.args = {'username': [''],
                             'email': [bogusEmail]}

        self.reset.handleRequestForUser = handleRequest
        d = renderPage(self.reset, reqFactory=Request)
        def completedRequest():
            self.assertEqual(len(requests), 0)
        d.addCallback(lambda ign: completedRequest())
        return d


    def test_notPresentEmailAddress(self):
        """
        If an email address is not present in the system, no notification
        should be sent, but the user should receive the same feedback as if it
        worked, to discourage cracking attempts.
        """
        return self.specifyBogusEmail('not-in-the-system@example.com')


    def test_malformedEmailAddress(self):
        """
        If a malformed email address is provided, no notification should be
        sent, but the user should receive the same feedback as if it worked, to
        discourage cracking attempts.
        """
        return self.specifyBogusEmail('hello, world!')
