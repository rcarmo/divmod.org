from axiom.test.historic.stubloader import saveStub

from epsilon.extime import Time

from xquotient.exmess import Message
from xquotient.mimestorage import Part

from xquotient.test.historic.stub_message1to2 import attrs

def createDatabase(s):
    Message(store=s,
            impl=Part(store=s),
            **attrs)

if __name__ == '__main__':
    saveStub(createDatabase, 7212)
