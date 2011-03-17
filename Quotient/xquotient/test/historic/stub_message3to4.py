
from axiom.test.historic.stubloader import saveStub

from xquotient.mimestorage import IncomingMIMEMessageStorer

template = """From: bob@b.example.com
To: alice@a.example.com
Subject: message number %d

This is the body of the message.
"""

def createDatabase(s):
    """
    Create a database containing several messages of various kinds.
    """
    # This is more of an integration test than previous upgrade tests for
    # message, because I am concerned with creating a realistic database, since
    # there are a number of nonsensical configurations which we are not
    # concerned about upgrading. --glyph
    messages = []
    for x in range(8):
        mms = IncomingMIMEMessageStorer(
            s, s.newFile("mail", "%d.eml" % (x,)),
            u'migration://migration')
        for line in (template % x).splitlines():
            mms.lineReceived(line)
        # Previously there was no notion of a separate initial 'draft' state
        # since everything was done with flags: messageDone was always called.
        mms.messageDone()
        messages.append(mms.message)

    # Something in the inbox
    messages[0].spam = False

    # Something in the archive
    messages[1].spam = False
    messages[1].archived = True
    # It used to be Deferred
    messages[1].everDeferred = True

    # Something currently deferred
    messages[2].spam = False
    messages[2].archived = False
    messages[2].everDeferred = True
    messages[2].deferred = True
    # It was read
    messages[2].read = True

    # Something that was sent
    messages[3].outgoing = True

    # A draft
    messages[4].outgoing = True
    messages[4].draft = True

    # Something in the trash
    messages[5].spam = False
    messages[5].trash = True

    # spam+trash
    messages[6].spam = True
    messages[6].trash = True

    # some spam
    messages[7].spam = True


if __name__ == '__main__':
    saveStub(createDatabase, 10089)
