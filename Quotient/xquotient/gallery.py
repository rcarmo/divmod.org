import itertools

from zope.interface import implements
from twisted.python.components import registerAdapter

from nevow import rend, static, flat, athena, tags, inevow
from nevow.athena import expose

from axiom.item import Item
from axiom import attributes
from axiom.upgrade import registerUpgrader

from xmantissa import ixmantissa, webnav, website, people, tdb
from xmantissa.fragmentutils import dictFillSlots, PatternDictionary

from xquotient.actions import SenderPersonFragment

from PIL import Image as PilImage
from cStringIO import StringIO

def makeThumbnail(data, outpath, thumbSize=135):
    try:
        # i since noticed that PIL.Image has a thumbnail method, maybe use
        # that instead
        image = PilImage.open(StringIO(data))
        # Calculate scale
        (width, height) = image.size
        biggest = max(width, height)
        scale = float(thumbSize) / max(biggest, thumbSize)
        # Do the thumbnailing
        image.resize((int(width * scale), int(height * scale)), True).save(outpath, 'jpeg')
    except IOError:
        pass

class ImageSetRenderer:
    implements(inevow.IRenderer)

    def __init__(self, imageSet):
        self.imageSet = imageSet

    def rend(self, *junk):
        prefixURL = '/' + self.imageSet.store.findUnique(ThumbnailDisplayer).prefixURL + '/'
        toWebID = ixmantissa.IWebTranslator(self.imageSet.store).toWebID

        return (tags.img(src=prefixURL + toWebID(img), width='20%', height='20%')
                    for img in self.imageSet.getImages())

class ImageSet(Item):
    message = attributes.reference()
    person = attributes.reference()

    def getImages(self):
        return self.store.query(Image, Image.imageSet == self)

registerAdapter(ImageSetRenderer, ImageSet, inevow.IRenderer)

class Image(Item):
    typeName = 'quotient_image'
    schemaVersion = 2

    part = attributes.reference()
    thumbnailPath = attributes.path()
    mimeType = attributes.text()
    imageSet = attributes.reference()

    message = attributes.reference()

def image1to2(old):
    new = old.upgradeVersion('quotient_image', 1, 2,
                             part=old.part,
                             mimeType=old.mimeType,
                             message=old.message,
                             imageSet=None)
    # XXX HACK
    new.thumbnailPath = old.thumbnailPath
    return new

registerUpgrader(image1to2, 'quotient_image', 1, 2)

class ThumbnailDisplay(rend.Page):

    def __init__(self, original):
        self.translator = ixmantissa.IWebTranslator(original.store)
        rend.Page.__init__(self, original)

    def locateChild(self, ctx, segments):
        if len(segments) == 1:
            imageWebID = segments[0]
            imageStoreID = self.translator.linkFrom(imageWebID)

            if imageStoreID is not None:
                image = self.original.store.getItemByID(imageStoreID)
                return (static.File(image.thumbnailPath.path), ())

        return rend.NotFound

class ThumbnailDisplayer(Item, website.PrefixURLMixin):
    typeName = 'quotient_thumbnail_displayer'
    schemaVersion = 1

    prefixURL = 'private/thumbnails'
    installedOn = attributes.reference()

    sessioned = True
    sessionless = False

    def createResource(self):
        return ThumbnailDisplay(self)

class Gallery(Item):
    implements(ixmantissa.INavigableElement)

    typeName = 'quotient_gallery'
    schemaVersion = 1

    installedOn = attributes.reference()

    powerupInterfaces = (ixmantissa.INavigableElement,)

    def getTabs(self):
        return [webnav.Tab('Mail', self.storeID, 0.6, children=
                    [webnav.Tab('Gallery', self.storeID, 0.0)],
                authoritative=False)]

class GalleryScreen(athena.LiveFragment):
    implements(ixmantissa.INavigableFragment)

    fragmentName = 'gallery'
    live = 'athena'
    title = ''
    jsClass = u'Quotient.Gallery.Controller'

    organizer = None

    itemsPerRow = 5
    rowsPerPage = 4

    def __init__(self, original):
        athena.LiveFragment.__init__(self, original)
        self.organizer = original.store.findUnique(people.Organizer)
        self.translator = ixmantissa.IWebTranslator(original.store)

        self.tdm = tdb.TabularDataModel(original.store, Image, (Image.message,),
                                        baseComparison=self._getComparison(),
                                        defaultSortColumn='message',
                                        itemsPerPage=self.itemsPerRow * self.rowsPerPage)
    def _getComparison(self):
        return None

    def _currentPage(self):
        patterns = PatternDictionary(self.docFactory)
        self.items = list(d['__item__'] for d in self.tdm.currentPage())
        lastMessageID = None
        imageClasses = itertools.cycle(('gallery-image', 'gallery-image-alt'))

        if 0 < len(self.items):
            for (i, image) in enumerate(self.items):
                if 0 < i and i % self.itemsPerRow == 0:
                    yield patterns['row-separator']()

                message = image.message
                if message.storeID != lastMessageID:
                    imageClass = imageClasses.next()
                    lastMessageID = message.storeID

                imageURL = (self.translator.linkTo(message.storeID)
                            + '/attachments/'
                            + self.translator.toWebID(image.part)
                            + '/' + image.part.getFilename())
                thumbURL = '/private/thumbnails/' + self.translator.toWebID(image)

                person = self.organizer.personByEmailAddress(message.sender)
                if person is None:
                    personStan = SenderPersonFragment(message)
                else:
                    personStan = people.PersonFragment(person)
                personStan.page = self.page

                yield dictFillSlots(patterns['image'],
                                        {'image-url': imageURL,
                                        'thumb-url': thumbURL,
                                        'message-url': self.translator.linkTo(message.storeID),
                                        'message-subject': message.subject,
                                        'sender-stan': personStan,
                                        'class': imageClass})
        else:
            yield patterns['no-images']()

    def render_images(self, ctx, data):
        return ctx.tag[self._currentPage()]

    def _paginationLinks(self):
        patterns = PatternDictionary(self.docFactory)
        if self.tdm.hasPrevPage():
            pp = patterns['prev-page']()
        else:
            pp = ''
        if self.tdm.hasNextPage():
            np = patterns['next-page']()
        else:
            np = ''
        return (pp, np)

    def render_paginationLinks(self, ctx, data):
        return ctx.tag[self._paginationLinks()]

    def _flatten(self, thing):
        return unicode(flat.flatten(thing), 'utf-8')

    def nextPage(self):
        self.tdm.nextPage()
        return map(self._flatten, (self._currentPage(), self._paginationLinks()))
    expose(nextPage)

    def prevPage(self):
        self.tdm.prevPage()
        return map(self._flatten, (self._currentPage(), self._paginationLinks()))
    expose(prevPage)

    def head(self):
        return None

registerAdapter(GalleryScreen, Gallery, ixmantissa.INavigableFragment)
