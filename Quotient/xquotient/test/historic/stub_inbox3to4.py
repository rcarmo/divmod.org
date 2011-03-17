# -*- test-case-name: xquotient.test.historic.test_inbox3to4 -*-

"""
Create a stub database for upgrade of L{xquotient.inbox.Inbox} from version 3
to version 4.
"""

from axiom.test.historic.stubloader import saveStub
from axiom import scheduler
from xmantissa import website, webapp
from xquotient.quotientapp import QuotientPreferenceCollection, MessageDisplayPreferenceCollection
from xquotient import inbox, mail

def createDatabase(s):
    s.findOrCreate(scheduler.SubScheduler).installOn(s)
    s.findOrCreate(website.WebSite).installOn(s)
    s.findOrCreate(webapp.PrivateApplication).installOn(s)

    s.findOrCreate(mail.DeliveryAgent).installOn(s)

    s.findOrCreate(mail.MessageSource)

    s.findOrCreate(QuotientPreferenceCollection).installOn(s)
    s.findOrCreate(MessageDisplayPreferenceCollection).installOn(s)
    s.findOrCreate(inbox.Inbox, uiComplexity=2, showMoreDetail=True).installOn(s)

if __name__ == '__main__':
    saveStub(createDatabase, 11096)
