# -*- test-case-name: xquotient.test.historic.test_mta2to3 -*-

"""
Create stub database for upgrade of L{xquotient.mail.MailTransferAgent} from
version 2 to 3.
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
    loginSystem = LoginSystem(store=s)
    loginSystem.installOn(s)

    mta = MailTransferAgent(store=s)
    mta.installOn(s)


if __name__ == '__main__':
    saveStub(createDatabase, 10876)
