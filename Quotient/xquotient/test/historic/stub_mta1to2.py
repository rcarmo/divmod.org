# -*- test-case-name: xquotient.test.historic.test_mta1to2 -*-

"""
Create stub database for upgrade of L{xquotient.mail.MailTransferAgent} from
version 1 to version 2.
"""

from axiom.test.historic.stubloader import saveStub

from axiom.scheduler import Scheduler, SubScheduler
from axiom.userbase import LoginSystem

from xquotient.mail import MailTransferAgent


def createDatabase(s):
    """
    Create an account in the given store and install a MailTransferAgent on
    both the given store and the substore for that account.
    """
    Scheduler(store=s).installOn(s)

    loginSystem = LoginSystem(store=s)
    loginSystem.installOn(s)

    mta = MailTransferAgent(store=s)
    mta.installOn(s)

    account = loginSystem.addAccount(u'testuser', u'localhost', None)
    subStore = account.avatars.open()
    SubScheduler(store=subStore).installOn(subStore)
    mda = MailTransferAgent(store=subStore)
    mda.installOn(subStore)



if __name__ == '__main__':
    saveStub(createDatabase, 7485)
