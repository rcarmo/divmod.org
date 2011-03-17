
"""
Tests for the upgrade of L{PrivateApplication} schema from 3 to 4.
"""

from axiom.userbase import LoginSystem
from axiom.test.historic.stubloader import StubbedTest

from xmantissa.ixmantissa import ITemplateNameResolver, IWebViewer
from xmantissa.website import WebSite
from xmantissa.webapp import PrivateApplication
from xmantissa.publicweb import CustomizedPublicPage
from xmantissa.webgestalt import AuthenticationApplication
from xmantissa.prefs import PreferenceAggregator, DefaultPreferenceCollection
from xmantissa.search import SearchAggregator

from xmantissa.test.historic.stub_privateApplication3to4 import (
    USERNAME, DOMAIN, PREFERRED_THEME, PRIVATE_KEY)

class PrivateApplicationUpgradeTests(StubbedTest):
    """
    Tests for L{xmantissa.webapp.privateApplication3to4}.
    """
    def setUp(self):
        d = StubbedTest.setUp(self)
        def siteStoreUpgraded(ignored):
            loginSystem = self.store.findUnique(LoginSystem)
            account = loginSystem.accountByAddress(USERNAME, DOMAIN)
            self.subStore = account.avatars.open()
            return self.subStore.whenFullyUpgraded()
        d.addCallback(siteStoreUpgraded)
        return d


    def test_powerup(self):
        """
        At version 4, L{PrivateApplication} should be an
        L{ITemplateNameResolver} powerup on its store.
        """
        application = self.subStore.findUnique(PrivateApplication)
        powerups = list(self.subStore.powerupsFor(ITemplateNameResolver))
        self.assertIn(application, powerups)


    def test_webViewer(self):
        """
        At version 5, L{PrivateApplication} should be an
        L{IWebViewer} powerup on its store.
        """
        application = self.subStore.findUnique(PrivateApplication)
        interfaces = list(self.subStore.interfacesFor(application))
        self.assertIn(IWebViewer, interfaces)


    def test_attributes(self):
        """
        All of the attributes of L{PrivateApplication} should have the same
        values on the upgraded item as they did before the upgrade.
        """
        application = self.subStore.findUnique(PrivateApplication)
        self.assertEqual(application.preferredTheme, PREFERRED_THEME)
        self.assertEqual(application.privateKey, PRIVATE_KEY)

        website = self.subStore.findUnique(WebSite)
        self.assertIdentical(application.website, website)

        customizedPublicPage = self.subStore.findUnique(CustomizedPublicPage)
        self.assertIdentical(
            application.customizedPublicPage, customizedPublicPage)

        authenticationApplication = self.subStore.findUnique(
            AuthenticationApplication)
        self.assertIdentical(
            application.authenticationApplication, authenticationApplication)

        preferenceAggregator = self.subStore.findUnique(PreferenceAggregator)
        self.assertIdentical(
            application.preferenceAggregator, preferenceAggregator)

        defaultPreferenceCollection = self.subStore.findUnique(
            DefaultPreferenceCollection)
        self.assertIdentical(
            application.defaultPreferenceCollection,
            defaultPreferenceCollection)

        searchAggregator = self.subStore.findUnique(SearchAggregator)
        self.assertIdentical(application.searchAggregator, searchAggregator)

        self.assertIdentical(application.privateIndexPage, None)
