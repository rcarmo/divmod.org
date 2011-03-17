
from zope.interface import Interface

class IMenuApplication(Interface):
    """
    I am one GTK application that hooks into Prime's internals and provides
    menu items for the menu.
    """

    def register(menuSection):
        """
        Initialize this application by adding it to a
        L{prime.gtk2prime.MenuSection}.
        """

