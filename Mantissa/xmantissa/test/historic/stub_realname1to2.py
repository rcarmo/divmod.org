
"""
Generate a stub for the tests for the deletion of the RealName item.
"""

from axiom.test.historic.stubloader import saveStub

from xmantissa.people import Person, RealName


def createDatabase(store):
    """
    Make a L{Person} with a corresponding L{RealName} which will be deleted.
    """
    person = Person(store=store)
    name = RealName(store=store, person=person)


if __name__ == '__main__':
    saveStub(createDatabase, 13508)
