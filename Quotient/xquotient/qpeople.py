# -*- test-case-name: xquotient.test.test_qpeople -*-

from zope.interface import implements

from nevow import rend, inevow, tags
from nevow.flat import flatten

from axiom.item import Item
from axiom import attributes
from axiom.upgrade import registerUpgrader
from axiom.dependency import dependsOn
from xmantissa import ixmantissa, people, liveform
from xmantissa.webtheme import getLoader
from xmantissa.fragmentutils import dictFillSlots

from xquotient import extract, mail, exmess, gallery

from xmantissa.scrolltable import UnsortableColumn, AttributeColumn, TYPE_FRAGMENT

from xquotient.exmess import MailboxSelector, CLEAN_STATUS

def makePersonExtracts(store, person):
    def queryMessageSenderPerson(typ):
        # having Message.person might speed this up, but it would
        # need some kind of notification thing that fires each time
        # an email address is associated with a Person item so we
        # can update the attribute
        sq = MailboxSelector(store)
        sq.refineByPerson(person)
        return store.query(typ, attributes.AND(
                typ.message == exmess.Message.storeID,
                sq._getComparison()))

    for etyp in extract.extractTypes.itervalues():
        for e in queryMessageSenderPerson(etyp):
            person.registerExtract(e)
            e.person = person

    for imageSet in queryMessageSenderPerson(gallery.ImageSet):
        person.registerExtract(imageSet)
        imageSet.person = person



class AddPersonFragment(liveform.LiveForm):
    """
    L{liveform.LiveForm} which creates a person and associates an email
    address with them.
    """
    jsClass = u'Quotient.Common.AddPerson'

    def __init__(self, organizer):
        self.organizer = organizer
        liveform.LiveForm.__init__(
            self, self.addPerson,
            (liveform.Parameter(
                'nickname',
                liveform.TEXT_INPUT,
                people._normalizeWhitespace,
                'Name'),
             liveform.Parameter(
                 'email',
                 liveform.TEXT_INPUT,
                 people._normalizeWhitespace,
                 'Email')),
             description=u'Add Person')


    def addPerson(self, nickname, email):
        """
        Make a person with the given name and email address.

        @type nickname: C{unicode}

        @type email: C{unicode}

        @rtype: L{people.PersonFragment}
        """
        person = self.organizer.createPerson(nickname)
        self.organizer.createContactItem(
            people.EmailContactType(self.organizer.store),
            person,
            {'email': email})
        return people.PersonFragment(person)



class CorrespondentExtractor(Item):
    """
    Creates items based on the people involved with particular messages.
    """
    installedOn = attributes.reference()

    def installed(self):
        self.store.findUnique(mail.MessageSource).addReliableListener(self)


    def processItem(self, item):
        """
        This was dead code.  It has been deleted.  (This is only here to avoid
        breaking old databases.)
        """

class PersonFragmentColumn(UnsortableColumn):
    person = None

    def extractValue(self, model, item):
        # XXX BAD
        f = people.PersonFragment(self.person)
        return unicode(flatten(f), 'utf-8')

    def getType(self):
        return TYPE_FRAGMENT

class MessageList(rend.Fragment):
    def __init__(self, messageLister, person):
        self.messageLister = messageLister
        self.person = person
        rend.Fragment.__init__(self, docFactory=getLoader('person-messages'))

    def render_messages(self, *junk):
        iq = inevow.IQ(self.docFactory)
        msgpatt = iq.patternGenerator('message')
        newpatt = iq.patternGenerator('unread-message')
        content = []
        addresses = set(self.person.store.query(
                            people.EmailAddress,
                            people.EmailAddress.person == self.person).getColumn('address'))

        wt = ixmantissa.IWebTranslator(self.person.store)
        link = lambda href, text: tags.a(href=href, style='display: block')[text]

        displayName = self.person.getDisplayName()
        for m in self.messageLister.mostRecentMessages(self.person):
            if m.sender in addresses:
                sender = displayName
            else:
                sender = 'Me'
            if m.read:
                patt = msgpatt
            else:
                patt = newpatt
            if not m.subject or m.subject.isspace():
                subject = '<no subject>'
            else:
                subject = m.subject

            url = wt.linkTo(m.storeID)
            content.append(dictFillSlots(patt,
                                         dict(sender=link(url, sender),
                                              subject=link(url, subject),
                                              date=link(url, m.receivedWhen.asHumanly()))))

        if 0 < len(content):
            return iq.onePattern('messages').fillSlots('messages', content)
        return iq.onePattern('no-messages')

class ExcerptColumn(AttributeColumn):
    def extractValue(self, model, item):
        return unicode(flatten(item.inContext()), 'utf-8')

    def getType(self):
        return TYPE_FRAGMENT

class SubjectColumn(AttributeColumn):
    def extractValue(self, model, item):
        return item.message.subject


class MessageLister(Item):
    implements(ixmantissa.IOrganizerPlugin)

    typeName = 'quotient_message_lister_plugin'
    schemaVersion = 2

    installedOn = attributes.reference()
    powerupInterfaces = (ixmantissa.IOrganizerPlugin,)
    organizer = dependsOn(people.Organizer)

    name = u'Messages'

    def personalize(self, person):
        return MessageList(self, person)

    def mostRecentMessages(self, person, n=5):
        """
        @param person: L{xmantissa.people.Person}
        @return: sequence of C{n} L{xquotient.exmess.Message} instances,
                 each one a message either to or from C{person}, ordered
                 descendingly by received date.
        """

        sq = MailboxSelector(self.store)
        sq.refineByStatus(CLEAN_STATUS)
        sq.refineByPerson(person)
        sq.setLimit(n)
        sq.setNewestFirst()
        return list(sq)

def messageLister1to2(old):
    """
    Upgrade the L{MessageLister} object from schema version 1 to 2, by filling
    out its 'organizer' slot with an L{Organizer} item, creating it if
    necessary.
    """
    ml = old.upgradeVersion(MessageLister.typeName, 1, 2)
    # During upgrading __init__ is run, which means that the Organizer (version
    # 2 in the historical tests, 3 as of this writing) will try to create a
    # Person during its creation and notify IOrganizerPlugin powerups about it.
    #
    # MessageLister is an IOrganizerPlugin, so it gets caught in the powerup
    # query.  Since it's Powerup items which are being queried for,
    # MessageLister is loaded by reference.  The load by reference triggers
    # this upgrader.  This upgrader then finds or creates an Organizer.  If we
    # don't check for the old not-fully-upgraded Organizer item, then we will
    # end up with 2 Organizer items (one that was upgraded, one created by this
    # upgrader) which causes the test - which correctly does a
    # findUnique(Organizer) since there should only be one - to fail.
    #
    # This edge case (the fact that other dependencies that will be queried for
    # might not be fully upgraded at the time that an upgrader runs) can really
    # occur during any upgrade, and it might be worthwhile to standardize this
    # idiom to limit the exposure of future upgraders.  However, as it stands
    # it's a bit of a hack, so this upgrader has been modified just far enough
    # to get its own historical tests to pass.
    #
    # -glyph
    for oldSchemaVersion in range(2, people.Organizer.schemaVersion):
        oldOrganizer = ml.store.getOldVersionOf(
            people.Organizer.typeName, oldSchemaVersion)
        ml.organizer = ml.store.findUnique(oldOrganizer, default=None)
        if ml.organizer is not None:
            return ml
    ml.organizer = ml.store.findOrCreate(people.Organizer)
    return ml

registerUpgrader(messageLister1to2, MessageLister.typeName, 1, 2)

class ImageLister(Item):
    typeName = 'quotient_image_lister_plugin'
    schemaVersion = 2
    z = attributes.integer()

class ExtractLister(Item):
    typeName = 'quotient_extract_lister_plugin'
    schemaVersion = 2
    z = attributes.integer()

def anyLister1to2(old):
    new = old.upgradeVersion(old.typeName, 1, 2)
    new.store.findUnique(people.Organizer).powerDown(new, ixmantissa.IOrganizerPlugin)
    new.deleteFromStore()

registerUpgrader(anyLister1to2, ImageLister.typeName, 1, 2)
registerUpgrader(anyLister1to2, ExtractLister.typeName, 1, 2)
