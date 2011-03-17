from axiom.item import Item
from axiom import attributes
from axiom.upgrade import registerDeletionUpgrader

class Settings(Item):
    typeName = 'mantissa_settings'
    schemaVersion = 2

    installedOn = attributes.reference()

def settings1to2(old):
    new = old.upgradeVersion('mantissa_settings', 1, 2,
                             installedOn=None)
    new.deleteFromStore()

registerDeletionUpgrader(Settings, 1, 2)
