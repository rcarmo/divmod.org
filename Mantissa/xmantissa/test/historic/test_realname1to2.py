
"""
Tests for the upgrade from schema version 1 to 2 of RealName, which deletes the
item.
"""

from axiom.test.historic.stubloader import StubbedTest

from xmantissa.people import Person, RealName


class RealNameUpgradeTests(StubbedTest):
    def test_deleted(self):
        """
        The L{RealName} should no longer exist in the database.
        """
        self.assertEqual(self.store.query(RealName).count(), 0)
