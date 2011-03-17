
"""
Generate a stub for the tests for the upgrade from schema version 1 to 2 of the
Person item.
"""

from epsilon.extime import Time

from axiom.test.historic.stubloader import saveStub

from xmantissa.people import Organizer, Person

NAME = u'testuser'
CREATED = Time.fromPOSIXTimestamp(1234567890)

def createDatabase(store):
    """
    Make a L{Person} in the given store.
    """
    organizer = Organizer(store=store)
    person = Person(
        store=store,
        organizer=organizer,
        name=NAME)
    person.created = CREATED


if __name__ == '__main__':
    saveStub(createDatabase, 13023)
