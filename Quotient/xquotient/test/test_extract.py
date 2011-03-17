import re

from twisted.trial.unittest import TestCase

from axiom.item import Item
from axiom import attributes
from axiom.store import Store

from xquotient import extract, exmess

class SimplePart(Item):
    myText = attributes.text()

    def getTypedParts(self, type):
        return [self]

    def getUnicodeBody(self):
        return self.myText

class ExtractTestCase(TestCase):
    def testExtraction(self):
        s = Store()
        part = SimplePart(store=s, myText=u'this is simple text')
        mesg = exmess.Message(store=s, impl=part)

        origRegex = extract.EmailAddressExtract.regex

        try:
            extract.EmailAddressExtract.regex = re.compile('simple')
            extract.EmailAddressExtract.extract(mesg)

            (theExtract,) = list(s.query(extract.EmailAddressExtract))
            def checkExtract(e):
                self.assertEqual(e.text, 'simple')
                self.assertEqual('this is simple text'[e.start:e.end], 'simple')
                self.assertIdentical(e.message, mesg)
            checkExtract(theExtract)

            # and again
            extract.EmailAddressExtract.extract(mesg)
            (theSameExtract,) = list(s.query(extract.EmailAddressExtract))

            self.assertIdentical(theExtract, theSameExtract)
            checkExtract(theSameExtract)

            extract.EmailAddressExtract.regex = re.compile('complicated')
            part = SimplePart(store=s, myText=u'life is complicated')
            mesg2 = exmess.Message(store=s, impl=part)

            extract.EmailAddressExtract.extract(mesg2)
            (theOldExtract, theNewExtract) = list(s.query(extract.EmailAddressExtract,
                                                          sort=extract.EmailAddressExtract.timestamp.asc))
            checkExtract(theOldExtract)
            self.assertEqual(theNewExtract.text, 'complicated')
            self.assertEqual('life is complicated'[theNewExtract.start:theNewExtract.end], 'complicated')
            self.assertIdentical(theNewExtract.message, mesg2)
        finally:
            extract.EmailAddressExtract.regex = origRegex
