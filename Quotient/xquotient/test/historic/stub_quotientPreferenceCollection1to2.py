from axiom.test.historic.stubloader import saveStub

from xmantissa.prefs import PreferenceAggregator
from xquotient.quotientapp import QuotientPreferenceCollection

def createDatabase(s):
    PreferenceAggregator(store=s).installOn(s)
    QuotientPreferenceCollection(store=s,
                                 preferredMimeType=u'image/png',
                                 preferredMessageDisplay=u'invisible',
                                 showRead=False)

if __name__ == '__main__':
    saveStub(createDatabase, 7860)
