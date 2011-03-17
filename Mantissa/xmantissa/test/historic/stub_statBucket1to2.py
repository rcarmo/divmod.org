
from axiom.test.historic.stubloader import saveStub

from xmantissa.stats import StatBucket

def createDatabase(s):
    StatBucket(store=s,
               type=u"_axiom_query:select 1")
    StatBucket(store=s,
               type=u"axiom_commits")

if __name__ == '__main__':
    saveStub(createDatabase, 7071)
