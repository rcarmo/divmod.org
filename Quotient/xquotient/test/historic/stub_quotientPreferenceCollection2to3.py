from axiom.test.historic.stubloader import saveStub

from xquotient.quotientapp import QuotientPreferenceCollection

def createDatabase(s):
    QuotientPreferenceCollection(store=s,
                                 preferredMimeType=u'image/png',
                                 preferredMessageDisplay=u'invisible',
                                 showRead=False,
                                 showMoreDetail=True)

if __name__ == '__main__':
    saveStub(createDatabase, 8528)
