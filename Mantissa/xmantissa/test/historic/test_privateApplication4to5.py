
"""
Tests for the upgrade of L{PrivateApplication} schema from 4 to 5, which was
dropping the 'hitCount' variable and adding the L{IWebViewer} powerup.
"""

from xmantissa.test.historic.test_privateApplication3to4 import (
    PrivateApplicationUpgradeTests)

class PrivateApplicationUpgradeTests5(PrivateApplicationUpgradeTests):
    """
    Tests for L{xmantissa.webapp.privateApplication4to5}.
    """

