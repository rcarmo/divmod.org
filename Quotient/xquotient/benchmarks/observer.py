
"""
Miscellaneous introspection tools for use by benchmarks, mainly to decide when
the task at hand has completed.
"""

from twisted.internet import reactor

from axiom.item import Item
from axiom.attributes import integer

from xquotient.mail import MessageSource

class StoppingMessageFilter(Item):
    """
    Reliable MessageSource listener which stops the reactor after it sees a
    preset number of messages.
    """
    messageCount = integer(default=0)
    totalMessages = integer(allowNone=False)

    def installOn(self, other):
        self.store.findUnique(MessageSource).addReliableListener(self)


    def processItem(self, item):
        self.messageCount += 1
        if self.messageCount == self.totalMessages:
            reactor.stop()
