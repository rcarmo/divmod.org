from twisted.python.components import registerAdapter
from axiom.attributes import reference
from axiom.item import Item
from nevow.page import Element
from xmantissa.ixmantissa import INavigableElement, INavigableFragment
from xmantissa.webnav import Tab
from zope.interface import implements, Interface

class ISuspender(Interface):
    """
    Marker interface for suspended powerup facades.
    """

class SuspendedNavigableElement(Item):
    implements(INavigableElement, ISuspender)
    powerupInterfaces = (INavigableElement, ISuspender)

    originalNE = reference()

    def getTabs(self):
        origTabs = self.originalNE.getTabs()
        def proxyTabs(tabs):
            for tab in tabs:
                yield Tab(tab.name, self.storeID, tab.priority,
                          proxyTabs(tab.children),
                          authoritative=tab.authoritative,
                          linkURL=tab.linkURL)

        return proxyTabs(origTabs)

class SuspendedFragment(Element):
    """
    Temporary account-suspended fragment.
    """
    fragmentName = 'suspend'
    live = False
    implements(INavigableFragment)

    def head(self):
        pass

registerAdapter(SuspendedFragment, SuspendedNavigableElement, INavigableFragment)



def suspendJustTabProviders(installation):
    """
    Replace INavigableElements with facades that indicate their suspension.
    """
    if installation.suspended:
        raise RuntimeError("Installation already suspended")
    powerups = list(installation.allPowerups)
    for p in powerups:
        if INavigableElement.providedBy(p):
            p.store.powerDown(p, INavigableElement)
            sne = SuspendedNavigableElement(store=p.store, originalNE=p)
            p.store.powerUp(sne, INavigableElement)
            p.store.powerUp(sne, ISuspender)
    installation.suspended = True

def unsuspendTabProviders(installation):
    """
    Remove suspension facades and replace them with their originals.
    """
    if not installation.suspended:
        raise RuntimeError("Installation not suspended")
    powerups = list(installation.allPowerups)
    allSNEs = list(powerups[0].store.powerupsFor(ISuspender))
    for p in powerups:
        for sne in allSNEs:
            if sne.originalNE is p:
                p.store.powerDown(sne, INavigableElement)
                p.store.powerDown(sne, ISuspender)
                p.store.powerUp(p, INavigableElement)
                sne.deleteFromStore()
    installation.suspended = False
