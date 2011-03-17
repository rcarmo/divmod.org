from axiom.item import Item
from axiom import attributes

class QuotientPublicPage(Item):
    """
    Needed for schema compatibility only.
    """
    typeName = 'quotient_public_page'
    schemaVersion = 1

    installedOn = attributes.reference()
