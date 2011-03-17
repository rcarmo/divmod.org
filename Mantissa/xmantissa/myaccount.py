"""
This module is here to satisfy old databases that contain MyAccount items
"""

from axiom.item import Item
from axiom.upgrade import registerUpgrader

class MyAccount(Item):
    typeName = 'mantissa_myaccount'
    schemaVersion = 2

def deleteMyAccount(old):
    # Just get rid of the old account object.  Don't even create a new one.
    old.deleteFromStore()
    return None

registerUpgrader(deleteMyAccount, 'mantissa_myaccount', 1, 2)
