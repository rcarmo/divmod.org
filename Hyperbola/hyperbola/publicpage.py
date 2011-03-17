"""
This module exists only for schema compatibility for existing databases. As
soon as Axiom supports removing types from a store, this module can be deleted.
"""

from axiom.item import Item
from axiom import attributes

class HyperbolaPublicPage(Item):
    """
    Needed for schema compatibility only.
    """
    installedOn = attributes.reference()
