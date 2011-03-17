// Copyright (c) 2006 Divmod.
// See LICENSE for details.

// Tests for L{Quotient.Message.ActionsModel}

// import Quotient.Message

var ALL_ACTIONS = ['foo', 'bar', 'baz'];

runTests([
    /**
     * Test that all actions are initially disabled
     */
    function test_initiallyDisabled() {
        var model = Quotient.Message.ActionsModel(ALL_ACTIONS);

        failIf(model.isActionEnabled('foo'));
        failIf(model.isActionEnabled('bar'));
        failIf(model.isActionEnabled('baz'));
    },

    /**
     * Test that actions can be enabled
     */
    function test_enable() {
        var model = Quotient.Message.ActionsModel(ALL_ACTIONS);

        model.enableAction('foo');
        failUnless(model.isActionEnabled('foo'));

        failIf(model.isActionEnabled('bar'));
        failIf(model.isActionEnabled('baz'));
    },

    /**
     * Test that actions can be disabled
     */
    function test_disable() {
        var model = Quotient.Message.ActionsModel(ALL_ACTIONS);

        model.enableAction('foo');
        model.disableAction('foo');

        failIf(model.isActionEnabled('foo'));
        failIf(model.isActionEnabled('bar'));
        failIf(model.isActionEnabled('baz'));
    },

    /**
     * Test that some subset of actions can be enabled at once
     */
    function test_enableOnly() {
        var model = Quotient.Message.ActionsModel(ALL_ACTIONS);
        model.enableOnlyActions(['foo', 'bar']);

        failUnless(model.isActionEnabled('foo'));
        failUnless(model.isActionEnabled('bar'));

        failIf(model.isActionEnabled('baz'));
        failIf(model.isActionEnabled('qux'));
        failIf(model.isActionEnabled('quux'));
    },

    /**
     * Test that when a group of actions are enabled, previously enabled
     * actions not in that group are disabled
     */
    function test_enableOnlyDisablesOthers() {
        var model = Quotient.Message.ActionsModel(ALL_ACTIONS);

        model.enableAction('foo');
        model.enableOnlyActions(['bar', 'baz']);

        failUnless(model.isActionEnabled('bar'));
        failUnless(model.isActionEnabled('baz'));

        failIf(model.isActionEnabled('foo'));
    },

    /**
     * Test that we can get a list of the currently enabled actions, when
     * there is only one
     */
    function test_enabledActionsSingle() {
        var model = Quotient.Message.ActionsModel(ALL_ACTIONS);
        model.enableAction('foo');
        assertArraysEqual(model.getEnabledActions(), ['foo']);
    },

    /**
     * Test that we can get a list of the currently enabled actions, when
     * there is more than one
     */
    function test_enabledActionsMany() {
        var model = Quotient.Message.ActionsModel(ALL_ACTIONS);
        model.enableOnlyActions(['foo', 'bar']);
        assertArraysEqual(model.getEnabledActions(), ['foo', 'bar']);
    },

    /**
     * Test action dispatch
     */
    function test_actionDispatch() {
        var model = Quotient.Message.ActionsModel(ALL_ACTIONS),
            called = 0,
            handler = function() {
                called++;
            },
            listener = {messageAction_foo: handler};

        model.setActionListener(listener);
        assertEqual(called, 0);
        model.dispatchAction('foo');
        assertEqual(called, 1);
    },

    /**
     * Test action dispatch with extra arguments
     */
    function test_actionDispatchArgs() {
        var model = Quotient.Message.ActionsModel(ALL_ACTIONS),
            gotArgs,
            handler = function(x, y) {
                gotArgs = [x, y];
            },
            listener = {messageAction_foo: handler};

        model.setActionListener(listener);
        model.dispatchAction('foo', [1, 2]);
        assertArraysEqual(gotArgs, [1, 2]);
    }]);
