
import itertools
from datetime import timedelta

from twisted.python.filepath import FilePath

from xquotient.iquotient import IMIMEDelivery
from xquotient.exmess import Message
from xquotient.benchmarks.benchmark_initialize import initializeStore
from xquotient.inbox import Inbox

N_LOOPS = 20
N_MESSAGES = 10000
N_LOOKUPS = 100

VIEWS = ('Trash', 'All', 'Sent', 'Spam')

def createInboxWithManyMessages():
    siteStore, userStore = initializeStore()

    # Deliver one message by way of the MIME parser.
    delivery = IMIMEDelivery(userStore)
    receiver = delivery.createMIMEReceiver(u'benchmark_nextmsg')
    receiver.feedFileNow(
        FilePath(__file__).sibling('messages').child(
            'Domain registration order #1487387.eml').open())
    message = receiver.message

    flags = itertools.cycle([
            [False, False, False, False, False],
            [True, False, False, False, False],
            [False, True, False, False, False],
            [False, False, True, False, False],
            [False, False, False, True, False],
            [False, False, False, False, True]])

    # Now make a ton of new Message objects and re-use the same implementation
    # object for each of them (otherwise this would take a month to finish).
    def deliverSome():
        read, archived, trash, deferred, spam = flags.next()
        for i in xrange(N_MESSAGES):
            Message(
                store=userStore,
#                 source=message.source,
#                 sentWhen=message.sentWhen + timedelta(seconds=i),
                receivedWhen=message.receivedWhen + timedelta(seconds=i),
#                 sender=message.sender,
#                 senderDisplay=message.senderDisplay,
#                 recipient=message.recipient,
#                 subject=message.subject,
#                 attachments=message.attachments,
                read=read,
                archived=archived,
                trash=trash,
                deferred=deferred,
                spam=False,
#                 trained=message.trained,
#                 impl=message.impl
                )
    for i in xrange(N_LOOPS):
        userStore.transact(deliverSome)


    # Setup is complete: there are a ton of messages in the database.  Now do
    # some stuff with an Inbox object.
    inbox = userStore.findUnique(Inbox)

    return inbox
