# -*- test-case-name xquotient.test.test_historic.test_needsDelivery1to2 -*-

"""
Create stub database for upgrade of L{xquotient.compose._NeedsDelivery} from
version 1 to version 2.
"""

from axiom.test.historic.stubloader import saveStub

from xquotient.compose import _NeedsDelivery, Composer

def createDatabase(s):
    """
    Install a _NeedsDelivery and Composer on the given store.
    """
    _NeedsDelivery(store=s,
                   composer=Composer(store=s),
                   message=s,
                   toAddress=u'to@host',
                   tries=21)



if __name__ == '__main__':
    saveStub(createDatabase, 9283)
