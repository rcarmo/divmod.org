# -*- test-case-name: xmantissa.test.test_people -*-
# Copyright 2008 Divmod, Inc. See LICENSE file for details

"""
Person item and related functionality.
"""

from warnings import warn

try:
    from PIL import Image
except ImportError:
    Image = None

# Python < 2.5 compatibility
try:
    from email.utils import getaddresses
except ImportError:
    from email.Utils import getaddresses

from zope.interface import implements

from twisted.python import components
from twisted.python.filepath import FilePath
from twisted.python.reflect import qual

from nevow import rend, athena, inevow, static, tags, url
from nevow.athena import expose, LiveElement
from nevow.loaders import stan
from nevow.page import Element, renderer
from nevow.taglibrary import tabbedPane
from formless import nameToLabel

from epsilon import extime
from epsilon.structlike import record
from epsilon.descriptor import requiredAttribute

from axiom import item, attributes
from axiom.tags import Tag
from axiom.dependency import dependsOn
from axiom.attributes import boolean
from axiom.upgrade import (
    registerUpgrader, registerAttributeCopyingUpgrader,
    registerDeletionUpgrader)
from axiom.userbase import LoginAccount, LoginMethod

from xmantissa.ixmantissa import IPeopleFilter
from xmantissa import ixmantissa, webnav, webtheme, liveform, signup
from xmantissa.ixmantissa import IOrganizerPlugin, IContactType
from xmantissa.webapp import PrivateApplication
from xmantissa.tdbview import TabularDataView, ColumnViewBase
from xmantissa.scrolltable import ScrollingElement, UnsortableColumn
from xmantissa.fragmentutils import dictFillSlots
from xmantissa.webtheme import ThemedDocumentFactory


def makeThumbnail(inputFile, outputFile, thumbnailSize, outputFormat='jpeg'):
    """
    Make a thumbnail of the image stored at C{inputPath}, preserving its
    aspect ratio, and write the result to C{outputPath}.

    @param inputFile: The image file (or path to the file) to thumbnail.
    @type inputFile: C{file} or C{str}

    @param outputFile: The file (or path to the file) to write the thumbnail
    to.
    @type outputFile: C{file} or C{str}

    @param thumbnailSize: The maximum length (in pixels) of the longest side of
    the thumbnail image.
    @type thumbnailSize: C{int}

    @param outputFormat: The C{format} argument to pass to L{Image.save}.
    Defaults to I{jpeg}.
    @type format: C{str}
    """
    if Image is None:
        # throw the ImportError here
        import PIL
    image = Image.open(inputFile)
    # Resize needed?
    if thumbnailSize < max(image.size):
        # Convert bilevel and paletted images to grayscale and RGB respectively;
        # otherwise PIL silently switches to Image.NEAREST sampling.
        if image.mode == '1':
            image = image.convert('L')
        elif image.mode == 'P':
            image = image.convert('RGB')
        image.thumbnail((thumbnailSize, thumbnailSize), Image.ANTIALIAS)
    image.save(outputFile, outputFormat)



def _normalizeWhitespace(text):
    """
    Remove leading and trailing whitespace and collapse adjacent spaces into a
    single space.

    @type text: C{unicode}
    @rtype: C{unicode}
    """
    return u' '.join(text.split())



def _objectToName(o):
    """
    Derive a possibly-useful string type name from C{o}'s class.

    @rtype: C{str}
    """
    return nameToLabel(o.__class__.__name__).lstrip()



def _descriptiveIdentifier(contactType):
    """
    Get a descriptive identifier for C{contactType}, taking into account the
    fact that it might not have implemented the C{descriptiveIdentifier}
    method.

    @type contactType: L{IContactType} provider.

    @rtype: C{unicode}
    """
    descriptiveIdentifierMethod = getattr(
        contactType, 'descriptiveIdentifier', None)
    if descriptiveIdentifierMethod is not None:
        return descriptiveIdentifierMethod()
    warn(
        "IContactType now has the 'descriptiveIdentifier'"
        " method, %s did not implement it" % (contactType.__class__,),
        category=PendingDeprecationWarning)
    return _objectToName(contactType).decode('ascii')



def _organizerPluginName(plugin):
    """
    Get a name for C{plugin}, taking into account the fact that it might not
    have defined L{IOrganizerPlugin.name}.

    @type plugin: L{IOrganizerPlugin} provider.

    @rtype: C{unicode}
    """
    name = getattr(plugin, 'name', None)
    if name is not None:
        return name
    warn(
        "IOrganizerPlugin now has the 'name' attribute"
        " and %s does not define it" % (plugin.__class__,),
        category=PendingDeprecationWarning)
    return _objectToName(plugin).decode('ascii')



class ContactGroup(record('groupName')):
    """
    An object describing a group of L{IContactItem} implementors.

    @see IContactType.getContactGroup

    @ivar groupName: The name of the group.
    @type groupNode: C{unicode}
    """



class BaseContactType(object):
    """
    Base class for L{IContactType} implementations which provides useful
    default behavior.
    """
    allowMultipleContactItems = True

    def uniqueIdentifier(self):
        """
        Uniquely identify this contact type.
        """
        return qual(self.__class__).decode('ascii')


    def getParameters(self, contact):
        """
        Return a list of L{liveform.Parameter} objects to be used to create
        L{liveform.LiveForm}s suitable for creating or editing contact
        information of this type.

        Override this in a subclass.

        @param contact: A contact item, values from which should be used as
            defaults in the parameters.  C{None} if the parameters are for
            creating a new contact item.

        """
        raise NotImplementedError("%s did not implement getParameters" % (self,))


    def coerce(self, **kw):
        """
        Callback for input validation.

        @param **kw: Mapping of submitted parameter names to values.

        @rtype: C{dict}
        @return: Mapping of coerced parameter names to values.
        """
        return kw


    def getEditFormForPerson(self, person):
        """
        Return C{None}.
        """
        return None


    def getContactGroup(self, contactItem):
        """
        Return C{None}.
        """
        return None



class SimpleReadOnlyView(Element):
    """
    Simple read-only contact item view, suitable for returning from an
    implementation of L{IContactType.getReadOnlyView}.

    @ivar attribute: The contact item attribute which should be rendered.
    @type attribute: Axiom attribute (e.g. L{attributes.text})

    @ivar contactItem: The contact item.
    @type contactItem: L{item.Item}
    """
    docFactory = ThemedDocumentFactory(
        'person-contact-read-only-view', 'store')

    def __init__(self, attribute, contactItem):
        Element.__init__(self)
        self.attribute = attribute
        self.contactItem = contactItem
        self.store = contactItem.store


    def attributeName(self, req, tag):
        """
        Render the name of L{contactItem}'s class, e.g. "Email Address".
        """
        return nameToLabel(self.contactItem.__class__.__name__)
    renderer(attributeName)


    def attributeValue(self, req, tag):
        """
        Render the value of L{attribute} on L{contactItem}.
        """
        return self.attribute.__get__(self.contactItem)
    renderer(attributeValue)



class _PersonVIPStatus:
    """
    Contact item type used by L{VIPPersonContactType}.

    @param person: The person whose VIP status we're interested in.
    @type person: L{Person}
    """
    def __init__(self, person):
        self.person = person



class VIPPersonContactType(BaseContactType):
    """
    A contact type for controlling whether L{Person.vip} is set.
    """
    implements(IContactType)
    allowMultipleContactItems = False

    def getParameters(self, contactItem):
        """
        Return a list containing a single parameter suitable for changing the
        VIP status of a person.

        @type contactItem: L{_PersonVIPStatus}

        @rtype: C{list} of L{liveform.Parameter}
        """
        isVIP = False # default
        if contactItem is not None:
            isVIP = contactItem.person.vip
        return [liveform.Parameter(
            'vip', liveform.CHECKBOX_INPUT, bool, 'VIP', default=isVIP)]


    def getContactItems(self, person):
        """
        Return a list containing a L{_PersonVIPStatus} instance for C{person}.

        @type person: L{Person}

        @rtype: C{list} of L{_PersonVIPStatus}
        """
        return [_PersonVIPStatus(person)]


    def createContactItem(self, person, vip):
        """
        Set the VIP status of C{person} to C{vip}.

        @type person: L{Person}

        @type vip: C{bool}

        @rtype: L{_PersonVIPStatus}
        """
        person.vip = vip
        return _PersonVIPStatus(person)


    def editContactItem(self, contactItem, vip):
        """
        Change the VIP status of C{contactItem}'s person to C{vip}.

        @type contactItem: L{_PersonVIPStatus}

        @type vip: C{bool}

        @rtype: C{NoneType}
        """
        contactItem.person.vip = vip


    def getReadOnlyView(self, contactItem):
        """
        Return a fragment which will render as the empty string.
        L{PersonSummaryView} handles the rendering of VIP status in the
        read-only L{Person} view.

        @type contactItem: L{_PersonVIPStatus}

        @rtype: L{Element}
        """
        return Element(docFactory=stan(tags.invisible()))



class EmailContactType(BaseContactType):
    """
    Contact type plugin which allows a person to have an email address.

    @ivar store: The L{Store} the contact items will be created in.
    """
    implements(IContactType)

    def __init__(self, store):
        self.store = store


    def getParameters(self, emailAddress):
        """
        Return a C{list} of one L{LiveForm} parameter for editing an
        L{EmailAddress}.

        @type emailAddress: L{EmailAddress} or C{NoneType}
        @param emailAddress: If not C{None}, an existing contact item from
            which to get the email address default value.

        @rtype: C{list}
        @return: The parameters necessary for specifying an email address.
        """
        if emailAddress is not None:
            address = emailAddress.address
        else:
            address = u''
        return [
            liveform.Parameter('email', liveform.TEXT_INPUT,
                               _normalizeWhitespace, 'Email Address',
                               default=address)]


    def descriptiveIdentifier(self):
        """
        Return 'Email Address'
        """
        return u'Email Address'


    def _existing(self, email):
        """
        Return the existing L{EmailAddress} item with the given address, or
        C{None} if there isn't one.
        """
        return self.store.findUnique(
            EmailAddress,
            EmailAddress.address == email,
            default=None)


    def createContactItem(self, person, email):
        """
        Create a new L{EmailAddress} associated with the given person based on
        the given email address.

        @type person: L{Person}
        @param person: The person with whom to associate the new
            L{EmailAddress}.

        @type email: C{unicode}
        @param email: The value to use for the I{address} attribute of the
            newly created L{EmailAddress}.  If C{''}, no L{EmailAddress} will
            be created.

        @return: C{None}
        """
        if email:
            address = self._existing(email)
            if address is not None:
                raise ValueError('There is already a person with that email '
                                 'address (%s): ' % (address.person.name,))
            return EmailAddress(store=self.store,
                                address=email,
                                person=person)


    def getContactItems(self, person):
        """
        Return all L{EmailAddress} instances associated with the given person.

        @type person: L{Person}
        """
        return person.store.query(
            EmailAddress,
            EmailAddress.person == person)


    def editContactItem(self, contact, email):
        """
        Change the email address of the given L{EmailAddress} to that specified
        by C{email}.

        @type email: C{unicode}
        @param email: The new value to use for the I{address} attribute of the
            L{EmailAddress}.

        @return: C{None}
        """
        address = self._existing(email)
        if address is not None and address is not contact:
            raise ValueError('There is already a person with that email '
                             'address (%s): ' % (address.person.name,))
        contact.address = email


    def getReadOnlyView(self, contact):
        """
        Return a L{SimpleReadOnlyView} for the given L{EmailAddress}.
        """
        return SimpleReadOnlyView(EmailAddress.address, contact)



class PeopleBenefactor(item.Item):
    implements(ixmantissa.IBenefactor)
    endowed = attributes.integer(default=0)
    powerupNames = ["xmantissa.people.AddPerson"]



class Person(item.Item):
    """
    Person Per"son (p[~e]r"s'n; 277), n.

        1. A character or part, as in a play; a specific kind or manifestation
        of individual character, whether in real life, or in literary or
        dramatic representation; an assumed character. [Archaic] [1913 Webster]

    This is Mantissa's simulation of a person, which has attached contact
    information.  It is highly pluggable, mostly via the L{Organizer} object.

    Do not create this item directly, as functionality of L{IOrganizerPlugin}
    powerups will be broken if you do.  Instead, use L{Organizer.createPerson}.
    """

    typeName = 'mantissa_person'
    schemaVersion = 3

    organizer = attributes.reference(
        doc="""
        The L{Organizer} to which this Person belongs.
        """)

    name = attributes.text(
        doc="""
        This name of this person.
        """, caseSensitive=False)

    created = attributes.timestamp(defaultFactory=extime.Time)

    vip = boolean(
        doc="""
        Flag indicating this L{Person} is very important.
        """, default=False, allowNone=False)


    def getDisplayName(self):
        return self.name


    def getEmailAddresses(self):
        """
        Return an iterator of all email addresses associated with this person.

        @return: an iterator of unicode strings in RFC2822 address format.
        """
        return self.store.query(
            EmailAddress,
            EmailAddress.person == self).getColumn('address')

    def getEmailAddress(self):
        """
        Return the default email address associated with this person.

        Note: this is effectively random right now if a person has more than
        one address.  It's just the first address returned.  This should be
        fixed in a future version.

        @return: a unicode string in RFC2822 address format.
        """
        for a in self.getEmailAddresses():
            return a


    def getMugshot(self):
        """
        Return the L{Mugshot} associated with this L{Person}, or an unstored
        L{Mugshot} pointing at a placeholder mugshot image.
        """
        mugshot = self.store.findUnique(
            Mugshot, Mugshot.person == self, default=None)
        if mugshot is not None:
            return mugshot
        return Mugshot.placeholderForPerson(self)


    def registerExtract(self, extract, timestamp=None):
        """
        @param extract: some Item that implements L{inevow.IRenderer}
        """
        if timestamp is None:
            timestamp = extime.Time()

        return ExtractWrapper(store=self.store,
                              extract=extract,
                              timestamp=timestamp,
                              person=self)


    def getExtractWrappers(self, n):
        return self.store.query(ExtractWrapper,
                                ExtractWrapper.person == self,
                                sort=ExtractWrapper.timestamp.desc,
                                limit=n)


item.declareLegacyItem(
    Person.typeName,
    1,
    dict(organizer=attributes.reference(),
         name=attributes.text(caseSensitive=True),
         created=attributes.timestamp()))

registerAttributeCopyingUpgrader(Person, 1, 2)

item.declareLegacyItem(
    Person.typeName,
    2,
    dict(organizer=attributes.reference(),
         name=attributes.text(caseSensitive=True),
         created=attributes.timestamp(),
         vip=attributes.boolean(default=False, allowNone=False)))

registerAttributeCopyingUpgrader(Person, 2, 3)



class ExtractWrapper(item.Item):
    extract = attributes.reference(whenDeleted=attributes.reference.CASCADE)
    timestamp = attributes.timestamp(indexed=True)
    person = attributes.reference(reftype=Person,
                                  whenDeleted=attributes.reference.CASCADE)



def _stringifyKeys(d):
    """
    Return a copy of C{d} with C{str} keys.

    @type d: C{dict} with C{unicode} keys.
    @rtype: C{dict} with C{str} keys.
    """
    return dict((k.encode('ascii'), v)  for (k, v) in d.iteritems())



class AllPeopleFilter(object):
    """
    L{IPeopleFilter} which includes all L{Person} items from the given store
    in its query.
    """
    implements(IPeopleFilter)
    filterName = 'All'

    def getPeopleQueryComparison(self, store):
        """
        @see IPeopleFilter.getPeopleQueryComparison
        """
        return None



class VIPPeopleFilter(object):
    """
    L{IPeopleFilter} which includes all VIP L{Person} items from the given
    store in its query.
    """
    implements(IPeopleFilter)
    filterName = 'VIP'

    def getPeopleQueryComparison(self, store):
        """
        @see IPeopleFilter.getPeopleQueryComparison
        """
        return Person.vip == True



class TaggedPeopleFilter(record('filterName')):
    """
    L{IPeopleFilter} which includes in its query all L{Person} items to which
    a specific tag has been applied.
    """
    implements(IPeopleFilter)

    def getPeopleQueryComparison(self, store):
        """
        @see IPeopleFilter.getPeopleQueryComparison
        """
        return attributes.AND(
                Tag.object == Person.storeID,
                Tag.name == self.filterName)



class BaseOrganizerPlugin(object):
    """
    Base class for L{IOrganizerPlugin} implementations, which provides null
    implementations of the interface's callback/notification methods.
    """
    name = requiredAttribute('name')

    def personCreated(self, person):
        """
        Do nothing.

        @see IOrganizerPlugin.personCreated
        """


    def personNameChanged(self, person, name):
        """
        Do nothing.

        @see IOrganizerPlugin.personNameChanged
        """


    def contactItemCreated(self, item):
        """
        Do nothing.

        @see IOrganizerPlugin.contactItemCreated
        """


    def contactItemEdited(self, item):
        """
        Do nothing.

        @see IOrganizerPlugin.contactItemEdited
        """



class ContactInfoOrganizerPlugin(BaseOrganizerPlugin):
    """
    Trivial in-memory L{IOrganizerPlugin}.
    """
    implements(IOrganizerPlugin)

    name = u'Contact'

    def getContactTypes(self):
        """
        No contact types.

        @see IOrganizerPlugin.getContactTypes
        """
        return ()


    def getPeopleFilters(self):
        """
        No people filters.

        @see IOrganizerPlugin.getPeopleFilters
        """
        return ()


    def personalize(self, person):
        """
        Return a L{ReadOnlyContactInfoView} for C{person}.

        @see IOrganizerPlugin.personalize
        """
        return ReadOnlyContactInfoView(person)



class Organizer(item.Item):
    """
    Oversee the creation, location, destruction, and modification of
    people in a particular set (eg, the set of people you know).
    """
    implements(ixmantissa.INavigableElement)

    typeName = 'mantissa_people'
    schemaVersion = 3

    _webTranslator = dependsOn(PrivateApplication)

    storeOwnerPerson = attributes.reference(
        doc="A L{Person} representing the owner of the store this organizer lives in",
        reftype=Person,
        whenDeleted=attributes.reference.DISALLOW)


    powerupInterfaces = (ixmantissa.INavigableElement,)


    def __init__(self, *a, **k):
        super(Organizer, self).__init__(*a, **k)
        if 'storeOwnerPerson' not in k:
            self.storeOwnerPerson = self._makeStoreOwnerPerson()


    def _makeStoreOwnerPerson(self):
        """
        Make a L{Person} representing the owner of the store that this
        L{Organizer} is installed in.

        @rtype: L{Person}
        """
        if self.store is None:
            return None
        userInfo = self.store.findFirst(signup.UserInfo)
        name = u''
        if userInfo is not None:
            name = userInfo.realName
        account = self.store.findUnique(LoginAccount,
                                        LoginAccount.avatars == self.store, None)
        ownerPerson = self.createPerson(name)
        if account is not None:
            for method in (self.store.query(
                    LoginMethod,
                    attributes.AND(LoginMethod.account == account,
                                   LoginMethod.internal == False))):
                self.createContactItem(
                    EmailContactType(self.store),
                    ownerPerson, dict(
                        email=method.localpart + u'@' + method.domain))
        return ownerPerson


    def getOrganizerPlugins(self):
        """
        Return an iterator of the installed L{IOrganizerPlugin} powerups.
        """
        return (list(self.store.powerupsFor(IOrganizerPlugin))
            + [ContactInfoOrganizerPlugin()])


    def _gatherPluginMethods(self, methodName):
        """
        Walk through each L{IOrganizerPlugin} powerup, yielding the bound
        method if the powerup implements C{methodName}.  Upon encountering a
        plugin which fails to implement it, issue a
        L{PendingDeprecationWarning}.

        @param methodName: The name of a L{IOrganizerPlugin} method.
        @type methodName: C{str}

        @return: Iterable of methods.
        """
        for plugin in self.getOrganizerPlugins():
            implementation = getattr(plugin, methodName, None)
            if implementation is not None:
                yield implementation
            else:
                warn(
                    ('IOrganizerPlugin now has the %r method, %s'
                        ' did not implement it') % (
                            methodName, plugin.__class__),
                    category=PendingDeprecationWarning)


    def _checkContactType(self, contactType):
        """
        Possibly emit some warnings about C{contactType}'s implementation of
        L{IContactType}.

        @type contactType: L{IContactType} provider
        """
        if getattr(contactType, 'getEditFormForPerson', None) is None:
            warn(
                "IContactType now has the 'getEditFormForPerson'"
                " method, but %s did not implement it." % (
                    contactType.__class__,),
                category=PendingDeprecationWarning)

        if getattr(contactType, 'getEditorialForm', None) is not None:
            warn(
                "The IContactType %s defines the 'getEditorialForm'"
                " method, which is deprecated.  'getEditFormForPerson'"
                " does something vaguely similar." % (contactType.__class__,),
                category=DeprecationWarning)


    def getContactTypes(self):
        """
        Return an iterator of L{IContactType} providers available to this
        organizer's store.
        """
        yield VIPPersonContactType()
        yield EmailContactType(self.store)
        yield PostalContactType()
        yield PhoneNumberContactType()
        yield NotesContactType()
        for getContactTypes in self._gatherPluginMethods('getContactTypes'):
            for contactType in getContactTypes():
                self._checkContactType(contactType)
                yield contactType


    def getPeopleFilters(self):
        """
        Return an iterator of L{IPeopleFilter} providers available to this
        organizer's store.
        """
        yield AllPeopleFilter()
        yield VIPPeopleFilter()
        for getPeopleFilters in self._gatherPluginMethods('getPeopleFilters'):
            for peopleFilter in getPeopleFilters():
                yield peopleFilter
        for tag in sorted(self.getPeopleTags()):
            yield TaggedPeopleFilter(tag)


    def getPeopleTags(self):
        """
        Return a sequence of tags which have been applied to L{Person} items.

        @rtype: C{set}
        """
        query = self.store.query(
            Tag, Tag.object == Person.storeID)
        return set(query.getColumn('name').distinct())


    def groupReadOnlyViews(self, person):
        """
        Collect all contact items from the available contact types for the
        given person, organize them by contact group, and turn them into
        read-only views.

        @type person: L{Person}
        @param person: The person whose contact items we're interested in.

        @return: A mapping of of L{ContactGroup} names to the read-only views
        of their member contact items, with C{None} being the key for
        groupless contact items.
        @rtype: C{dict} of C{str}
        """
        # this is a slightly awkward, specific API, but at the time of
        # writing, read-only views are the thing that the only caller cares
        # about.  we need the contact type to get a read-only view for a
        # contact item.  there is no way to get from a contact item to a
        # contact type, so this method can't be "groupContactItems" (which
        # seems to make more sense), unless it returned some weird data
        # structure which managed to associate contact items and contact
        # types.
        grouped = {}
        for contactType in self.getContactTypes():
            for contactItem in contactType.getContactItems(person):
                contactGroup = contactType.getContactGroup(contactItem)
                if contactGroup is not None:
                    contactGroup = contactGroup.groupName
                if contactGroup not in grouped:
                    grouped[contactGroup] = []
                grouped[contactGroup].append(
                    contactType.getReadOnlyView(contactItem))
        return grouped


    def getContactCreationParameters(self):
        """
        Yield a L{Parameter} for each L{IContactType} known.

        Each yielded object can be used with a L{LiveForm} to create a new
        instance of a particular L{IContactType}.
        """
        for contactType in self.getContactTypes():
            if contactType.allowMultipleContactItems:
                descriptiveIdentifier = _descriptiveIdentifier(contactType)
                yield liveform.ListChangeParameter(
                    contactType.uniqueIdentifier(),
                    contactType.getParameters(None),
                    defaults=[],
                    modelObjects=[],
                    modelObjectDescription=descriptiveIdentifier)
            else:
                yield liveform.FormParameter(
                    contactType.uniqueIdentifier(),
                    liveform.LiveForm(
                        lambda **k: k,
                        contactType.getParameters(None)))


    def _parametersToDefaults(self, parameters):
        """
        Extract the defaults from C{parameters}, constructing a dictionary
        mapping parameter names to default values, suitable for passing to
        L{ListChangeParameter}.

        @type parameters: C{list} of L{liveform.Parameter} or
        L{liveform.ChoiceParameter}.

        @rtype: C{dict}
        """
        defaults = {}
        for p in parameters:
            if isinstance(p, liveform.ChoiceParameter):
                selected = []
                for choice in p.choices:
                    if choice.selected:
                        selected.append(choice.value)
                defaults[p.name] = selected
            else:
                defaults[p.name] = p.default
        return defaults


    def toContactEditorialParameter(self, contactType, person):
        """
        Convert the given contact type into a L{liveform.LiveForm} parameter.

        @type contactType: L{IContactType} provider.

        @type person: L{Person}

        @rtype: L{liveform.Parameter} or similar.
        """
        contactItems = list(contactType.getContactItems(person))
        if contactType.allowMultipleContactItems:
            defaults = []
            modelObjects = []
            for contactItem in contactItems:
                defaultedParameters = contactType.getParameters(contactItem)
                if defaultedParameters is None:
                    continue
                defaults.append(self._parametersToDefaults(
                    defaultedParameters))
                modelObjects.append(contactItem)
            descriptiveIdentifier = _descriptiveIdentifier(contactType)
            return liveform.ListChangeParameter(
                contactType.uniqueIdentifier(),
                contactType.getParameters(None),
                defaults=defaults,
                modelObjects=modelObjects,
                modelObjectDescription=descriptiveIdentifier)
        (contactItem,) = contactItems
        return liveform.FormParameter(
            contactType.uniqueIdentifier(),
            liveform.LiveForm(
                lambda **k: k,
                contactType.getParameters(contactItem)))


    def getContactEditorialParameters(self, person):
        """
        Yield L{LiveForm} parameters to edit each contact item of each contact
        type for the given person.

        @type person: L{Person}
        @return: An iterable of two-tuples.  The first element of each tuple
            is an L{IContactType} provider.  The third element of each tuple
            is the L{LiveForm} parameter object for that contact item.
        """
        for contactType in self.getContactTypes():
            yield (
                contactType,
                self.toContactEditorialParameter(contactType, person))


    _NO_VIP = object()

    def createPerson(self, nickname, vip=_NO_VIP):
        """
        Create a new L{Person} with the given name in this organizer.

        @type nickname: C{unicode}
        @param nickname: The value for the new person's C{name} attribute.

        @type vip: C{bool}
        @param vip: Value to set the created person's C{vip} attribute to
        (deprecated).

        @rtype: L{Person}
        """
        for person in (self.store.query(
                Person, attributes.AND(
                    Person.name == nickname,
                    Person.organizer == self))):
            raise ValueError("Person with name %r exists already." % (nickname,))
        person = Person(
            store=self.store,
            created=extime.Time(),
            organizer=self,
            name=nickname)

        if vip is not self._NO_VIP:
            warn(
                "Usage of Organizer.createPerson's 'vip' parameter"
                " is deprecated",
                category=DeprecationWarning)
            person.vip = vip

        self._callOnOrganizerPlugins('personCreated', person)
        return person


    def createContactItem(self, contactType, person, contactInfo):
        """
        Create a new contact item for the given person with the given contact
        type.  Broadcast a creation to all L{IOrganizerPlugin} powerups.

        @type contactType: L{IContactType}
        @param contactType: The contact type which will be used to create the
            contact item.

        @type person: L{Person}
        @param person: The person with whom the contact item will be
            associated.

        @type contactInfo: C{dict}
        @param contactInfo: The contact information to use to create the
            contact item.

        @return: The contact item, as created by the given contact type.
        """
        contactItem = contactType.createContactItem(
            person, **_stringifyKeys(contactInfo))
        if contactItem is not None:
            self._callOnOrganizerPlugins('contactItemCreated', contactItem)
        return contactItem


    def editContactItem(self, contactType, contactItem, contactInfo):
        """
        Edit the given contact item with the given contact type.  Broadcast
        the edit to all L{IOrganizerPlugin} powerups.

        @type contactType: L{IContactType}
        @param contactType: The contact type which will be used to edit the
            contact item.

        @param contactItem: The contact item to edit.

        @type contactInfo: C{dict}
        @param contactInfo: The contact information to use to edit the
            contact item.

        @return: C{None}
        """
        contactType.editContactItem(
            contactItem, **_stringifyKeys(contactInfo))
        self._callOnOrganizerPlugins('contactItemEdited', contactItem)


    def _callOnOrganizerPlugins(self, methodName, *args):
        """
        Call a method on all L{IOrganizerPlugin} powerups on C{self.store}, or
        emit a deprecation warning for each one which does not implement that
        method.
        """
        for observer in self.getOrganizerPlugins():
            method = getattr(observer, methodName, None)
            if method is not None:
                method(*args)
            else:
                warn(
                    "IOrganizerPlugin now has the %s method, %s "
                    "did not implement it" % (methodName, observer.__class__,),
                    category=PendingDeprecationWarning)


    def editPerson(self, person, nickname, edits):
        """
        Change the name and contact information associated with the given
        L{Person}.

        @type person: L{Person}
        @param person: The person which will be modified.

        @type nickname: C{unicode}
        @param nickname: The new value for L{Person.name}

        @type edits: C{list}
        @param edits: list of tuples of L{IContactType} providers and
        corresponding L{ListChanges} objects or dictionaries of parameter
        values.
        """
        for existing in self.store.query(Person, Person.name == nickname):
            if existing is person:
                continue
            raise ValueError(
                "A person with the name %r exists already." % (nickname,))
        oldname = person.name
        person.name = nickname
        self._callOnOrganizerPlugins('personNameChanged', person, oldname)
        for contactType, submission in edits:
            if contactType.allowMultipleContactItems:
                for edit in submission.edit:
                    self.editContactItem(
                        contactType, edit.object, edit.values)
                for create in submission.create:
                    create.setter(
                        self.createContactItem(
                            contactType, person, create.values))
                for delete in submission.delete:
                    delete.deleteFromStore()
            else:
                (contactItem,) = contactType.getContactItems(person)
                self.editContactItem(
                    contactType, contactItem, submission)


    def deletePerson(self, person):
        """
        Delete the given person from the store.
        """
        person.deleteFromStore()


    def personByName(self, name):
        """
        Retrieve the L{Person} item for the given Q2Q address,
        creating it first if necessary.

        @type name: C{unicode}
        """
        return self.store.findOrCreate(Person, organizer=self, name=name)


    def personByEmailAddress(self, address):
        """
        Retrieve the L{Person} item for the given email address
        (or return None if no such person exists)

        @type name: C{unicode}
        """
        email = self.store.findUnique(EmailAddress,
                                      EmailAddress.address == address,
                                      default=None)
        if email is not None:
            return email.person


    def linkToPerson(self, person):
        """
        @param person: L{Person} instance
        @return: string url at which C{person} will be rendered
        """
        return self._webTranslator.linkTo(person.storeID)


    def urlForViewState(self, person, viewState):
        """
        Return a url for L{OrganizerFragment} which will display C{person} in
        state C{viewState}.

        @type person: L{Person}
        @type viewState: L{ORGANIZER_VIEW_STATES} constant.

        @rtype: L{url.URL}
        """
        # ideally there would be a more general mechanism for encoding state
        # like this in a url, rather than ad-hoc query arguments for each
        # fragment which needs to do it.
        organizerURL = self._webTranslator.linkTo(self.storeID)
        return url.URL(
            netloc='', scheme='',
            pathsegs=organizerURL.split('/')[1:],
            querysegs=(('initial-person', person.name),
                       ('initial-state', viewState)))


    # INavigableElement
    def getTabs(self):
        """
        Implement L{INavigableElement.getTabs} to return a single tab,
        'People', that points to this item.
        """
        return [webnav.Tab('People', self.storeID, 0.5, authoritative=True)]



def organizer1to2(old):
    o = old.upgradeVersion(old.typeName, 1, 2)
    o._webTranslator = old.store.findOrCreate(PrivateApplication)
    return o

registerUpgrader(organizer1to2, Organizer.typeName, 1, 2)



item.declareLegacyItem(Organizer.typeName, 2,
    dict(_webTranslator=attributes.reference()))



registerAttributeCopyingUpgrader(Organizer, 2, 3)



class VIPColumn(UnsortableColumn):
    def getType(self):
        return 'boolean'



class MugshotURLColumn(record('organizer attributeID')):
    """
    L{ixmantissa.IColumn} provider which extracts the URL of a L{Person}'s
    mugshot.

    @type organizer: L{Organizer}
    """
    implements(ixmantissa.IColumn)

    def extractValue(self, model, item):
        """
        Figure out the URL of C{item}'s mugshot.

        @type item: L{Person}

        @rtype: C{unicode}
        """
        return self.organizer.linkToPerson(item) + u'/mugshot/smaller'


    def sortAttribute(self):
        """
        Return C{None}.  Unsortable.
        """
        return None


    def getType(self):
        """
        Return C{text}
        """
        return 'text'


    def toComparableValue(self, value):
        """
        This shouldn't be called.

        @raise L{NotImplementedError}: Always.
        """
        raise NotImplementedError(
            '%r does not implement toComparableValue: it is unsortable' %
            (self.__class__,))



class PersonScrollingFragment(ScrollingElement):
    """
    Scrolling element which displays L{Person} objects and allows actions to
    be taken on them.

    @type organizer: L{Organizer}
    """
    jsClass = u'Mantissa.People.PersonScroller'

    def __init__(self, organizer, baseConstraint, defaultSortColumn,
            webTranslator):
        self._originalBaseConstraint = baseConstraint
        ScrollingElement.__init__(
            self,
            organizer.store,
            Person,
            baseConstraint,
            [MugshotURLColumn(organizer, 'mugshotURL'),
             VIPColumn(Person.vip, 'vip'),
             Person.name],
            defaultSortColumn=defaultSortColumn,
            webTranslator=webTranslator)
        self.organizer = organizer
        self.filters = dict((filter.filterName, filter)
                for filter in organizer.getPeopleFilters())


    def getInitialArguments(self):
        """
        Include L{organizer}'s C{storeOwnerPerson}'s name.
        """
        return (ScrollingElement.getInitialArguments(self)
                    + [self.organizer.storeOwnerPerson.name])


    def filterByFilter(self, filterName):
        """
        Swap L{baseConstraint} with the result of calling
        L{IPeopleFilter.getPeopleQueryComparison} on the named filter.

        @type filterName: C{unicode}
        """
        filter = self.filters[filterName]
        self.baseConstraint = filter.getPeopleQueryComparison(self.store)
    expose(filterByFilter)



class PersonSummaryView(Element):
    """
    Fragment which renders a business card-like summary of a L{Person}: their
    mugshot, vip status, and name.

    @type person: L{Person}
    @ivar person: The person to summarize.
    """
    docFactory = ThemedDocumentFactory('person-summary', 'store')

    def __init__(self, person):
        self.person = person
        self.organizer = person.organizer
        self.store = person.store


    def mugshotURL(self, req, tag):
        """
        Render the URL of L{person}'s mugshot, or the URL of a placeholder
        mugshot if they don't have one set.
        """
        return self.organizer.linkToPerson(self.person) + '/mugshot/smaller'
    renderer(mugshotURL)


    def personName(self, req, tag):
        """
        Render the display name of L{person}.
        """
        return self.person.getDisplayName()
    renderer(personName)


    def vipStatus(self, req, tag):
        """
        Return C{tag} if L{person} is a VIP, otherwise return the empty
        string.
        """
        if self.person.vip:
            return tag
        return ''
    renderer(vipStatus)



class ReadOnlyContactInfoView(Element):
    """
    Fragment which renders a read-only version of a person's contact
    information.

    @ivar person: A person.
    @type person: L{Person}
    """
    docFactory = ThemedDocumentFactory(
        'person-read-only-contact-info', 'store')

    def __init__(self, person):
        self.person = person
        self.organizer = person.organizer
        self.store = person.store
        Element.__init__(self)


    def personSummary(self, request, tag):
        """
        Render a L{PersonSummaryView} for L{person}.
        """
        return PersonSummaryView(self.person)
    renderer(personSummary)


    def contactInfo(self, request, tag):
        """
        Render the result of calling L{IContactType.getReadOnlyView} on the
        corresponding L{IContactType} for each piece of contact info
        associated with L{person}.  Arrange the result by group, using
        C{tag}'s I{contact-group} pattern. Groupless contact items will have
        their views yielded directly.

        The I{contact-group} pattern appears once for each distinct
        L{ContactGroup}, with the following slots filled:
          I{name} - The group's C{groupName}.
          I{views} - A sequence of read-only views belonging to the group.
        """
        groupPattern = inevow.IQ(tag).patternGenerator('contact-group')
        groupedViews = self.organizer.groupReadOnlyViews(self.person)
        for (groupName, views) in groupedViews.iteritems():
            if groupName is None:
                yield views
            else:
                yield groupPattern().fillSlots(
                    'name', groupName).fillSlots(
                    'views', views)
    renderer(contactInfo)



class ORGANIZER_VIEW_STATES:
    """
    Some constants describing possible initial states of L{OrganizerFragment}.

    @ivar EDIT: The state which involves editing a person.

    @ivar ALL_STATES: A sequence of all valid initial states.
    """
    EDIT = u'edit'

    ALL_STATES = (EDIT,)



class _ElementWrapper(LiveElement):
    """
    L{LiveElement} which wraps & renders an L{Element}.

    @type wrapped: L{Element}
    """
    docFactory = stan(
        tags.div(render=tags.directive('liveElement'))[
            tags.directive('element')])

    def __init__(self, wrapped):
        LiveElement.__init__(self)
        self.wrapped = wrapped


    def element(self, request, tag):
        """
        Render L{wrapped}.
        """
        return self.wrapped
    renderer(element)



class PersonPluginView(LiveElement):
    """
    Element which renders UI for selecting between the views of available
    person plugins.  A tab will be rendered for each L{IOrganizerPlugin} in
    L{plugins}, with the corresponding personalization being rendered when a
    tab is selected.

    @ivar plugins: Sequence of L{IOrganizerPlugin} providers.
    @type plugins: C{list}

    @ivar person: The person we're interested in.
    @type person: L{Person}
    """
    docFactory = ThemedDocumentFactory('person-plugins', 'store')
    jsClass = u'Mantissa.People.PersonPluginView'

    def __init__(self, plugins, person):
        LiveElement.__init__(self)
        self.plugins = plugins
        self.person = person
        self.store = person.store


    def pluginTabbedPane(self, request, tag):
        """
        Render a L{tabbedPane.TabbedPaneFragment} with an entry for each item
        in L{plugins}.
        """
        iq = inevow.IQ(tag)
        tabNames = [
            _organizerPluginName(p).encode('ascii') # gunk
                for p in self.plugins]
        child = tabbedPane.TabbedPaneFragment(
            zip(tabNames,
                ([self.getPluginWidget(tabNames[0])]
                    + [iq.onePattern('pane-body') for _ in tabNames[1:]])))
        child.jsClass = u'Mantissa.People.PluginTabbedPane'
        child.setFragmentParent(self)
        return child
    renderer(pluginTabbedPane)


    def _toLiveElement(self, element):
        """
        Wrap the given element in a L{LiveElement} if it is not already one.

        @rtype: L{LiveElement}
        """
        if isinstance(element, LiveElement):
            return element
        return _ElementWrapper(element)


    def getPluginWidget(self, pluginName):
        """
        Return the named plugin's view.

        @type pluginName: C{unicode}
        @param pluginName: The name of the plugin.

        @rtype: L{LiveElement}
        """
        # this will always pick the first plugin with pluginName if there is
        # more than one.  don't do that.
        for plugin in self.plugins:
            if _organizerPluginName(plugin) == pluginName:
                view = self._toLiveElement(
                    plugin.personalize(self.person))
                view.setFragmentParent(self)
                return view
    expose(getPluginWidget)



class OrganizerFragment(LiveElement):
    """
    Address book view.  The initial state of this fragment can be extracted
    from the query parameters in its url, if present.  The two parameters it
    looks for are: I{initial-person} (the name of the L{Person} to select
    initially in the scrolltable) and I{initial-state} (a
    L{ORGANIZER_VIEW_STATES} constant describing what to do with the person).
    Both query arguments must be present if either is.

    @type organizer: L{Organizer}
    @ivar organizer: The organizer for which this is a view.

    @ivar initialPerson: The person to load initially.  Defaults to C{None}.
    @type initialPerson: L{Person} or C{NoneType}

    @ivar initialState: The initial state of the organizer view.  Defaults to
    C{None}.
    @type initialState: L{ORGANIZER_VIEW_STATES} or C{NoneType}
    """
    docFactory = ThemedDocumentFactory('people-organizer', 'store')
    fragmentName = None
    live = 'athena'
    title = 'People'
    jsClass = u'Mantissa.People.Organizer'

    def __init__(self, organizer, initialPerson=None, initialState=None):
        LiveElement.__init__(self)
        self.organizer = organizer
        self.initialPerson = initialPerson
        self.initialState = initialState

        self.store = organizer.store
        self.wt = organizer._webTranslator


    def head(self):
        """
        Do nothing.
        """


    def beforeRender(self, ctx):
        """
        Implement this hook to initialize the L{initialPerson} and
        L{initialState} slots with information from the request url's query
        args.
        """
        # see the comment in Organizer.urlForViewState which suggests an
        # alternate implementation of this kind of functionality.
        request = inevow.IRequest(ctx)
        if not set(['initial-person', 'initial-state']).issubset( # <=
            set(request.args)):
            return
        initialPersonName = request.args['initial-person'][0].decode('utf-8')
        initialPerson = self.store.findFirst(
            Person, Person.name == initialPersonName)
        if initialPerson is None:
            return
        initialState = request.args['initial-state'][0].decode('utf-8')
        if initialState not in ORGANIZER_VIEW_STATES.ALL_STATES:
            return
        self.initialPerson = initialPerson
        self.initialState = initialState


    def getInitialArguments(self):
        """
        Include L{organizer}'s C{storeOwnerPerson}'s name, and the name of
        L{initialPerson} and the value of L{initialState}, if they are set.
        """
        initialArguments = (self.organizer.storeOwnerPerson.name,)
        if self.initialPerson is not None:
            initialArguments += (self.initialPerson.name, self.initialState)
        return initialArguments


    def getAddPerson(self):
        """
        Return an L{AddPersonFragment} which is a child of this fragment and
        which will add a person to C{self.organizer}.
        """
        fragment = AddPersonFragment(self.organizer)
        fragment.setFragmentParent(self)
        return fragment
    expose(getAddPerson)


    def getImportPeople(self):
        """
        Return an L{ImportPeopleWidget} which is a child of this fragment and
        which will add people to C{self.organizer}.
        """
        fragment = ImportPeopleWidget(self.organizer)
        fragment.setFragmentParent(self)
        return fragment
    expose(getImportPeople)


    def getEditPerson(self, name):
        """
        Get an L{EditPersonView} for editing the person named C{name}.

        @param name: A person name.
        @type name: C{unicode}

        @rtype: L{EditPersonView}
        """
        view = EditPersonView(self.organizer.personByName(name))
        view.setFragmentParent(self)
        return view
    expose(getEditPerson)


    def deletePerson(self, name):
        """
        Delete the person named C{name}

        @param name: A person name.
        @type name: C{unicode}
        """
        self.organizer.deletePerson(self.organizer.personByName(name))
    expose(deletePerson)


    def peopleTable(self, request, tag):
        """
        Return a L{PersonScrollingFragment} which will display the L{Person}
        items in the wrapped organizer.
        """
        f = PersonScrollingFragment(
            self.organizer, None, Person.name, self.wt)
        f.setFragmentParent(self)
        f.docFactory = webtheme.getLoader(f.fragmentName)
        return f
    renderer(peopleTable)


    def peopleFilters(self, request, tag):
        """
        Return an instance of C{tag}'s I{filter} pattern for each filter we
        get from L{Organizer.getPeopleFilters}, filling the I{name} slot with
        the filter's name.  The first filter will be rendered using the
        I{selected-filter} pattern.
        """
        filters = iter(self.organizer.getPeopleFilters())
        # at some point we might actually want to look at what filter is
        # yielded first, and filter the person list accordingly.  we're just
        # going to assume it's the "All" filter, and leave the person list
        # untouched for now.
        yield tag.onePattern('selected-filter').fillSlots(
            'name', filters.next().filterName)
        pattern = tag.patternGenerator('filter')
        for filter in filters:
            yield pattern.fillSlots('name', filter.filterName)
    renderer(peopleFilters)


    def getPersonPluginWidget(self, name):
        """
        Return the L{PersonPluginView} for the named person.

        @type name: C{unicode}
        @param name: A value which corresponds to the I{name} attribute of an
        extant L{Person}.

        @rtype: L{PersonPluginView}
        """
        fragment = PersonPluginView(
            self.organizer.getOrganizerPlugins(),
            self.organizer.personByName(name))
        fragment.setFragmentParent(self)
        return fragment
    expose(getPersonPluginWidget)

components.registerAdapter(OrganizerFragment, Organizer, ixmantissa.INavigableFragment)



class EditPersonView(LiveElement):
    """
    Render a view for editing the contact information for a L{Person}.

    @ivar person: L{Person} which can be edited.

    @ivar contactTypes: A mapping from parameter names to the L{IContactTypes}
        whose items the parameters are editing.
    """
    docFactory = ThemedDocumentFactory('edit-person', 'store')
    fragmentName = 'edit-person'
    jsClass = u'Mantissa.People.EditPerson'

    def __init__(self, person):
        athena.LiveElement.__init__(self)
        self.person = person
        self.store = person.store
        self.organizer = person.organizer
        self.contactTypes = {}


    def editContactItems(self, nickname, **edits):
        """
        Update the information on the contact items associated with the wrapped
        L{Person}.

        @type nickname: C{unicode}
        @param nickname: New value to use for the I{name} attribute of the
            L{Person}.

        @param **edits: mapping from contact type identifiers to
            ListChanges instances.
        """
        submissions = []
        for paramName, submission in edits.iteritems():
            contactType = self.contactTypes[paramName]
            submissions.append((contactType, submission))
        self.person.store.transact(
            self.organizer.editPerson,
            self.person, nickname, submissions)


    def makeEditorialLiveForms(self):
        """
        Make some L{liveform.LiveForm} instances for editing the contact
        information of the wrapped L{Person}.
        """
        parameters = [
            liveform.Parameter(
                'nickname', liveform.TEXT_INPUT,
                _normalizeWhitespace, 'Name',
                default=self.person.name)]
        separateForms = []
        for contactType in self.organizer.getContactTypes():
            if getattr(contactType, 'getEditFormForPerson', None):
                editForm = contactType.getEditFormForPerson(self.person)
                if editForm is not None:
                    editForm.setFragmentParent(self)
                    separateForms.append(editForm)
                    continue
            param = self.organizer.toContactEditorialParameter(
                contactType, self.person)
            parameters.append(param)
            self.contactTypes[param.name] = contactType
        form = liveform.LiveForm(
            self.editContactItems, parameters, u'Save')
        form.compact()
        form.jsClass = u'Mantissa.People.EditPersonForm'
        form.setFragmentParent(self)
        return [form] + separateForms


    def mugshotFormURL(self, request, tag):
        """
        Render a URL for L{MugshotUploadForm}.
        """
        return self.organizer.linkToPerson(self.person) + '/mugshotUploadForm'
    renderer(mugshotFormURL)


    def editorialContactForms(self, request, tag):
        """
        Put the result of L{makeEditorialLiveForms} in C{tag}.
        """
        return tag[self.makeEditorialLiveForms()]
    renderer(editorialContactForms)



class RealName(item.Item):
    """
    This is a legacy item left over from a previous schema.  Do not create it.
    """
    typeName = 'mantissa_organizer_addressbook_realname'
    schemaVersion = 2

    empty = attributes.reference()


item.declareLegacyItem(
    RealName.typeName, 1,
    dict(person=attributes.reference(
            doc="""
            allowNone=False,
            whenDeleted=attributes.reference.CASCADE,
            reftype=Person
            """),
         first=attributes.text(),
         last=attributes.text(indexed=True)))

registerDeletionUpgrader(RealName, 1, 2)



class EmailAddress(item.Item):
    """
    An email address contact info item associated with a L{Person}.

    Do not create this item directly, as functionality of L{IOrganizerPlugin}
    powerups will be broken if you do.  Instead, use
    L{Organizer.createContactItem} with L{EmailContactType}.
    """
    typeName = 'mantissa_organizer_addressbook_emailaddress'
    schemaVersion = 3

    address = attributes.text(allowNone=False)
    person = attributes.reference(
        allowNone=False,
        whenDeleted=attributes.reference.CASCADE,
        reftype=Person)
    label = attributes.text(
        """
        This is a label for the role of the email address, usually something like
        "home", "work", "school".
        """,
        allowNone=False,
        default=u'')

def emailAddress1to2(old):
    return old.upgradeVersion('mantissa_organizer_addressbook_emailaddress',
                              1, 2,
                              address=old.address,
                              person=old.person)

registerUpgrader(emailAddress1to2,
                 'mantissa_organizer_addressbook_emailaddress',
                 1, 2)

item.declareLegacyItem(EmailAddress.typeName, 2, dict(
                  address = attributes.text(allowNone=False),
                  person = attributes.reference(allowNone=False)))

registerAttributeCopyingUpgrader(EmailAddress, 2, 3)


class PhoneNumber(item.Item):
    """
    A contact information item representing a L{Person}'s phone number.

    Do not create this item directly, as functionality of L{IOrganizerPlugin}
    powerups will be broken if you do.  Instead, use
    L{Organizer.createContactItem} with L{PhoneNumberContactType}.
    """
    typeName = 'mantissa_organizer_addressbook_phonenumber'
    schemaVersion = 3

    number = attributes.text(allowNone=False)
    person = attributes.reference(allowNone=False)
    label = attributes.text(
        """
        This is a label for the role of the phone number.
        """,
        allowNone=False,
        default=u'',)


    class LABELS:
        """
        Constants to use for the value of the L{label} attribute, describing
        the type of the telephone number.

        @ivar HOME: This is a home phone number.
        @type HOME: C{unicode}

        @ivar WORK: This is a work phone number.
        @type WORK: C{unicode}

        @ivar MOBILE: This is a mobile phone number.
        @type MOBILE: C{unicode}

        @ivar HOME_FAX: This is the 80's and someone has a fax machine in
        their house.
        @type HOME_FAX: C{unicode}

        @ivar WORK_FAX: This is the 80's and someone has a fax machine in
        their office.
        @type WORK_FAX: C{unicode}

        @ivar PAGER: This is the 80's and L{person} is a drug dealer.
        @type PAGER: C{unicode}

        @ivar ALL_LABELS: A sequence of all of the label constants.
        @type ALL_LABELS: C{list}
        """
        HOME = u'Home'
        WORK = u'Work'
        MOBILE = u'Mobile'
        HOME_FAX = u'Home Fax'
        WORK_FAX = u'Work Fax'
        PAGER = u'Pager'


        ALL_LABELS = [HOME, WORK, MOBILE, HOME_FAX, WORK_FAX, PAGER]

def phoneNumber1to2(old):
    return old.upgradeVersion('mantissa_organizer_addressbook_phonenumber',
                              1, 2,
                              number=old.number,
                              person=old.person)

item.declareLegacyItem(PhoneNumber.typeName, 2, dict(
                  number = attributes.text(allowNone=False),
                  person = attributes.reference(allowNone=False)))

registerUpgrader(phoneNumber1to2,
                 'mantissa_organizer_addressbook_phonenumber',
                 1, 2)

registerAttributeCopyingUpgrader(PhoneNumber, 2, 3)



class PhoneNumberContactType(BaseContactType):
    """
    Contact type plugin which allows telephone numbers to be associated with
    people.
    """
    implements(IContactType)

    def getParameters(self, phoneNumber):
        """
        Return a C{list} of two liveform parameters, one for editing
        C{phoneNumber}'s I{number} attribute, and one for editing its I{label}
        attribute.

        @type phoneNumber: L{PhoneNumber} or C{NoneType}
        @param phoneNumber: If not C{None}, an existing contact item from
        which to get the parameter's default values.

        @rtype: C{list}
        """
        defaultNumber = u''
        defaultLabel = PhoneNumber.LABELS.HOME
        if phoneNumber is not None:
            defaultNumber = phoneNumber.number
            defaultLabel = phoneNumber.label
        labelChoiceParameter = liveform.ChoiceParameter(
            'label',
            [liveform.Option(label, label, label == defaultLabel)
                for label in PhoneNumber.LABELS.ALL_LABELS],
            'Number Type')
        return [
            labelChoiceParameter,
            liveform.Parameter(
                'number',
                liveform.TEXT_INPUT,
                unicode,
                'Phone Number',
                default=defaultNumber)]


    def descriptiveIdentifier(self):
        """
        Return 'Phone Number'
        """
        return u'Phone Number'


    def createContactItem(self, person, label, number):
        """
        Create a L{PhoneNumber} item for C{number}, associated with C{person}.

        @type person: L{Person}

        @param label: The value to use for the I{label} attribute of the new
        L{PhoneNumber} item.
        @type label: C{unicode}

        @param number: The value to use for the I{number} attribute of the new
        L{PhoneNumber} item.  If C{''}, no item will be created.
        @type number: C{unicode}

        @rtype: L{PhoneNumber} or C{NoneType}
        """
        if number:
            return PhoneNumber(
                store=person.store, person=person, label=label, number=number)


    def editContactItem(self, contact, label, number):
        """
        Change the I{number} attribute of C{contact} to C{number}, and the
        I{label} attribute to C{label}.

        @type contact: L{PhoneNumber}

        @type label: C{unicode}

        @type number: C{unicode}

        @return: C{None}
        """
        contact.label = label
        contact.number = number


    def getContactItems(self, person):
        """
        Return an iterable of L{PhoneNumber} items that are associated with
        C{person}.

        @type person: L{Person}
        """
        return person.store.query(
            PhoneNumber, PhoneNumber.person == person)


    def getReadOnlyView(self, contact):
        """
        Return a L{ReadOnlyPhoneNumberView} for the given L{PhoneNumber}.
        """
        return ReadOnlyPhoneNumberView(contact)



class ReadOnlyPhoneNumberView(Element):
    """
    Read-only view for L{PhoneNumber}.

    @type phoneNumber: L{PhoneNumber}
    """
    docFactory = ThemedDocumentFactory(
        'person-contact-read-only-phone-number-view', 'store')

    def __init__(self, phoneNumber):
        self.phoneNumber = phoneNumber
        self.store = phoneNumber.store


    def number(self, request, tag):
        """
        Add the value of L{phoneNumber}'s I{number} attribute to C{tag}.
        """
        return tag[self.phoneNumber.number]
    renderer(number)


    def label(self, request, tag):
        """
        Add the value of L{phoneNumber}'s I{label} attribute to C{tag}.
        """
        return tag[self.phoneNumber.label]
    renderer(label)



class PostalAddress(item.Item):
    typeName = 'mantissa_organizer_addressbook_postaladdress'

    address = attributes.text(allowNone=False)
    person = attributes.reference(
        allowNone=False,
        whenDeleted=attributes.reference.CASCADE,
        reftype=Person)



class PostalContactType(BaseContactType):
    """
    Contact type plugin which allows a person to have a snail-mail address.
    """
    implements(IContactType)

    def getParameters(self, postalAddress):
        """
        Return a C{list} of one L{LiveForm} parameter for editing a
        L{PostalAddress}.

        @type postalAddress: L{PostalAddress} or C{NoneType}

        @param postalAddress: If not C{None}, an existing contact item from
            which to get the postal address default value.

        @rtype: C{list}
        @return: The parameters necessary for specifying a postal address.
        """
        address = u''
        if postalAddress is not None:
            address = postalAddress.address
        return [
            liveform.Parameter('address', liveform.TEXT_INPUT,
                               unicode, 'Postal Address', default=address)]


    def descriptiveIdentifier(self):
        """
        Return 'Postal Address'
        """
        return u'Postal Address'


    def createContactItem(self, person, address):
        """
        Create a new L{PostalAddress} associated with the given person based on
        the given postal address.

        @type person: L{Person}
        @param person: The person with whom to associate the new
            L{EmailAddress}.

        @type address: C{unicode}
        @param address: The value to use for the I{address} attribute of the
            newly created L{PostalAddress}.  If C{''}, no L{PostalAddress} will
            be created.

        @rtype: L{PostalAddress} or C{NoneType}
        """
        if address:
            return PostalAddress(
                store=person.store, person=person, address=address)


    def editContactItem(self, contact, address):
        """
        Change the postal address of the given L{PostalAddress} to that
        specified by C{address}.

        @type contact: L{PostalAddress}
        @param contact: The existing contact item to modify.

        @type address: C{unicode}
        @param address: The new value to use for the I{address} attribute of
            the L{PostalAddress}.

        @return: C{None}
        """
        contact.address = address


    def getContactItems(self, person):
        """
        Return a C{list} of the L{PostalAddress} items associated with the
        given person.

        @type person: L{Person}
        """
        return person.store.query(PostalAddress, PostalAddress.person == person)


    def getReadOnlyView(self, contact):
        """
        Return a L{SimpleReadOnlyView} for the given L{PostalAddress}.
        """
        return SimpleReadOnlyView(PostalAddress.address, contact)



class Notes(item.Item):
    typeName = 'mantissa_organizer_addressbook_notes'

    notes = attributes.text(allowNone=False)
    person = attributes.reference(allowNone=False)



class NotesContactType(BaseContactType):
    """
    Contact type plugin which allows a person to be annotated with a free-form
    textual note.
    """
    implements(IContactType)
    allowMultipleContactItems = False

    def getParameters(self, notes):
        """
        Return a C{list} of one L{LiveForm} parameter for editing a
        L{Notes}.

        @type notes: L{Notes} or C{NoneType}
        @param notes: If not C{None}, an existing contact item from
            which to get the parameter's default value.

        @rtype: C{list}
        """
        defaultNotes = u''
        if notes is not None:
            defaultNotes = notes.notes
        return [
            liveform.Parameter('notes', liveform.TEXTAREA_INPUT,
                               unicode, 'Notes', default=defaultNotes)]


    def descriptiveIdentifier(self):
        """
        Return 'Notes'
        """
        return u'Notes'


    def createContactItem(self, person, notes):
        """
        Create a new L{Notes} associated with the given person based on the
        given string.

        @type person: L{Person}
        @param person: The person with whom to associate the new L{Notes}.

        @type notes: C{unicode}
        @param notes: The value to use for the I{notes} attribute of the newly
        created L{Notes}.  If C{''}, no L{Notes} will be created.

        @rtype: L{Notes} or C{NoneType}
        """
        if notes:
            return Notes(
                store=person.store, person=person, notes=notes)


    def editContactItem(self, contact, notes):
        """
        Set the I{notes} attribute of C{contact} to the value of the C{notes}
        parameter.

        @type contact: L{Notes}
        @param contact: The existing contact item to modify.

        @type notes: C{unicode}
        @param notes: The new value to use for the I{notes} attribute of
            the L{Notes}.

        @return: C{None}
        """
        contact.notes = notes


    def getContactItems(self, person):
        """
        Return a C{list} of the L{Notes} items associated with the given
        person.  If none exist, create one, wrap it in a list and return it.

        @type person: L{Person}
        """
        notes = list(person.store.query(Notes, Notes.person == person))
        if not notes:
            return [Notes(store=person.store,
                          person=person,
                          notes=u'')]
        return notes


    def getReadOnlyView(self, contact):
        """
        Return a L{SimpleReadOnlyView} for the given L{Notes}.
        """
        return SimpleReadOnlyView(Notes.notes, contact)



class AddPerson(item.Item):
    implements(ixmantissa.INavigableElement)

    typeName = 'mantissa_add_person'
    schemaVersion = 2

    powerupInterfaces = (ixmantissa.INavigableElement,)
    organizer = dependsOn(Organizer)

    def getTabs(self):
        return []



def addPerson1to2(old):
    ap = old.upgradeVersion(old.typeName, 1, 2)
    ap.organizer = old.store.findOrCreate(Organizer)
    return ap

registerUpgrader(addPerson1to2, AddPerson.typeName, 1, 2)



class AddPersonFragment(athena.LiveFragment):
    """
    View class for L{AddPerson}, presenting a user interface for creating a new
    L{Person}.

    @ivar organizer: The L{Organizer} instance which will be used to add the
        person.
    """
    docFactory = ThemedDocumentFactory('add-person', 'store')
    jsClass = u'Mantissa.People.AddPerson'

    def __init__(self, organizer):
        athena.LiveFragment.__init__(self)
        self.organizer = organizer
        self.store = organizer.store


    def head(self):
        """
        Supply no content to the head area of the page.
        """
        return None


    _baseParameters = [
        liveform.Parameter('nickname', liveform.TEXT_INPUT,
                           _normalizeWhitespace, 'Name')]

    def render_addPersonForm(self, ctx, data):
        """
        Create and return a L{liveform.LiveForm} for creating a new L{Person}.
        """
        addPersonForm = liveform.LiveForm(
            self.addPerson, self._baseParameters, description='Add Person')
        addPersonForm.compact()
        addPersonForm.jsClass = u'Mantissa.People.AddPersonForm'
        addPersonForm.setFragmentParent(self)
        return addPersonForm


    def addPerson(self, nickname):
        """
        Create a new L{Person} with the given C{nickname}.

        @type nickname: C{unicode}
        @param nickname: The value for the I{name} attribute of the created
            L{Person}.

        @raise L{liveform.InputError}: When some aspect of person creation
        raises a L{ValueError}.
        """
        try:
            self.organizer.createPerson(nickname)
        except ValueError, e:
            raise liveform.InputError(unicode(e))
    expose(addPerson)



class ImportPeopleWidget(athena.LiveElement):
    """
    Widget that implements importing people to an L{Organizer}.

    @ivar organizer: the L{Organizer} to use
    """

    docFactory = ThemedDocumentFactory('import-people', 'store')

    jsClass = u'Mantissa.People.ImportPeopleWidget'

    def __init__(self, organizer):
        athena.LiveElement.__init__(self)
        self.organizer = organizer
        self.store = organizer.store


    def _parseAddresses(addresses):
        """
        Extract name/address pairs from an RFC 2822 style address list.

        For addresses without a display name, the name defaults to the
        local-part for the purpose of importing.

        @type addresses: unicode
        @return: a list of C{(name, email)} tuples
        """
        def coerce((name, email)):
            if len(email):
                if not len(name):
                    name = email.split(u'@', 1)[0]  # lame
                return (name, email)
        coerced = map(coerce, getaddresses([addresses]))
        return [r for r in coerced if r is not None]
    _parseAddresses = staticmethod(_parseAddresses)


    def importPeopleForm(self, request, tag):
        """
        Create and return a L{liveform.LiveForm} for adding new L{Person}s.
        """
        form = liveform.LiveForm(
            self.importAddresses,
            [liveform.Parameter('addresses', liveform.TEXTAREA_INPUT,
                                self._parseAddresses, 'Email Addresses')],
            description='Import People')
        form.jsClass = u'Mantissa.People.ImportPeopleForm'
        form.compact()
        form.setFragmentParent(self)
        return form
    importPeopleForm = renderer(importPeopleForm)


    def importAddresses(self, addresses):
        """
        Create new L{Person}s for the given names and email addresses.
        Names and emails that already exist are ignored.

        @param addresses: a sequence of C{(name, email)} tuples
                          (as returned from L{_parseAddresses})
        @return: the names of people actually imported
        """
        results = []
        for (name, address) in addresses:
            def txn():
                # Skip names and addresses that already exist.
                if self.organizer.personByEmailAddress(address) is not None:
                    return
                # XXX: Needs a better existence check.
                if self.store.query(Person, Person.name == name).count():
                    return

                try:
                    person = self.organizer.createPerson(name)
                    self.organizer.createContactItem(
                        EmailContactType(self.store), person,
                        dict(email=address))
                except ValueError, e:
                    # XXX: Granularity required;  see #711 and #2435
                    raise liveform.ConfigurationError(u'%r' % (e,))
                return person
            results.append(self.store.transact(txn))
        return [p.name for p in results if p is not None]



class PersonExtractFragment(TabularDataView):
    def render_navigation(self, ctx, data):
        return inevow.IQ(
                webtheme.getLoader('person-extracts')).onePattern('navigation')



class ExtractWrapperColumnView(ColumnViewBase):
    def stanFromValue(self, idx, item, value):
        return inevow.IRenderer(item.extract)



class MugshotUploadForm(rend.Page):
    """
    Resource which presents some UI for associating a new mugshot with
    L{person}.

    @ivar person: The person whose mugshot is going to be changed.
    @type person: L{Person}

    @ivar cbGotImage: Function to call after a successful upload.  It will be
    passed the C{unicode} content-type of the uploaded image and a file
    containing the uploaded image.
    """
    docFactory = ThemedDocumentFactory('mugshot-upload-form', 'store')

    def __init__(self, person, cbGotMugshot):
        rend.Page.__init__(self)
        self.person = person
        self.organizer  = person.organizer
        self.store = person.store
        self.cbGotMugshot = cbGotMugshot


    def renderHTTP(self, ctx):
        """
        Extract the data from the I{uploaddata} field of the request and pass
        it to our callback.
        """
        req = inevow.IRequest(ctx)
        if req.method == 'POST':
            udata = req.fields['uploaddata']
            self.cbGotMugshot(udata.type.decode('ascii'), udata.file)
        return rend.Page.renderHTTP(self, ctx)


    def render_smallerMugshotURL(self, ctx, data):
        """
        Render the URL of a smaller version of L{person}'s mugshot.
        """
        return self.organizer.linkToPerson(self.person) + '/mugshot/smaller'



class Mugshot(item.Item):
    """
    An image that is associated with a person
    """
    schemaVersion = 3

    type = attributes.text(doc="""
    Content-type of image data
    """, allowNone=False)

    body = attributes.path(doc="""
    Path to image data
    """, allowNone=False)

    # at the moment we require an upgrader to change the size of either of the
    # mugshot thumbnails.  we might save ourselves some effort by generating
    # scaled versions on demand, and caching them.
    smallerBody = attributes.path(doc="""
    Path to smaller version of image data
    """, allowNone=False)

    person = attributes.reference(doc="""
    L{Person} this mugshot is of
    """, allowNone=False)

    size = 120
    smallerSize = 60

    def fromFile(cls, person, inputFile, format):
        """
        Create a L{Mugshot} item for C{person} out of the image data in
        C{inputFile}, or update C{person}'s existing L{Mugshot} item to
        reflect the new images.

        @param inputFile: An image of a person.
        @type inputFile: C{file}

        @param person: The person this mugshot is to be associated with.
        @type person: L{Person}

        @param format: The format of the data in C{inputFile}.
        @type format: C{unicode} (e.g. I{jpeg})

        @rtype: L{Mugshot}
        """
        body = cls.makeThumbnail(inputFile, person, format, smaller=False)
        inputFile.seek(0)
        smallerBody = cls.makeThumbnail(
            inputFile, person, format, smaller=True)

        ctype = u'image/' + format

        self = person.store.findUnique(
            cls, cls.person == person, default=None)
        if self is None:
            self = cls(store=person.store,
                       person=person,
                       type=ctype,
                       body=body,
                       smallerBody=smallerBody)
        else:
            self.body = body
            self.smallerBody = smallerBody
            self.type = ctype
        return self
    fromFile = classmethod(fromFile)


    def makeThumbnail(cls, inputFile, person, format, smaller):
        """
        Make a thumbnail of a mugshot image and store it on disk.

        @param inputFile: The image to thumbnail.
        @type inputFile: C{file}

        @param person: The person this mugshot thumbnail is associated with.
        @type person: L{Person}

        @param format: The format of the data in C{inputFile}.
        @type format: C{str} (e.g. I{jpeg})

        @param smaller: Thumbnails are available in two sizes.  if C{smaller}
        is C{True}, then the thumbnail will be in the smaller of the two
        sizes.
        @type smaller: C{bool}

        @return: path to the thumbnail.
        @rtype: L{twisted.python.filepath.FilePath}
        """
        dirsegs = ['mugshots', str(person.storeID)]
        if smaller:
            dirsegs.insert(1, 'smaller')
            size = cls.smallerSize
        else:
            size = cls.size
        atomicOutputFile = person.store.newFile(*dirsegs)
        makeThumbnail(inputFile, atomicOutputFile, size, format)
        atomicOutputFile.close()
        return atomicOutputFile.finalpath
    makeThumbnail = classmethod(makeThumbnail)


    def placeholderForPerson(cls, person):
        """
        Make an unstored, placeholder L{Mugshot} instance for the given
        person.

        @param person: A person without a L{Mugshot}.
        @type person: L{Person}

        @rtype: L{Mugshot}
        """
        imageDir = FilePath(__file__).parent().child(
            'static').child('images')
        return cls(
            type=u'image/png',
            body=imageDir.child('mugshot-placeholder.png'),
            smallerBody=imageDir.child(
                'mugshot-placeholder-smaller.png'),
            person=person)
    placeholderForPerson = classmethod(placeholderForPerson)

def mugshot1to2(old):
    """
    Upgrader for L{Mugshot} from version 1 to version 2, which sets the
    C{smallerBody} attribute to the path of a smaller mugshot image.
    """
    smallerBody = Mugshot.makeThumbnail(old.body.open(),
                                        old.person,
                                        old.type.split('/')[1],
                                        smaller=True)

    return old.upgradeVersion(Mugshot.typeName, 1, 2,
                              person=old.person,
                              type=old.type,
                              body=old.body,
                              smallerBody=smallerBody)

registerUpgrader(mugshot1to2, Mugshot.typeName, 1, 2)



item.declareLegacyItem(
    Mugshot.typeName,
    2,
    dict(person=attributes.reference(),
         type=attributes.text(),
         body=attributes.path(),
         smallerBody=attributes.path()))



def mugshot2to3(old):
    """
    Upgrader for L{Mugshot} from version 2 to version 3, which re-thumbnails
    the mugshot to take into account the new value of L{Mugshot.smallerSize}.
    """
    new = old.upgradeVersion(Mugshot.typeName, 2, 3,
                             person=old.person,
                             type=old.type,
                             body=old.body,
                             smallerBody=old.smallerBody)
    new.smallerBody = new.makeThumbnail(
        new.body.open(), new.person, new.type[len('image/'):], smaller=True)
    return new

registerUpgrader(mugshot2to3, Mugshot.typeName, 2, 3)



class MugshotResource(rend.Page):
    """
    Web accessible resource that serves Mugshot images. Serves a smaller
    mugshot if the final path segment is "smaller"
    """
    smaller = False

    def __init__(self, mugshot):
        """
        @param mugshot: L{Mugshot}
        """
        self.mugshot = mugshot
        rend.Page.__init__(self)


    def locateChild(self, ctx, segments):
        if segments == ('smaller',):
            self.smaller = True
            return (self, ())
        return rend.NotFound


    def renderHTTP(self, ctx):
        if self.smaller:
            path = self.mugshot.smallerBody
        else:
            path = self.mugshot.body

        return static.File(path.path, str(self.mugshot.type))



def getPersonURL(person):
    """
    Return the address the view for this Person is available at.
    """
    return person.organizer.linkToPerson(person)



class PersonDetailFragment(athena.LiveFragment, rend.ChildLookupMixin):
    """
    Renderer for detailed information about a L{Person}.
    """
    fragmentName = 'person-detail'
    live = 'athena'

    def __init__(self, person):
        athena.LiveFragment.__init__(self, person)
        self.person = person


    def head(self):
        return None


    def _gotMugshotFile(self, ctype, infile):
        (majortype, minortype) = ctype.split('/')
        if majortype == 'image':
            Mugshot.fromFile(self.person, infile, minortype)


    def child_mugshotUploadForm(self, ctx):
        """
        Return a L{MugshotUploadForm}, which will render some UI for
        associating a new mugshot with this person.
        """
        return MugshotUploadForm(self.person, self._gotMugshotFile)


    def child_mugshot(self, ctx):
        """
        Return a L{MugshotResource} displaying this L{Person}'s mugshot image.
        """
        return MugshotResource(self.person.getMugshot())



components.registerAdapter(PersonDetailFragment, Person, ixmantissa.INavigableFragment)

class PersonFragment(rend.Fragment):
    def __init__(self, person, contactMethod=None):
        rend.Fragment.__init__(self, person,
                               webtheme.getLoader('person-fragment'))
        self.person = person
        self.contactMethod = contactMethod

    def render_person(self, ctx, data):
        detailURL = self.person.organizer.linkToPerson(self.person)

        mugshot = self.person.store.findUnique(Mugshot,
                                               Mugshot.person == self.person,
                                               default=None)
        if mugshot is None:
            mugshotURL = '/Mantissa/images/mugshot-placeholder-smaller.png'
        else:
            mugshotURL = detailURL + '/mugshot/smaller'

        name = self.person.getDisplayName()
        return dictFillSlots(ctx.tag, {'name': name,
                                       'detail-url': detailURL,
                                       'contact-method': self.contactMethod or name,
                                       'mugshot-url': mugshotURL})
