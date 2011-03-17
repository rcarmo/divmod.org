// -*- test-case-name: xmantissa.test.test_javascript -*-
// Copyright (c) 2007 Divmod.
// See LICENSE for details.

// import Divmod.UnitTest
// import Mantissa.Offering

/**
 * Tests for L{Mantissa.Offering}.
 */
Mantissa.Test.TestOffering.OfferingTestCase = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestOffering.OfferingTestCase');
Mantissa.Test.TestOffering.OfferingTestCase.methods(


    /**
     * Create an L{Mantissa.Offering.UninstalledOffering} for use by test methods.
     */
    function setUp(self) {
	self.node = document.createElement('span');
        self.node.id = 'athena:123'; self.node.className = 'uninstalled';
        document.body.appendChild(self.node);
        self.uninstalledOffering = Mantissa.Offering.UninstalledOffering(self.node);
    },


    /**
     * L{Mantissa.Offering.UninstalledOffering.notify} should add the message to
     * the document, and remove it again.
     *
     * XXX: should switch to something like twisted.internet.task.Clock instead
     * of stubbing callLater
     */
    function test_notify(self) {
        // intercept callLater
        var _callLater = [];
        self.uninstalledOffering.callLater = function (delay, thunk) {
            _callLater.push({delay: delay, thunk: thunk});
        };

        var message = 'floop', className = 'bloop', duration = 5;

        // XXX: errs on the side of strictness
        function messageInDocument() {
            var found = false;
            Divmod.Runtime.theRuntime.traverse(document.body, function (node) {
                if (node.nodeValue === message) {
                    found = true;
                    self.assertIdentical(node.parentNode.className, className)
                    return Divmod.Runtime.Platform.DOM_TERMINATE;
                }
                return Divmod.Runtime.Platform.DOM_DESCEND;
            });
            return found;
        };

        self.uninstalledOffering.notify(message, className, duration);
        self.assert(messageInDocument(),
                    'message should be in document after notify');

        self.assertIdentical(_callLater.length, 1);
        self.assertIdentical(_callLater[0].delay, duration);
        _callLater[0].thunk();
        self.assert(!messageInDocument(),
                    'message should not be in document after duration');
    },


    /**
     * L{Mantissa.Offering.UninstalledOffering.install} should call the remote
     * install and reflect what happens.
     */
    function test_install(self) {
        // interception
        var _callRemote = [];
        self.uninstalledOffering.callRemote = function (methodName, configuration) {
            var result = Divmod.Defer.Deferred();
            _callRemote.push({methodName: methodName, result: result});
            return result;
        };
        var _notify = [];
        self.uninstalledOffering.notify = function (message) {
            _notify.push({message: message});
        };

        // test helpers
        function assertNodeState(className, clickable) {
            self.assertIdentical(self.node.className, className);
            self.assert((self.node.onclick === null) != clickable,
                        'offering should be '+(clickable?'':'non-')+'clickable');
        };
        function callInstall() {
            assertNodeState('uninstalled', true);
            self.uninstalledOffering.install();
            assertNodeState('installing', true);
            self.assertIdentical(_callRemote.length, 1);
            self.assertIdentical(_callRemote[0].methodName, 'install');
            return _callRemote.pop().result;
        };
        function checkNotify() {
            self.assertIdentical(_notify.length, 1);
            self.assert(typeof _notify[0].message === 'string',
                        'non-string notification: ' + _notify[0].message);
            return _notify.pop().message;
        };


        // 1. Installation failure
        var remote = callInstall();
        remote.errback(Divmod.Defer.Failure('Denied!'));
        var message = checkNotify();
        self.assert(0 <= message.indexOf('Denied!'),
                    'notification should contain failure message');

        // 2. Installation success
        var remote = callInstall();
        remote.callback(null);
        checkNotify();
        assertNodeState('installed', false);
    },


    /**
     * XXX TODO: Remove this once the test harness handles teardown.
     */
    function tearDown(self) {
        delete self.uninstalledOffering;
        document.body.removeChild(self.node);
    }

);
