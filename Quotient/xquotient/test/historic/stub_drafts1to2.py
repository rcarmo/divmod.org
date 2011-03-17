# -*- test-case-name: xquotient.test.historic.test_drafts1to2 -*-

"""
Create stub database for upgrade of L{xquotient.compose.Drafts} from version 1
to version 2.
"""


from axiom.test.historic.stubloader import saveStub

from xquotient.compose import Composer, Drafts


def createDatabase(s):
    """
    Add a Drafts item to the store.
    """
    c = Composer(store=s)
    Drafts(store=s, installedOn=c)
    c.installed()


if __name__ == '__main__':
    saveStub(createDatabase, 10914)
