# -*- test-case-name: xquotient.test.historic.test_filter1to2 -*-

from axiom.test.historic.stubloader import saveStub
from axiom.scheduler import Scheduler

from xquotient.mail import MessageSource
from xquotient.spam import Filter

def createDatabase(s):
    Scheduler(store=s).installOn(s)
    MessageSource(store=s)
    Filter(store=s).installOn(s)

if __name__ == '__main__':
    saveStub(createDatabase, 8041)
