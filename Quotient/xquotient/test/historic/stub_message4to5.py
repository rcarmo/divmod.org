
from axiom.dependency import installOn
from axiom.scheduler import SubScheduler
from axiom.test.historic.stubloader import saveStub

from xquotient.mimestorage import IncomingMIMEMessageStorer
from datetime import timedelta

template = """From: bob@b.example.com
To: alice@a.example.com
Subject: message number %(index)d
Date: Thu, 26 Apr 2001 22:01:%(index)02d GMT

This is the body of the message.
"""

def createDatabase(s):
    """
    Create a database containing several messages of various kinds.
    """
    installOn(SubScheduler(store=s), s)
    messages = []
    for x in range(8):
        mms = IncomingMIMEMessageStorer(
            s, s.newFile("mail", "%d.eml" % (x,)),
            u'migration://migration',
            draft = (x == 3 or x == 4))
        for line in (template % {'index': x}).splitlines():
            mms.lineReceived(line)
        mms.messageDone()
        mms.message.attachments = x * 2
        messages.append(mms.message)
    messages[0].classifyClean()

    messages[1].classifyClean()
    messages[1].deferFor(timedelta(days=10))
    messages[1].undefer()
    messages[1].archive()

    messages[2].classifyClean()
    messages[2].deferFor(timedelta(days=10))
    messages[2].markRead()

    # this one was sent (see above for entering the draft status)
    messages[3].startedSending()
    messages[3].sent()
    messages[3].finishedSending()

    # message 4 is a draft by default, we don't need to push it further through
    # the workflow.

    messages[5].classifyClean()
    messages[5].moveToTrash()

    messages[6].classifySpam()
    messages[6].moveToTrash()

    messages[7].classifySpam()
    messages[7].trainSpam()


if __name__ == '__main__':
    saveStub(createDatabase, 11812)
