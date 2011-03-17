from twisted.trial.unittest import TestCase

from epsilon.extime import Time

from axiom.store import Store
from axiom.dependency import installOn

from xmantissa.people import (
    Organizer, Person, EmailAddress, PersonFragment)

from xquotient.qpeople import MessageLister, AddPersonFragment
from xquotient.test.test_inbox import testMessageFactory


class AddPersonTestCase(TestCase):
    def test_addPerson(self):
        """
        Test that adding a person via the Quotient version of
        C{AddPersonFragment} works.
        """
        def keyword(contactType):
            return contactType.uniqueIdentifier().encode('ascii')

        store = Store()
        self.organizer = Organizer(store=store)
        installOn(self.organizer, store)
        addPersonFrag = AddPersonFragment(self.organizer)
        name = u'Captain P.'
        email = u'foo@bar'
        fragment = addPersonFrag.addPerson(name, email)
        self.assertTrue(isinstance(fragment, PersonFragment))
        person = fragment.person
        self.assertIdentical(
            store.findUnique(
                Person,
                Person.storeID != self.organizer.storeOwnerPerson.storeID),
            person)
        self.assertEqual(person.name, name)
        self.assertEqual(person.getEmailAddress(), email)



class MessageListerTestCase(TestCase):
    def testMostRecentMessages(self):
        s = Store()

        o = Organizer(store=s)
        installOn(o, s)

        def makePerson(name, address):
            return EmailAddress(store=s,
                                address=address,
                                person=Person(store=s,
                                              organizer=o,
                                              name=name)).person

        p11 = makePerson(u'11 Message Person', u'11@person')
        p2  = makePerson(u'2 Message Person', u'2@person')

        def makeMessages(n, email):
            return list(reversed(list(
                        testMessageFactory(store=s,
                                           subject=u'Message %d' % (i,),
                                           sender=email,
                                           spam=False,
                                           receivedWhen=Time())
                        for i in xrange(n))))

        p11messages = makeMessages(11, u'11@person')
        p2messages  = makeMessages(2, u'2@person')

        lister = MessageLister(store=s)

        getMessages = lambda person, count: list(
            lister.mostRecentMessages(person, count))

        self.assertEquals(getMessages(p2, 3), p2messages)
        self.assertEquals(getMessages(p2, 2), p2messages)
        self.assertEquals(getMessages(p2, 1), p2messages[:-1])

        self.assertEquals(getMessages(p11, 12), p11messages)
        self.assertEquals(getMessages(p11, 11), p11messages)
        self.assertEquals(getMessages(p11, 10), p11messages[:-1])

        p11messages[0].trainSpam()

        self.assertEquals(getMessages(p11, 11), p11messages[1:])

        # Used to be:
        # p11messages[1].draft = True
        # but this is now a nonsensical transition.
        p11messages[1].trainSpam()

        self.assertEquals(getMessages(p11, 11), p11messages[2:])

        p11messages[2].moveToTrash()

        self.assertEquals(getMessages(p11, 11), p11messages[3:])


    def test_name(self):
        """
        L{MessageLister} should define a C{name} attribute.
        """
        self.assertEqual(MessageLister.name, u'Messages')
