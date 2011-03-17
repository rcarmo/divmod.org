# -*- test-case-name: xmantissa.test.historic.test_messagequeue1to2 -*-

from axiom.test.historic.stubloader import saveStub

from axiom.dependency import installOn

from xmantissa.interstore import MessageQueue

MESSAGE_COUNT = 17

def createDatabase(store):
    installOn(MessageQueue(store=store, messageCounter=MESSAGE_COUNT), store)

if __name__ == '__main__':
    saveStub(createDatabase, 17606)
