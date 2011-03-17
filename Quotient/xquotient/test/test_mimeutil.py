# Copyright 2005 Divmod, Inc.  See LICENSE file for details

from twisted.trial import unittest

from xquotient import mimeutil

class MIMEUtilTests(unittest.TestCase):

    def testheaderToUnicode(self):
        expected = [('=?ISO-8859-1?Q?C=E9sar?=', u'C\u00e9sar', ()),
                    ('=?ISO-8859-1?Q?C=E9sar?= fu bar', u'C\u00e9sar fu bar', ()),
                    ('=?ISO-FUBAR1?Q?C=E9sar?= fu bar', u'C\ufffdr fu bar', ()),
                    ('=?ISO-FUBAR1?Q?C=E9sar?= fu bar', u'C\u00e9sar fu bar', ('iso-8859-1',))]

        for source, expected, args in expected:
            result = mimeutil.headerToUnicode(source, *args)
            self.failUnless(isinstance(result, unicode))
            self.assertEquals(result, expected, "from %r got %r, expected %r" % (source, result, expected))

    dates = [
        ("Wed, 08 Dec 2004 16:44:11 -0500", (2004, 12, 8, 21, 44, 11, 2, 343, 0)),
        ("08 Dec 2004 16:44:11 -0500", (2004, 12, 8, 21, 44, 11, 2, 343, 0)),
        ("8 Dec 2004 16:44:11 -0500", (2004, 12, 8, 21, 44, 11, 2, 343, 0)),
        ("8 Dec 04 16:44:11 -0500", (2004, 12, 8, 21, 44, 11, 2, 343, 0)),
        ("  Wed,    08     Dec    2004      16:44:11     -0500", (2004, 12, 8, 21, 44, 11, 2, 343, 0)),
        ("Wed,08 Dec 2004 16:44:11 -0500", (2004, 12, 8, 21, 44, 11, 2, 343, 0)),
        # implementation doesn't handle comments correctly, but they are now obsoleted
        #("Wed,08 Dec 2004 16(rfc2822 allows):44: (comments all over here)  11 -0500", (2004, 12, 8, 21, 44, 11, 2, 343, 0)),
        ("08 Dec 2004 16:44 -0500", (2004, 12, 8, 21, 44, 0, 2, 343, 0)),
        ("08 Dec 2004 15:44:11 -0600", (2004, 12, 8, 21, 44, 11, 2, 343, 0)),
        ("08 Dec 2004 21:44:11 -0000", (2004, 12, 8, 21, 44, 11, 2, 343, 0)),
        ("08 Dec 2004 21:44:11 +0000", (2004, 12, 8, 21, 44, 11, 2, 343, 0)),
        ("Wed, 08 Dec 2004 16:44:11 EST", (2004, 12, 8, 21, 44, 11, 2, 343, 0)),
        # implementation says it handles military style timezones, but it
        # doesn't. They are obsolete now anyway, and because rfc822 got the
        # sign on them backwards, rfc2822 suggests they all be considered
        # -0000. Whatever.
        #("Wed, 08 Dec 2004 16:44:11 R", (2004, 12, 8, 21, 44, 11, 2, 343, 0)),
        ("Wednesday, 08 Dec 2004 16:44:11 EST", (2004, 12, 8, 21, 44, 11, 2, 343, 0)),
        ]

    def test_formatdate(self):
        for formatted, tuple in self.dates:
            self.assertEquals(mimeutil.parsedate(mimeutil.formatdate(tuple)), tuple)

    def test_parsedate(self):
        for formatted, tuple in self.dates:
            self.assertEquals(mimeutil.parsedate(formatted), tuple)

    def test_parseBadDate(self):
        """Invalid dates return None"""
        self.failUnless(mimeutil.parsedate('invalid date') is None, 'parsedate("invalid date") did not return None')


class EmailAddressTests(unittest.TestCase):
    def test_cmp(self):
        self.assertEquals(mimeutil.EmailAddress('    '), mimeutil.EmailAddress(''))
        self.assertEquals(mimeutil.EmailAddress('Fu@bAr'), mimeutil.EmailAddress('  fu  @ bar  '))
        self.assertEquals(mimeutil.EmailAddress('bleh <Fu@bAr>'), mimeutil.EmailAddress(('  bleh  ', '  fu  @ bar  ')))
        self.assertNotEquals(mimeutil.EmailAddress('bleh <Fu@bAr>'), mimeutil.EmailAddress('  fu  @ bar  '))

    def _parseTestCase(self, input, display, email, anyDisplayName, pseudoFormat, localpart, domain):
        """
        Parse the given input and assert that the attributes of the resulting
        L{mimeutil.EmailAddress} are equal to the given values.
        """
        e = mimeutil.EmailAddress(input)
        self.assertEquals(e.display, display)
        self.failUnless(isinstance(e.display, unicode))
        self.assertEquals(e.email, email)
        self.failUnless(isinstance(e.email, unicode))
        self.assertEquals(e.anyDisplayName(), anyDisplayName)
        self.failUnless(isinstance(e.anyDisplayName(), unicode))
        self.assertEquals(e.pseudoFormat(), pseudoFormat)
        self.failUnless(isinstance(e.pseudoFormat(), unicode))
        self.assertEquals(e.localpart, localpart)
        self.failUnless(isinstance(e.localpart, unicode))
        self.assertEquals(e.domain, domain)
        self.failUnless(isinstance(e.domain, unicode))


    def test_normalString(self):
        """
        Test that a string of the common form, one with a display name and an
        email address, separated by whitespace, parses properly.
        """
        self._parseTestCase(
            input=' SoMe  NaMe   <SoMeNaMe@example.com>',
            display=u'SoMe NaMe',
            email=u'somename@example.com',
            anyDisplayName=u'SoMe NaMe',
            pseudoFormat=u'SoMe NaMe <somename@example.com>',
            localpart=u'somename',
            domain=u'example.com')


    def test_parseTuple(self):
        """
        Test that a two-tuple of a display name and an email address is parsed
        properly.
        """
        self._parseTestCase(
            input=('  SoMe  NaMe  ', 'SoMeNaMe@example.com'),
            display=u'SoMe NaMe',
            email=u'somename@example.com',
            anyDisplayName=u'SoMe NaMe',
            pseudoFormat=u'SoMe NaMe <somename@example.com>',
            localpart=u'somename',
            domain=u'example.com')


    def test_parseUnicodeDisplayName(self):
        """
        Test that a two-tuple of a unicode string giving display name and a
        byte string giving an email address is parsed properly.

        Possibly this is not a desirable feature of this API, but for the time
        being we will test to make sure it works.  Maybe later on we will want
        to deprecate/eliminate it.
        """
        self._parseTestCase(
            input=(u'  SoMe  NaMe  ', 'SoMeNaMe@example.com'),
            display=u'SoMe NaMe',
            email=u'somename@example.com',
            anyDisplayName=u'SoMe NaMe',
            pseudoFormat=u'SoMe NaMe <somename@example.com>',
            localpart=u'somename',
            domain=u'example.com')


    def test_parseUnicodeEmail(self):
        """
        Test that a two-tuple of a byte string giving display name and a
        unicode string giving an email address is parsed properly.

        Possibly this is not a desirable feature of this API, but for the time
        being we will test to make sure it works.  Maybe later on we will want
        to deprecate/eliminate it.
        """
        self._parseTestCase(
            input=('  SoMe  NaMe  ', u'SoMeNaMe@example.com'),
            display=u'SoMe NaMe',
            email=u'somename@example.com',
            anyDisplayName=u'SoMe NaMe',
            pseudoFormat=u'SoMe NaMe <somename@example.com>',
            localpart=u'somename',
            domain=u'example.com')


    def test_parseUnicodeTuple(self):
        """
        Test that a two-tuple of unicode strings giving a display name and an
        email address is parsed properly.

        Possibly this is not a desirable feature of this API, but for the time
        being we will test to make sure it works.  Maybe later on we will want
        to deprecate/eliminate it.
        """
        self._parseTestCase(
            input=(u'  SoMe  NaMe  ', u'SoMeNaMe@example.com'),
            display=u'SoMe NaMe',
            email=u'somename@example.com',
            anyDisplayName=u'SoMe NaMe',
            pseudoFormat=u'SoMe NaMe <somename@example.com>',
            localpart=u'somename',
            domain=u'example.com')


    def test_parseWithoutDisplay(self):
        """
        Test the parsing of an address without a display part.
        """
        self._parseTestCase(
            input=' n o  name  @ examplE.com  ',
            display=u'',
            email=u'noname@example.com',
            anyDisplayName=u'noname@example.com',
            pseudoFormat=u'noname@example.com',
            localpart=u'noname',
            domain=u'example.com')


    def test_emptyAddress(self):
        """
        Test the parsing of pure whitespace.
        """
        self._parseTestCase(
            input='    ',
            display=u'',
            email=u'',
            anyDisplayName=u'Nobody',
            pseudoFormat=u'',
            localpart=u'',
            domain=u'')


    def test_Q(self):
        """
        Test the parsing of an address with MIME Header Q encoded characters in the
        display part. (RFC 2047, Section 4, 4.2)
        """
        self._parseTestCase(
            input='  =?ISO-8859-1?Q?C=E9sar______?= fu   bar  <cesarfubar@example.com>',
            display=u'C\u00e9sar fu bar',
            email=u'cesarfubar@example.com',
            anyDisplayName=u'C\u00e9sar fu bar',
            pseudoFormat=u'C\u00e9sar fu bar <cesarfubar@example.com>',
            localpart=u'cesarfubar',
            domain=u'example.com')


    def test_parseEmailAddresses(self):
        self.assertEquals(
            mimeutil.parseEmailAddresses('  one@t  wo , three <four@five>  '),
            map(mimeutil.EmailAddress, ['one@two', 'three <four@five>']))

    def test_flattenEmailAddresses(self):
        """
        Test that L{xquotient.mimeutil.flattenEmailAddresses} works as
        expected
        """
        self.assertEquals(
            mimeutil.flattenEmailAddresses(
                (mimeutil.EmailAddress('One <one@two>'),
                 mimeutil.EmailAddress('two@three'))),
            'One <one@two>, two@three')

    def test_makeHeader(self):
        e = mimeutil.EmailAddress('  =?ISO-8859-1?Q?C=E9sar______?= fu   bar  <cesarfubar@example.com>')
        header = e.makeHeader('To')
        e2 = mimeutil.EmailAddress(header.encode())
        self.assertEquals(e, e2)

    def test_ListHeader(self):
        emails = []
        emails.append(mimeutil.EmailAddress('  =?ISO-8859-1?Q?C=E9sar______?= fu   bar  <cesarfubar@example.com>'))
        emails.append(mimeutil.EmailAddress(' n o  name  @ examplE.com  '))
        header = mimeutil.makeEmailListHeader(emails, 'To')
        parsed = mimeutil.parseEmailAddresses(header.encode())
        self.assertEquals(emails, parsed)

    def test_nonzero(self):
        self.failIf(mimeutil.EmailAddress(''))
        self.failUnless(mimeutil.EmailAddress('foo@bar'))
        self.failUnless(mimeutil.EmailAddress('baz <foo@bar>'))
        self.failUnless(mimeutil.EmailAddress('baz <>'))
