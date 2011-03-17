# Copyright 2008 Divmod, Inc. See LICENSE file for details

"""
Tests for AMPConfiguration's 1 to 2 upgrader.
"""

from axiom.test.historic import stubloader
from axiom.userbase import LoginSystem

from xmantissa.ampserver import AMPConfiguration
from xmantissa.ixmantissa import IOneTimePadGenerator


class AMPConfigurationUpgradeTests(stubloader.StubbedTest):
    """
    Tests for AMPConfiguration's 1 to 2 upgrader.
    """
    def test_attributeCopied(self):
        """
        L{AMPConfiguration.loginSystem}'s value should have been preserved.
        """
        self.assertIdentical(
            self.store.findUnique(AMPConfiguration).loginSystem,
            self.store.findUnique(LoginSystem))


    def test_poweredUp(self):
        """
        L{AMPConfiguration} should be powered-up as L{IOneTimePadGenerator}.
        """
        self.assertIdentical(
            IOneTimePadGenerator(self.store),
            self.store.findUnique(AMPConfiguration))
