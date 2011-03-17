# Copyright 2006-2008 Divmod, Inc.
# See LICENSE file for details

"""
Tests for L{xmantissa.websession}.
"""

from twisted.trial.unittest import TestCase
from nevow.testutil import FakeRequest

from xmantissa.websession import PersistentSessionWrapper, usernameFromRequest


class TestUsernameFromRequest(TestCase):

    def test_domainUnspecified(self):
        """
        Test that L{usernameFromRequest} adds the value of host header to the
        username in the request if the username doesn't already specify a
        domain.
        """
        request = FakeRequest(headers={'host': 'divmod.com'})
        request.args = {'username': ['joe']}
        username = usernameFromRequest(request)
        self.assertEqual(username, 'joe@divmod.com')


    def test_domainSpecified(self):
        """
        Test that L{usernameFromRequest} returns the username in the request
        if that username specifies a domain.
        """
        request = FakeRequest(headers={'host': 'divmod.com'})
        request.args = {'username': ['joe@notdivmod.com']}
        username = usernameFromRequest(request)
        self.assertEqual(username, 'joe@notdivmod.com')



class TestPersistentSessionWrapper(TestCase):
    """
    Tests for L{PersistentSessionWrapper}.
    """
    def test_savorSessionCookie(self):
        """
        L{PersistentSessionWrapper.savorSessionCookie} adds a cookie with a
        large maximum age and a request-appropriate domain to the request.
        """
        request = FakeRequest(headers={'host': 'example.com'})
        resource = PersistentSessionWrapper(
            None, None, domains=['example.org', 'example.com'])

        resource.savorSessionCookie(request)
        self.assertEqual(
            request.cookies, {resource.cookieKey: request.getSession().uid})


    def _cookieTest(self, host, cookie, **kw):
        """
        Assert that a L{PersistentSessionWrapper} created with the given
        keyword arguments returns C{cookie} from its C{cookieDomainForRequest}
        method when passed a request with C{host} as the value for its I{Host}
        header.
        """
        request = FakeRequest(headers={'host': host})
        resource = PersistentSessionWrapper(None, None, **kw)
        self.assertEqual(resource.cookieDomainForRequest(request), cookie)


    def test_missingHostHeaderCookie(self):
        """
        L{PersistentSessionWrapper.cookieDomainForRequest} returns C{None} if
        no host header is present.
        """
        self._cookieTest(None, None)


    def test_noDomainsNoSubdomainsCookie(self):
        """
        L{PersistentSessionWrapper.cookieDomainForRequest} returns C{None} if
        no domain sequence is provided and subdomains are disabled.
        """
        self._cookieTest('example.com', None)


    def test_noDomainsSubdomainsCookie(self):
        """
        L{PersistentSessionWrapper.cookieDomainForRequest} returns the hostname
        from the request prefixed with C{"."} if no domain sequence is provided
        and subdomains are enabled.
        """
        self._cookieTest('example.com', '.example.com', enableSubdomains=True)


    def test_domainNotFoundNoSubdomainsCookie(self):
        """
        L{PersistentSessionWrapper.cookieDomainForRequest} returns the C{None}
        if the hostname from the request is not found in the supplied domain
        sequence and subdomains are disabled.
        """
        self._cookieTest('example.com', None, domains=['example.org'])


    def test_domainNotFoundSubdomainsCookie(self):
        """
        L{PersistentSessionWrapper.cookieDomainForRequest} returns the hostname
        from the request prefixed with C{"."} if the hostname from the request
        is not found in the supplied domain sequence and subdomains are
        enabled.
        """
        self._cookieTest('example.com', ".example.com", domains=['example.org'],
                         enableSubdomains=True)


    def test_domainFoundNoSubdomainsCookie(self):
        """
        L{PersistentSessionWrapper.cookieDomainForRequest} returns C{None} if
        the hostname from the request is found in the supplied domain sequence
        and subdomains are disabled.
        """
        self._cookieTest('example.com', None, domains=['example.com'])


    def test_domainFoundSubdomainsCookie(self):
        """
        L{PersistentSessionWrapper.cookieDomainForRequest} returns the hostname
        from the request prefixed with C{"."} if the hostname from the request
        is found in the supplied domain sequence and subdomains are enabled.
        """
        self._cookieTest('example.com', ".example.com",
                         domains=['example.com'], enableSubdomains=True)


    def test_subdomainFoundNoSubdomainsCookie(self):
        """
        L{PersistentSessionWrapper.cookieDomainForRequest} returns C{None} if
        the hostname from the request is a subdomain of one of the domains in
        the supplied domain sequence but subdomains are disabled.
        """
        self._cookieTest('alice.example.com', None, domains=['example.com'])


    def test_subdomainFoundSubdomainsCookie(self):
        """
        L{PersistentSessionWrapper.cookieDomainForRequest} returns the domain
        from the supplied domain sequence prefixed with C{"."} that the
        hostname from the request is found to be a subdomain of, if it is found
        to be a subdomain of any of them and subdomains are enabled.
        """
        self._cookieTest('alice.example.com', '.example.com',
                         domains=['example.com'], enableSubdomains=True)


    def test_explicitPortNumberCookie(self):
        """
        L{PersistentSessionWrapper.cookieDomainForRequest} disregards the port
        number in the request host.
        """
        self._cookieTest('alice.example.com:8080', '.example.com',
                         domains=['example.com'], enableSubdomains=True)
