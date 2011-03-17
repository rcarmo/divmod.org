
"""
This module is a very simple test to verify that un-upgraded Hyperbola
items don't cause stores to become unopenable.
"""

from axiom.test.historic.stubloader import StubbedTest

from hyperbola.hyperbola_model import HyperbolaPublicPresence


class StoreStillOpens(StubbedTest):
    """
    Tests to verify that HyperbolaPublicPresence won't cause undue problems.
    """
    def test_itemExists(self):
        """
        Verify that the item will still exist.
        """
        hpp = self.store.findUnique(HyperbolaPublicPresence)

