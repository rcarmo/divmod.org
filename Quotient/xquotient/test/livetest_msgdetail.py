from epsilon.extime import Time

from axiom.store import Store
from axiom import attributes
from axiom.tags import Catalog
from axiom.item import Item
from axiom.dependency import installOn

from nevow.livetrial import testcase
from nevow import tags, loaders
from nevow.athena import expose

from xmantissa.webtheme import getLoader
from xmantissa import people

from xquotient.exmess import Message, MessageDetail, MessageBodyFragment, MessageActions
from xquotient.inbox import Inbox
from xquotient import equotient
from xquotient.test.util import MIMEReceiverMixin, PartMaker

class _Header(Item):
    part = attributes.reference()
    name = attributes.text()
    value = attributes.text()

class _Part(Item):
    z = attributes.integer()

    def getHeader(self, k):
        for hdr in self.store.query(
            _Header, attributes.AND(_Header.part == self,
                                    _Header.name == k.lower())):
            return hdr.value
        raise equotient.NoSuchHeader(k)

    def walkMessage(self, *junk):
        return ()
    walkAttachments = walkMessage

    def associateWithMessage(self, message):
        pass

    def relatedAddresses(self):
        return []

    def guessSentTime(self, default):
        return Time()

    def getAllReplyAddresses(self):
        return {}

    def getReplyAddresses(self):
        return []



def _docFactoryFactory(testName, renderMethod='msgDetail'):
    return loaders.stan(tags.div[
                tags.div(render=tags.directive('liveTest'))[testName],
                tags.div(render=tags.directive('msgDetail'))])

class _MsgDetailTestMixin(object):
    """
    Mixin which provides some methods for setting up stores and messages
    """
    def _setUpStore(self):
        """
        Create a store and install the items required by a
        L{xquotient.exmess.Message}

        @rtype: L{axiom.store.Store}
        """
        s = Store()
        installOn(Inbox(store=s), s)
        return s

    def _setUpMsg(self):
        """
        Install an innocuous incoming message in a newly-created store

        @rtype: L{xquotient.exmess.Message}
        """
        s = self._setUpStore()

        m = Message.createIncoming(s, _Part(store=s), u'test://test')
        m.subject = u'the subject'
        m.sender = u'sender@host'
        m.senderDisplay = u'Sender'
        m.recipient = u'recipient@host'
        m.sentWhen = Time.fromPOSIXTimestamp(0)
        m.receivedWhen = Time.fromPOSIXTimestamp(1)
        m.classifyClean()
        return m



class MsgDetailTestCase(testcase.TestCase, _MsgDetailTestMixin):
    """
    Tests for L{xquotient.exmess.MessageDetail}
    """
    jsClass = u'Quotient.Test.MsgDetailTestCase'

    def setUp(self):
        """
        Setup & populate a store, and render a
        L{xquotient.exmess.MessageDetail}
        """
        f = MessageDetail(self._setUpMsg())
        f.setFragmentParent(self)
        f.docFactory = getLoader(f.fragmentName)
        return f
    expose(setUp)



class MsgDetailTagsTestCase(testcase.TestCase, _MsgDetailTestMixin):
    """
    Tests for L{xquotient.exmess.MessageDetail} and tags
    """
    jsClass = u'Quotient.Test.MsgDetailTagsTestCase'

    def _setUpMsg(self, tags):
        """
        Same as L{_MsgDetailTestMixin._setUpMsg}, but with a tagged message!

        @param tags: tags to assign to message
        @type tags: C{list} of C{unicode}
        """
        msg = super(MsgDetailTagsTestCase, self)._setUpMsg()
        cat = msg.store.findOrCreate(Catalog)
        for tag in tags:
            cat.tag(msg, tag)
        return msg


    def setUp(self, tags):
        """
        Setup & populate a store, and render a
        L{xquotient.exmess.MessageDetail}
        """
        f = MessageDetail(self._setUpMsg(tags))
        f.setFragmentParent(self)
        f.docFactory = getLoader(f.fragmentName)
        return f
    expose(setUp)



class MsgDetailAddPersonTestCase(testcase.TestCase, _MsgDetailTestMixin):
    """
    Test adding a person from the msg detail
    """
    jsClass = u'Quotient.Test.MsgDetailAddPersonTestCase'

    def __init__(self, *a, **k):
        super(MsgDetailAddPersonTestCase, self).__init__(*a, **k)
        self._stores = {}

    def _setUpStore(self):
        s = super(MsgDetailAddPersonTestCase, self)._setUpStore()
        installOn(people.AddPerson(store=s), s)
        return s

    def verifyPerson(self, key):
        """
        Called from the client after a person has been added.  Verifies that
        there is only one person, and that his details match those of the
        sender of the single message in our store
        """
        store = self._stores[key]
        organizer = store.findUnique(people.Organizer)
        p = self._stores[key].findUnique(
            people.Person,
            people.Person.storeID != organizer.storeOwnerPerson.storeID)
        self.assertEquals(p.getEmailAddress(), 'sender@host')
        self.assertEquals(p.getDisplayName(), 'Sender')
    expose(verifyPerson)

    def setUp(self, key):
        """
        Setup & populate a store, and render a
        L{xquotient.exmess.MessageDetail}
        """
        msg = self._setUpMsg()
        self._stores[key] = msg.store
        f = MessageDetail(msg)
        f.setFragmentParent(self)
        f.docFactory = getLoader(f.fragmentName)
        return f
    expose(setUp)

class MsgDetailInitArgsTestCase(testcase.TestCase, _MsgDetailTestMixin):
    """
    Test for L{xquotient.exmess.MessageDetail}'s initargs
    """
    jsClass = u'Quotient.Test.MsgDetailInitArgsTestCase'

    def _setUpMsg(self):
        m = super(MsgDetailInitArgsTestCase, self)._setUpMsg()
        m.store.findUnique(Inbox).showMoreDetail = True
        return m

    def setUp(self):
        """
        Setup & populate a store, and render a
        L{xquotient.exmess.MessageDetail}
        """
        f = MessageDetail(self._setUpMsg())
        f.setFragmentParent(self)
        f.docFactory = getLoader(f.fragmentName)
        return f
    expose(setUp)


class _MsgDetailHeadersTestMixin(_MsgDetailTestMixin):
    """
    Extension of L{_MsgDetailTestMixin} which allows the client to set
    arbitrary headers on our message
    """

    def _setUpMsg(self, headers):
        msg = super(_MsgDetailHeadersTestMixin, self)._setUpMsg()
        for (k, v) in headers.iteritems():
            _Header(store=msg.store,
                    part=msg.impl,
                    name=k.lower(),
                    value=v)
        return msg


class MsgDetailHeadersTestCase(testcase.TestCase, _MsgDetailHeadersTestMixin):
    """
    Test for the rendering of messages which have various headers set
    """
    jsClass = u'Quotient.Test.MsgDetailHeadersTestCase'

    def setUp(self, headers):
        """
        Setup & populate a store with a L{xquotient.exmess.Message} which has
        the headers in C{headers} set to the given values

        @type headers: C{dict} of C{unicode}
        """
        msg = self._setUpMsg(headers)
        f = MessageDetail(msg)
        f.setFragmentParent(self)
        f.docFactory = getLoader(f.fragmentName)
        return f
    expose(setUp)


class MsgDetailCorrespondentPeopleTestCase(testcase.TestCase, _MsgDetailHeadersTestMixin):
    """
    Tests for rendering a message where various correspondents are or aren't
    represented by L{xmantissa.people.Person} items in the store
    """
    jsClass = u'Quotient.Test.MsgDetailCorrespondentPeopleTestCase'

    def _setUpStore(self):
        store = super(MsgDetailCorrespondentPeopleTestCase, self)._setUpStore()
        self.organizer = people.Organizer(store=store)
        installOn(self.organizer, store)
        return store

    def setUp(self, peopleAddresses, sender, recipient, cc):
        """
        Setup & populate a store with a L{xquotient.exmess.Message} which has
        correspondents set to the values of C{cc} and C{recipient}, and a
        person for each email address in C{peopleAddresses}

        @param sender: address to use as the value of the C{from} header
        @type cc: C{unicode}

        @param recipient: address to use as the value of the C{recipient}
        attribute
        @type cc: C{unicode}

        @param cc: addresses to use as the value of the C{cc} header
        @type cc: C{unicode}

        @type headers: C{dict} of C{unicode}
        """
        headers = {u'from': sender}
        if cc:
            headers[u'cc'] = cc
        msg = self._setUpMsg(headers)
        msg.recipient = recipient
        for addr in peopleAddresses:
            people.EmailAddress(
                store=msg.store,
                address=addr,
                person=people.Person(
                    store=msg.store,
                    organizer=self.organizer))
        f = MessageDetail(msg)
        f.setFragmentParent(self)
        f.docFactory = getLoader(f.fragmentName)
        return f
    expose(setUp)



class MsgBodyTestCase(testcase.TestCase, MIMEReceiverMixin):
    """
    Tests for the selection and rendering of alternate text parts
    """
    jsClass = u'Quotient.Test.MsgBodyTestCase'

    def setUp(self, key):
        # is there a better way?  TestCase.mktemp() doesn't work otherwise
        self._testMethodName = key
        self.setUpMailStuff()
        p = self.createMIMEReceiver().feedStringNow(
            PartMaker('multipart/alternative', 'alt',
                PartMaker('text/plain', 'this is the text/plain'),
                PartMaker('text/html', 'this is the text/html')).make())
        f = MessageBodyFragment(p.message, 'text/plain')
        f.setFragmentParent(self)
        return f
    expose(setUp)



class ActionsTestCase(testcase.TestCase):
    """
    Tests for Quotient.Message's actions stuff
    """
    jsClass = u'Quotient.Test.ActionsTestCase'


    def setUp(self):
        f = MessageActions()
        f.setFragmentParent(self)
        return f
    expose(setUp)
