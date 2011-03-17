# -*- test-case-name: xquotient.test.historic.test_mailinglistfilter1to2 -*-
from axiom.test.historic.stubloader import saveStub
from xquotient.filter import MailingListFilteringPowerup
from xquotient.mail import MessageSource
from axiom.tags import Catalog
from axiom.scheduler import Scheduler


def createDatabase(s):
    """
    Create a store containing a MailingListFilteringPowerup and its
    dependencies.
    """
    Scheduler(store=s).installOn(s)
    MessageSource(store=s)
    tc = Catalog(store=s)
    rfp = MailingListFilteringPowerup(store=s,
                               tagCatalog=tc).installOn(s)

if __name__ == '__main__':
    saveStub(createDatabase, 10876)
