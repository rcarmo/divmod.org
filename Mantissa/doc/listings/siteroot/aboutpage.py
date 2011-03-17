from zope.interface import implements

from axiom.item import Item
from axiom.attributes import text

from nevow.page import Element, renderer
from nevow.loaders import stan
from nevow.tags import div, directive

from xmantissa.ixmantissa import ISiteRootPlugin, INavigableFragment

class AboutPlugin(Item):
    info = text(default=u'This is a great site!')
    powerupInterfaces = (ISiteRootPlugin,)
    implements(*powerupInterfaces)

    def produceResource(self, request, segments, viewer):
        if segments == tuple(['about.php']):
            return viewer.wrapModel(AboutText(self.info)), ()

class AboutText(Element):
    implements(INavigableFragment)
    docFactory = stan(div(render=directive("about")))
    def __init__(self, text):
        self.text = text

    @renderer
    def about(self, request, tag):
        return tag[self.text]
