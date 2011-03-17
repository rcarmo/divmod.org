from axiom.test.historic.stubloader import saveStub

from epsilon.extime import Time

from xquotient.exmess import Message
from xquotient.mimestorage import Part

attrs = dict(sender=u'foo@bar.baz',
             subject=u'This is a spam',
             recipient=u'baz@bar.foo',
             senderDisplay=u'Spammer',
             spam=True,
             archived=False,
             trash=True,
             outgoing=False,
             draft=False,
             trained=True,
             read=True,
             attachments=23,
             sentWhen=Time.fromPOSIXTimestamp(123),
             receivedWhen=Time.fromPOSIXTimestamp(456))

def createDatabase(s):
    Message(store=s,
            impl=Part(store=s),
            **attrs)

if __name__ == '__main__':
    saveStub(createDatabase, 7105)
