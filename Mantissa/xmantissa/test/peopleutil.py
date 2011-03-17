"""
Helpful utilities for code which tests functionality related to
L{xmantissa.people}.
"""
from zope.interface import implements

from twisted.python.reflect import qual

from axiom.store import Store
from axiom.item import Item
from axiom.attributes import inmemory, text

from xmantissa.ixmantissa import IPeopleFilter, IContactType, IWebTranslator
from xmantissa.people import Organizer

from epsilon.descriptor import requiredAttribute


class PeopleFilterTestMixin:
    """
    Mixin for testing L{IPeopleFilter} providers.  Requires the following
    attributes:

    @ivar peopleFilterClass: The L{IPeopleFilter} being tested.
    @type peopleFilterClass: L{IPeopleFilter} provider.

    @ivar peopleFilterName: The expected name of L{peopleFilterClass}.
    @type peopleFilterName: C{str}
    """
    peopleFilterClass = requiredAttribute('peopleFilterClass')
    peopleFilterName = requiredAttribute('peopleFilterName')


    def assertComparisonEquals(self, comparison):
        """
        Instantiate L{peopleFilterClass}, call
        L{IPeopleFilter.getPeopleQueryComparison} on it and assert that its
        result is equal to C{comparison}.

        @type comparison: L{axiom.iaxiom.IComparison}
        """
        peopleFilter = self.peopleFilterClass()
        actualComparison = peopleFilter.getPeopleQueryComparison(Store())
        # none of the Axiom query objects have meaningful equality
        # comparisons, but their string representations do.
        # this assertion should be addressed along with #2464
        self.assertEqual(str(actualComparison), str(comparison))


    def makeOrganizer(self):
        """
        Return an L{Organizer}.
        """
        return Organizer(store=Store())


    def test_implementsInterface(self):
        """
        Our people filter should provide L{IPeopleFilter}.
        """
        self.assertTrue(IPeopleFilter.providedBy(self.peopleFilterClass()))


    def test_organizerIncludesIt(self):
        """
        L{Organizer.getPeopleFilters} should include an instance of our
        L{IPeopleFilter}.
        """
        organizer = self.makeOrganizer()
        self.assertIn(
            self.peopleFilterClass,
            [filter.__class__ for filter in organizer.getPeopleFilters()])


    def test_filterName(self):
        """
        Our L{IPeopleFilter}'s I{filterName} should match L{peopleFilterName}.
        """
        self.assertEqual(
            self.peopleFilterClass().filterName, self.peopleFilterName)



class StubPerson(object):
    """
    Stub implementation of L{Person} used for testing.

    @ivar contactItems: A list of three-tuples of the arguments passed to
        createContactInfoItem.
    """
    name = u'person'

    def __init__(self, contactItems):
        self.contactItems = contactItems
        self.store = object()


    def createContactInfoItem(self, cls, attr, value):
        """
        Record the creation of a new contact item.
        """
        self.contactItems.append((cls, attr, value))


    def getContactInfoItems(self, itemType, valueColumn):
        """
        Return an empty list.
        """
        return []


    def getMugshot(self):
        """
        Return C{None} since there is no mugshot.
        """
        return None


    def getDisplayName(self):
        """
        Return a name of some sort.
        """
        return u"Alice"


    def getEmailAddress(self):
        """
        Return an email address.
        """
        return u"alice@example.com"



class StubTranslator(object):
    """
    Translate between a dummy row identifier and a dummy object.
    """
    implements(IWebTranslator)

    def __init__(self, rowIdentifier, item):
        self.fromWebID = {rowIdentifier: item}.__getitem__
        self.toWebID = {item: rowIdentifier}.__getitem__



class StubOrganizer(object):
    """
    Mimic some of the API presented by L{Organizer}.

    @ivar people: A C{dict} mapping C{unicode} strings giving person names to
    person objects.  These person objects will be returned from appropriate
    calls to L{personByName}.

    @ivar contactTypes: a C{list} of L{IContactType}s.

    @ivar groupedReadOnlyViews: The C{dict} to be returned from
    L{groupReadOnlyViews}

    @ivar editedPeople: A list of the arguments which have been passed to the
    C{editPerson} method.

    @ivar deletedPeople: A list of the arguments which have been passed to the
    C{deletePerson} method.

    @ivar contactEditorialParameters: A mapping of people to lists.  When
    passed a person, L{getContactEditorialParameters} will return the
    corresponding list.

    @ivar groupedReadOnlyViewPeople: A list of the arguments passed to
    L{groupReadOnlyViews}.

    @ivar peopleTags: The value to return from L{getPeopleTags}.
    @type peopleTags: C{list}

    @ivar peopleFilters: The sequence to return from L{getPeopleFilters}.
    @type peopleFilters: C{list}

    @ivar organizerPlugins: The sequence of return from L{getOrganizerPlugins}.
    @type organizerPlugins: C{list}
    """
    _webTranslator = StubTranslator(None, None)

    def __init__(self, store=None, contactTypes=None, deletedPeople=None,
            editedPeople=None, contactEditorialParameters=None,
            groupedReadOnlyViews=None, peopleTags=None, peopleFilters=None,
            organizerPlugins=None):
        self.store = store
        self.people = {}
        if contactTypes is None:
            contactTypes = []
        if deletedPeople is None:
            deletedPeople = []
        if editedPeople is None:
            editedPeople = []
        if contactEditorialParameters is None:
            contactEditorialParameters = []
        if groupedReadOnlyViews is None:
            groupedReadOnlyViews = {}
        if peopleTags is None:
            peopleTags = []
        if peopleFilters is None:
            peopleFilters = []
        if organizerPlugins is None:
            organizerPlugins = []
        self.contactTypes = contactTypes
        self.deletedPeople = deletedPeople
        self.editedPeople = editedPeople
        self.contactEditorialParameters = contactEditorialParameters
        self.groupedReadOnlyViews = groupedReadOnlyViews
        self.groupedReadOnlyViewPeople = []
        self.peopleTags = peopleTags
        self.peopleFilters = peopleFilters
        self.organizerPlugins = organizerPlugins


    def personByName(self, name):
        return self.people[name]


    def lastNameOrder(self):
        return None


    def deletePerson(self, person):
        self.deletedPeople.append(person)


    def editPerson(self, person, name, edits):
        self.editedPeople.append((person, name, edits))


    def toContactEditorialParameter(self, contactType, person):
        for (_contactType, param) in self.contactEditorialParameters[person]:
            if _contactType == contactType:
                return param


    def getContactEditorialParameters(self, person):
        return self.contactEditorialParameters[person]


    def getContactTypes(self):
        return self.contactTypes


    def getPeopleFilters(self):
        """
        Return L{peopleFilters}.
        """
        return self.peopleFilters


    def groupReadOnlyViews(self, person):
        """
        Return L{groupedReadOnlyViews}.
        """
        self.groupedReadOnlyViewPeople.append(person)
        return self.groupedReadOnlyViews


    def linkToPerson(self, person):
        return "/person/" + person.getDisplayName()


    def getPeopleTags(self):
        """
        Return L{peopleTags}.
        """
        return self.peopleTags


    def getOrganizerPlugins(self):
        """
        Return L{organizerPlugins}.
        """
        return self.organizerPlugins



class StubOrganizerPlugin(Item):
    """
    Organizer powerup which records which people are created and gives back
    canned responses to method calls.
    """
    name = text(
        doc="""
        @see IOrganizerPlugin.name
        """)

    createdPeople = inmemory(
        doc="""
        A list of all L{Person} items created since this item was last loaded
        from the database.
        """)

    contactTypes = inmemory(
        doc="""
        A list of L{IContactType} implementors to return from
        L{getContactTypes}.
        """)

    peopleFilters = inmemory(
        doc="""
        A list of L{IPeopleFilter} imlpementors to return from
        L{getPeopleFilters}.
        """)

    renamedPeople = inmemory(
        doc="""
        A list of two-tuples of C{unicode} with the first element giving the
        name of each L{Person} item whose name changed at the time of the
        change and the second element giving the value passed for the old name
        parameter.
        """)

    createdContactItems = inmemory(
        doc="""
        A list of contact items created since this item was last loaded from
        the database.
        """)

    editedContactItems = inmemory(
        doc="""
        A list of contact items edited since this item was last loaded from
        the database.
        """)

    personalization = inmemory(
        doc="""
        An objects to be returned by L{personalize}.
        """)

    personalizedPeople = inmemory(
        doc="""
        A list of people passed to L{personalize}.
        """)

    def activate(self):
        """
        Initialize in-memory state tracking attributes to default values.
        """
        self.createdPeople = []
        self.renamedPeople = []
        self.createdContactItems = []
        self.editedContactItems = []
        self.personalization = None
        self.personalizedPeople = []


    def personCreated(self, person):
        """
        Record the creation of a L{Person}.
        """
        self.createdPeople.append(person)


    def personNameChanged(self, person, oldName):
        """
        Record the change of a L{Person}'s name.
        """
        self.renamedPeople.append((person.name, oldName))


    def contactItemCreated(self, contactItem):
        """
        Record the creation of a contact item.
        """
        self.createdContactItems.append(contactItem)


    def contactItemEdited(self, contactItem):
        """
        Record the editing of a contact item.
        """
        self.editedContactItems.append(contactItem)


    def getContactTypes(self):
        """
        Return the contact types list this item was constructed with.
        """
        return self.contactTypes


    def getPeopleFilters(self):
        """
        Return L{peopleFilters}.
        """
        return self.peopleFilters


    def personalize(self, person):
        """
        Record a personalization attempt and return C{self.personalization}.
        """
        self.personalizedPeople.append(person)
        return self.personalization



class StubReadOnlyView(object):
    """
    Test double for the objects returned by L{IContactType.getReadOnlyView}.

    @ivar item: The contact item the view is for.
    @ivar type: The contact type the contact item comes from.
    """
    def __init__(self, contactItem, contactType):
        self.item = contactItem
        self.type = contactType




class StubContactType(object):
    """
    Behaviorless contact type implementation used for tests.

    @ivar parameters: A list of L{xmantissa.liveform.Parameter} instances which
        will become the return value of L{getParameters}.
    @ivar createdContacts: A list of tuples of the arguments passed to
        C{createContactItem}.
    @ivar editorialForm: The object which will be returned from
        L{getEditFormForPerson}.
    @ivar editedContacts: A list of the contact items passed to
        L{getEditFormForPerson}.
    @ivar contactItems: The list of objects which will be returned from
        L{getContactItems}.
    @ivar queriedPeople: A list of the person items passed to
        L{getContactItems}.
    @ivar editedContacts: A list of two-tuples of the arguments passed to
        L{editContactItem}.
    @ivar createContactItems: A boolean indicating whether C{createContactItem}
        will return an object pretending to be a new contact item (C{True}) or
        C{None} to indicate no contact item was created (C{False}).
    @ivar theDescriptiveIdentifier: The object to return from
        L{descriptiveIdentifier}.
    @ivar contactGroup: The object to return from L{getContactGroup}.
    """
    implements(IContactType)

    def __init__(self, parameters, editorialForm, contactItems,
            createContactItems=True, allowMultipleContactItems=True,
            theDescriptiveIdentifier=u'', contactGroup=None):
        self.parameters = parameters
        self.createdContacts = []
        self.editorialForm = editorialForm
        self.editedContacts = []
        self.contactItems = contactItems
        self.queriedPeople = []
        self.editedContacts = []
        self.createContactItems = createContactItems
        self.allowMultipleContactItems = allowMultipleContactItems
        self.theDescriptiveIdentifier = theDescriptiveIdentifier
        self.contactGroup = contactGroup


    def getParameters(self, ignore):
        """
        Return L{parameters}.
        """
        return self.parameters


    def uniqueIdentifier(self):
        """
        Return the L{qual} of this class.
        """
        return qual(self.__class__).decode('ascii')


    def descriptiveIdentifier(self):
        """
        Return L{theDescriptiveIdentifier}.
        """
        return self.theDescriptiveIdentifier


    def getEditFormForPerson(self, contact):
        """
        Return an object which is supposed to be a form for editing an existing
        instance of this contact type and record the contact object which was
        passed in.
        """
        self.editedContacts.append(contact)
        return self.editorialForm


    def createContactItem(self, person, **parameters):
        """
        Record an attempt to create a new contact item of this type for the
        given person.
        """
        contactItem = (person, parameters)
        self.createdContacts.append(contactItem)
        if self.createContactItems:
            return contactItem
        return None


    def getContactItems(self, person):
        """
        Return C{self.contactItems} and record the person item passed in.
        """
        self.queriedPeople.append(person)
        return self.contactItems


    def editContactItem(self, contact, **changes):
        """
        Record an attempt to edit the details of a contact item.
        """
        self.editedContacts.append((contact, changes))


    def getContactGroup(self, contactItem):
        """
        Return L{contactGroup}.
        """
        return self.contactGroup


    def getReadOnlyView(self, contact):
        """
        Return a stub view object for the given contact.

        @rtype: L{StubReadOnlyView}
        """
        return StubReadOnlyView(contact, self)
