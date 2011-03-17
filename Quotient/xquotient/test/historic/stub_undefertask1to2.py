from datetime import timedelta

from zope.interface import implements

from epsilon.extime import Time

from axiom.iaxiom import IScheduler
from axiom.item import Item
from axiom.attributes import inmemory, integer, text
from axiom.test.historic.stubloader import saveStub

from xquotient.iquotient import IMessageData
from xquotient.exmess import Message, SENDER_RELATION, RECIPIENT_RELATION
from xquotient.mimeutil import EmailAddress
from xquotient.test.test_workflow import DummyMessageImplementation



SCHEDULE_LOG = []


class FakeScheduler(Item):
    # XXX - copied from xquotient.test.test_workflow
    """
    This is an alternate in-memory axiom IScheduler implementation, provided so
    that we can catch and flush scheduled events in these tests.
    """
    typeName = "stub_undefertask_fake_scheduler"

    ignored = integer()

    implements(IScheduler)


    def schedule(self, runnable, when):
        SCHEDULE_LOG.append(('schedule', runnable))


    def unscheduleAll(self, runnable):
        SCHEDULE_LOG.append(('unschedule', runnable))



def createDatabase(s):
    """
    Populate the given Store with a deferred message.
    """
    messageData = DummyMessageImplementation(store=s)
    fakeScheduler = FakeScheduler(store=s)
    s.powerUp(fakeScheduler, IScheduler)
    m = Message.createIncoming(s, messageData, u'test')
    m.classifyClean()
    m.markRead()
    now = Time()
    m.deferFor(timedelta(days=1), timeFactory=lambda: now)



if __name__ == '__main__':
    saveStub(createDatabase, 10588)
