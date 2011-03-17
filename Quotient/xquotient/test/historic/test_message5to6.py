"""
Tests for re-parsing certain incorrect message structures (namely, multipart
messages with parts whose content-type contained the string 'message/rfc822;').

"""
from axiom.test.historic.stubloader import StubbedTest
from xquotient.exmess import Message

class MessageUpgradeTest(StubbedTest):


    def test_messageParsing(self):
        """
        Check that subparts of message/rfc822 parts are included in the message
        structure now.
        """
        msg = self.store.findUnique(Message)
        parts = list(msg.impl.walk())
        self.assertEqual(len(parts), 6)
        types = [(p.getHeader("content-type").split(';', 1)[0]
                  .lower().strip().encode('ascii'))
                 for p in parts]
        self.assertEqual(types,
                         ['multipart/mixed', 'text/plain',
                          'message/rfc822', 'multipart/mixed',
                          'text/plain', 'image/jpeg'])


