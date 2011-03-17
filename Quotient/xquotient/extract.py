import re

from zope.interface import implements

from twisted.python.components import registerAdapter

from nevow import tags
from nevow.inevow import IRenderer

from epsilon.extime import Time

from axiom.item import Item, declareLegacyItem
from axiom import attributes
from axiom.upgrade import registerUpgrader
from axiom.dependency import dependsOn

from xquotient import mail
from xquotient.gallery import Image, ImageSet, makeThumbnail, Gallery, ThumbnailDisplayer
from xquotient.exmess import Message

def extractImages(message):
    imageSet = None
    for attachment in message.walkAttachments():
        if attachment.type.startswith('image/'):
            thumbdir = message.store.newDirectory('thumbnails')
            if not thumbdir.exists():
                thumbdir.makedirs()

            basename = (str(attachment.messageID)
                            + '-' + str(attachment.identifier))

            # TODO pass attachment.part.source to image magick
            imgdata = attachment.part.getBody(decode=True)
            thumbf = thumbdir.child(basename)
            makeThumbnail(imgdata, thumbf.path)

            if imageSet is None:
                imageSet = ImageSet(store=message.store,
                                    message=message)

            Image(part=attachment.part,
                  thumbnailPath=thumbf,
                  message=message,
                  mimeType=unicode(attachment.type),
                  imageSet=imageSet,
                  store=message.store)

class ExtractRenderer:
    implements(IRenderer)

    def __init__(self, extract):
        self.extract = extract

    def rend(self, *junk):
        (l, middle, r) = self.extract.inContext()
        return tags.div(class_='extract-container')[
                l,
                tags.div(class_='extract-text')[
                    tags.span[middle]],
                r]

# the idea with extraction is that we only store an extract
# once per sender.  so if you import the last 5 years worth
# of bugtraq daily message digests, and each one ends with a
# long sig listing a bunch of email addresses, we we will
# only store each unique address once so they at least show up in
# the extracts-per-person view.  highlighting the extracts
# per message will be done by client-side code.

class SimpleExtractMixin(object):

    # a lot of class methods. though it is less weird this way i think

    def findExisting(cls, message, extractedText):
        return message.store.findUnique(cls,
                        attributes.AND(cls.text == extractedText,
                                       cls.message == Message.storeID,
                                       Message.sender == message.sender),
                        default=None)

    findExisting = classmethod(findExisting)

    def worthStoring(message, extractedText):
        return True

    worthStoring = staticmethod(worthStoring)

    def extract(cls, message):
        def updateExtract(e, **kw):
            for (k, v) in kw.iteritems():
                if getattr(e, k) != v:
                    setattr(e, k, v)

        for part in message.impl.getTypedParts('text/plain'):
            for match in cls.regex.finditer(part.getUnicodeBody()):
                (start, end) = match.span()
                extractedText = match.group()

                if cls.worthStoring(message, extractedText):
                    existing = cls.findExisting(message, extractedText)
                    if existing is not None:
                        f = lambda **k: updateExtract(existing, **k)
                    else:
                        f = lambda **k: cls(store=message.store, **k)

                    f(message=message,
                      part=part,
                      timestamp=Time(),
                      text=extractedText,
                      start=start,
                      end=end)

    extract = classmethod(extract)

    def inContext(self, chars=30):
        text = self.part.getUnicodeBody()
        (start, end) = (self.start, self.end)

        return (text[start-chars:start],
                self.asStan(),
                text[end:end+chars])

def registerExtractUpgrader1to2(itemClass):
    registerUpgrader(lambda old: old.deleteFromStore(), itemClass.typeName, 1, 2)

class URLExtract(SimpleExtractMixin, Item):
    typeName = 'quotient_url_extract'
    schemaVersion = 2

    start = attributes.integer()
    end = attributes.integer()
    text = attributes.text(indexed=True)

    message = attributes.reference()
    part = attributes.reference()
    timestamp = attributes.timestamp()

    person = attributes.reference()

    regex = re.compile(ur'(?:\w+:\/\/|www\.)[^\s\<\>\'\(\)\"]+[^\s\<\>\(\)\'\"\?\.]',
                       re.UNICODE | re.IGNORECASE)

    def asStan(self):
        return tags.b[tags.a(href=self.text)[self.text]]

registerAdapter(ExtractRenderer, URLExtract, IRenderer)
registerExtractUpgrader1to2(URLExtract)

class PhoneNumberExtract(SimpleExtractMixin, Item):

    typeName = 'quotient_phone_number_extract'
    schemaVersion = 2

    start = attributes.integer()
    end = attributes.integer()
    text = attributes.text(indexed=True)

    message = attributes.reference()
    part = attributes.reference()
    timestamp = attributes.timestamp()

    person = attributes.reference()

    regex = re.compile(ur'%(area)s%(body)s%(extn)s' % dict(area=r'(?:(?:\(?\d{3}\)?[-.\s]?|\d{3}[-.\s]))?',
                                                           body=r'\d{3}[-.\s]\d{4}',
                                                           extn=r'(?:\s?(?:ext\.?|\#)\s?\d+)?'),
                       re.UNICODE | re.IGNORECASE)

    def asStan(self):
        return tags.b[self.text]

registerAdapter(ExtractRenderer, PhoneNumberExtract, IRenderer)
registerExtractUpgrader1to2(PhoneNumberExtract)

class EmailAddressExtract(SimpleExtractMixin, Item):

    typeName = 'quotient_email_address_extract'
    schemaVersion = 2

    start = attributes.integer()
    end = attributes.integer()
    text = attributes.text(indexed=True)

    message = attributes.reference()
    part = attributes.reference()
    timestamp = attributes.timestamp()

    person = attributes.reference()

    regex = re.compile(ur'[\w\-\.]+@(?:[a-z0-9-]+\.)+[a-z]+',
                       re.UNICODE | re.IGNORECASE)

    def worthStoring(message, extractedText):
        return not message.sender == extractedText

    worthStoring = staticmethod(worthStoring)

    def asStan(self):
        return tags.b[self.text]

registerAdapter(ExtractRenderer, EmailAddressExtract, IRenderer)
registerExtractUpgrader1to2(EmailAddressExtract)

extractTypes = {'url': URLExtract,
                'phone number': PhoneNumberExtract,
                'email address': EmailAddressExtract}


class ExtractPowerup(Item):
    schemaVersion = 2
    gallery = dependsOn(Gallery)
    thumbnailDisplayer = dependsOn(ThumbnailDisplayer)

    def installed(self):
        self.store.findUnique(mail.MessageSource).addReliableListener(self)

    def processItem(self, message):
        extractImages(message)

        for et in extractTypes.itervalues():
            et.extract(message)

declareLegacyItem(ExtractPowerup.typeName, 1, dict(
    installedOn = attributes.reference()))

def _extractPowerup1to2(old):
    return old.upgradeVersion(ExtractPowerup.typeName, 1, 2,
                              gallery=old.store.findOrCreate(Gallery),
                              thumbnailDisplayer=old.store.findOrCreate(ThumbnailDisplayer))
registerUpgrader(_extractPowerup1to2, ExtractPowerup.typeName, 1, 2)
