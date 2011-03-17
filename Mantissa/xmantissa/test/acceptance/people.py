"""
An interactive demonstration of various people-related functionality.

Run this test like this::
    $ twistd -n athena-widget --element=xmantissa.test.acceptance.people.{editperson,addperson}
    $ firefox http://localhost:8080/
"""

from axiom.store import Store
from axiom.dependency import installOn

from xmantissa.people import Organizer, EditPersonView, AddPersonFragment

store = Store()
organizer = Organizer(store=store)
installOn(organizer, store)
person = organizer.createPerson(u'alice')

def editperson():
    """
    Create a database with a Person in it and return the L{EditPersonView} for
    that person.
    """
    return EditPersonView(person)



def addperson():
    """
    Create a database with an L{Organizer} in it and return a
    L{AddPersonFragment} wrapped around the organizer.
    """
    return AddPersonFragment(organizer)
