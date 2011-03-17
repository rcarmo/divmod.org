# -*- test-case-name: xquotient.test.historic.test_rulefilter1to2 -*-
"""
Create a store with a RuleFilteringPowerup and its dependencies in it.
"""
from axiom.test.historic.stubloader import saveStub
from xquotient.filter import RuleFilteringPowerup
from axiom.tags import Catalog
from xquotient.mail import MessageSource
from axiom.scheduler import Scheduler

def createDatabase(s):
    Scheduler(store=s).installOn(s)
    MessageSource(store=s)
    tc = Catalog(store=s)
    rfp = RuleFilteringPowerup(store=s,
                               tagCatalog=tc).installOn(s)

if __name__ == '__main__':
    saveStub(createDatabase, 10876)
