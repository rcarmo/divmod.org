# Copyright (c) 2006 Divmod.
# See LICENSE for details.

"""
Runs Quotient javascript tests as part of the Quotient python test suite
"""

import sys

from twisted.python.filepath import FilePath
from twisted.python.util import untilConcludes
from twisted.trial.unittest import TestCase
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.error import ProcessTerminated
from twisted.internet.defer import Deferred
from twisted.internet import reactor

from nevow.testutil import setJavascriptInterpreterOrSkip
from nevow.jsutil import generateTestScript

# XXX TODO: Rewrite all of this use Divmod.UnitTest instead.
class _JavaScriptTestSuiteProtocol(ProcessProtocol):
    finished = None

    def connectionMade(self):
        self.out = []
        self.err = []

    def outReceived(self, out):
        untilConcludes(sys.stdout.write, out)
        untilConcludes(sys.stdout.flush)
        self.out.append(out)

    def errReceived(self, err):
        untilConcludes(sys.stdout.write, err)
        untilConcludes(sys.stdout.flush)
        self.err.append(err)

    def processEnded(self, reason):
        if reason.check(ProcessTerminated):
            self.finished.errback(Exception(reason.getErrorMessage(), ''.join(self.out), ''.join(self.err)))
        elif self.err:
            self.finished.errback(Exception(''.join(self.out), ''.join(self.err)))
        else:
            self.finished.callback(''.join(self.out))



class JavaScriptTestSuite(TestCase):
    """
    Inherit from me if you want to run javascript tests

    @ivar path: path to directory containing the javascipt files
    @type path: L{twisted.python.filepath.FilePath}
    """
    javascriptInterpreter = None
    path = None

    def onetest(self, jsfile):
        """
        Test the javascript file C{jsfile}

        @param jsfile: filename
        @type jsfile: C{str}

        @return: deferred that fires when the javascript interpreter process
        terminates
        @rtype: L{twisted.interner.defer.Deferred}
        """
        p = _JavaScriptTestSuiteProtocol()
        d = p.finished = Deferred()

        fname = self.mktemp()
        file(fname, 'w').write(
            generateTestScript(self.path.child(jsfile).path))

        reactor.spawnProcess(
            p,
            self.javascriptInterpreter,
            ("js", fname))

        return d



class QuotientJavaScriptTestSuite(JavaScriptTestSuite):
    """
    Run all the Quotient javascript tests
    """
    path = FilePath(__file__).parent()

    def test_utils(self):
        return self.onetest('test_utils.js')

    def test_messageActions(self):
        return self.onetest('test_messageActions.js')

setJavascriptInterpreterOrSkip(QuotientJavaScriptTestSuite)



from nevow.testutil import JavaScriptTestCase



class JavaScriptTests(JavaScriptTestCase):
    """
    xQuotient Javascript unit tests.
    """
    def test_common(self):
        """
        Tests for C{Quotient.Common}.
        """
        return 'Quotient.Test.TestCommon'


    def test_mailboxController(self):
        """
        Tests for C{Quotient.Mailbox.Controller}.
        """
        return 'Quotient.Test.TestController'
