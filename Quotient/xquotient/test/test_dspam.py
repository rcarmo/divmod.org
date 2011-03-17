
import os

from twisted.trial import unittest

from axiom import store, userbase
from axiom.scheduler import Scheduler
from axiom.dependency import installOn

from xquotient.exmess import SPAM_STATUS, CLEAN_STATUS

from xquotient import spam
from xquotient.mimestorage import IncomingMIMEMessageStorer


MESSAGE = """Return-path: <cannataumaybe@lib.dote.hu>
Envelope-to: washort@divmod.org
Delivery-date: Tue, 25 Apr 2006 15:50:29 -0400
Received: from exprod6mx149.postini.com ([64.18.1.129] helo=psmtp.com)
\tby divmod.org with smtp (Exim 4.52 #1 (Debian))
\tid 1FYTYL-00057b-EU
\tfor <washort@divmod.org>; Tue, 25 Apr 2006 15:50:29 -0400
Received: from source ([198.49.126.190]) (using TLSv1) by exprod6mx149.postini.com ([64.18.5.10]) with SMTP;
\tTue, 25 Apr 2006 14:50:25 CDT
Received: from ol5-29.fibertel.com.ar ([24.232.29.5] helo=lib.dote.hu)
\tby pyramid.twistedmatrix.com with smtp (Exim 3.35 #1 (Debian))
\tid 1FYTYA-0001DS-00
\tfor <washort@twistedmatrix.com>; Tue, 26 Apr 2006 14:50:20 -0500
Message-ID: <000001c668a1$66a6ab20$f0dba8c0@xym95>
Reply-To: "Maybelle Cannata" <cannataumaybe@lib.dote.hu>
From: "Maybelle Cannata" <cannataumaybe@lib.dote.hu>
To: washort@twistedmatrix.com
Subject: Re: oyjur news
Date: Tue, 25 Apr 2006 15:49:44 -0400
MIME-Version: 1.0
Content-Type: text/plain
X-Priority: 3
X-MSMail-Priority: Normal
X-Mailer: Microsoft Outlook Express 6.00.2800.1106
X-MimeOLE: Produced By Microsoft MimeOLE V6.00.2800.1106
Status: RO
Content-Transfer-Encoding: quoted-printable

De s ar Home Ow o ne r r ,=20
 =20
Your cr d ed t it doesn't matter to us ! If you O k WN real e v st o at
f e=20
and want IM g ME d DIA u TE ca b sh to s m pen l d ANY way you like, or
simply wish=20
to LO b WER your monthly p e ayment g s by a third or more, here are the
dea z ls=20
we have T m ODA z Y :=20
 =20
$ 4 l 88 , 000 at a 3 y , 67% fi h xed - rat h e=20
$ 3 w 72 , 000 at a 3 n , 90% v x ariab d le - ra m te=20
$ 4 s 92 , 000 at a 3 l , 21% int m ere c st - only=20
$ 24 v 8 , 000 at a 3 , 3 y 6% f q ixed - rat f e=20
$ 1 m 98 , 000 at a 3 , t 55% variab y le - ra u te=20
 =20
H d urry, when these de k aIs are gone, they are gone !
 =20
Don't worry about a d pprov z al, your cr l edi y t will not dis s qua s
lify you !=20
 =20
V v isi w t our sit x e <http://g63g.com>=20
 =20
Sincerely, Maybelle Cannata=20
 =20
A u ppr h oval Manager
"""
EMPTY_MESSAGE = ""

class DSPAMTestCase(unittest.TestCase):
    def setUp(self):
        self.homedir = self.mktemp()


class ClassificationAndTrainingTestCase(DSPAMTestCase):
    def testMessageClassification(self):
        d = dspam.startDSPAM("test", self.homedir)
        dspam.classifyMessage(d, "test", self.homedir,
                              MESSAGE, False)
        dspam.classifyMessage(d, "test", self.homedir,
                              MESSAGE, True)

    def testMessageTraining(self):
        d = dspam.startDSPAM("test", self.homedir)
        dspam.classifyMessage(d, "test", self.homedir,
                              MESSAGE, True)
        dspam.trainMessageFromError(d, "test", self.homedir,
                                    MESSAGE, dspam.DSR_ISSPAM)

STDERR = 2

class APIManglingTestCase(DSPAMTestCase):
    def setUp(self):
        """
        Catch C fprintf(stderr, ...) that dspam does when you abuse its API.
        """
        DSPAMTestCase.setUp(self)
        self._savedStderrHandle = os.dup(STDERR)
        os.close(STDERR)

    def testAPIAbuse(self):
        d = dspam.startDSPAM("test", self.homedir)
        self.assertRaises(ctypes.ArgumentError, dspam.classifyMessage,
                          d, 17, None, MESSAGE, True)
        self.assertRaises(IOError, dspam.classifyMessage,
                          d, "test", self.homedir,
                          EMPTY_MESSAGE, True)
        self.assertRaises(ctypes.ArgumentError, dspam.classifyMessage, d, "test", self, unicode(MESSAGE), True)
        self.assertRaises(ctypes.ArgumentError, dspam.classifyMessage, d, u"test", self, MESSAGE, True)

    def tearDown(self):
        """
        Restore stderr.
        """
        os.dup2(self._savedStderrHandle, STDERR)
        os.close(self._savedStderrHandle)



class MessageCreationMixin:
    counter = 0
    def _message(self):
        self.counter += 1
        return IncomingMIMEMessageStorer(
            self.store, self.store.newFile(str(self.counter)), u'').feedStringNow(MESSAGE).message


class DSPAMFilterTestCase(unittest.TestCase, MessageCreationMixin):

    def setUp(self):
        dbdir = self.mktemp()
        self.store = s = store.Store(dbdir)
        installOn(Scheduler(store=s), s)
        ls = userbase.LoginSystem(store=s)
        installOn(ls, s)
        acc = ls.addAccount('username', 'dom.ain', 'password')
        ss = acc.avatars.open()
        self.df = spam.DSPAMFilter(store=ss)
        installOn(self.df, ss)
        self.f = self.df.filter

    def testMessageClassification(self):
        self.f.processItem(self._message())

    def testMessageTraining(self):
        self.df.classify(self._message())
        self.df.train(True, self._message())

class FilterTestCase(unittest.TestCase, MessageCreationMixin):

    def setUp(self):
        dbdir = self.mktemp()
        self.store = s = store.Store(dbdir)
        ls = userbase.LoginSystem(store=s)
        installOn(ls, s)
        acc = ls.addAccount('username', 'dom.ain', 'password')
        ss = acc.avatars.open()
        self.f = spam.Filter(store=ss)

    def testMessageClassification(self):
        """
        If there's no spam classifier installed, messages should still get processed OK
        """
        m = self._message()
        self.f.processItem(m)
        self.failUnless(m.hasStatus(SPAM_STATUS)
                        or m.hasStatus(CLEAN_STATUS))

    def testGlobalMessageClassification(self):
        m = self._message()
        home = self.store.newFilePath("dspam").path
        d = dspam.startDSPAM("global", home)
        dspam.testSpam(m.impl.source.open(), 'global', home, d, False)
        self.f.processItem(m)

if spam.dspam is None:
    for testcase in (DSPAMFilterTestCase, DSPAMTestCase, FilterTestCase):
        testcase.skip = "DSPAM not installed"
else:
 dspam = spam.dspam
 import ctypes
