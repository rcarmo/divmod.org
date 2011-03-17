// -*- test-case-name: xmantissa.test.test_javascript -*-
// Copyright (c) 2006 Divmod.
// See LICENSE for details.

// import Divmod.UnitTest
// import Mantissa.AutoComplete


Mantissa.Test.TestAutoComplete.KEYCODE_TAB = 9;
Mantissa.Test.TestAutoComplete.KEYCODE_ENTER = 13;
Mantissa.Test.TestAutoComplete.KEYCODE_UP = 38;
Mantissa.Test.TestAutoComplete.KEYCODE_DOWN = 40;
Mantissa.Test.TestAutoComplete.KEYCODE_ALNUM = 0;

Mantissa.Test.TestAutoComplete.AutoCompleteTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestAutoComplete.AutoCompleteTests');
Mantissa.Test.TestAutoComplete.AutoCompleteTests.methods(
    /**
     * Make a L{Mantissa.AutoComplete.Model} with some completions and a
     * L{Mantissa.AutoComplete.Controller}
     */
    function setUp(self) {
        self.model = Mantissa.AutoComplete.Model(
            ['a', 'aaa', 'aaab', 'abba', 'abracadabra', 'zoop']);
        self.view = Mantissa.Test.TestAutoComplete.MockAutoCompleteView();

        self.controller = Mantissa.AutoComplete.Controller(
            self.model, self.view,
            function(f, when) {
                f();
            });
    },

    /**
     * Make something which looks a little bit like an event object a browser
     * might construct in response to a keypress event
     *
     * @param keyCode: code of the key that was pressed.  C{_KEYCODE_ALNUM},
     * C{_KEYCODE_UP}, C{_KEYCODE_DOWN}, C{_KEYCODE_TAB} and C{_KEYCODE_ENTER} are
     * the interesting ones
     * @type keyCode: C{Number}
     *
     * @rtype: C{Object}
     */
    function makeKeypressEvent(self, keyCode) {
        return {keyCode: keyCode};
    },

    /**
     * Test L{Mantissa.AutoComplete.Model.complete}
     */
    function test_modelCompletion(self) {
        assertArraysEqual(self.model.complete('ab'), ['abba', 'abracadabra']);
        assertArraysEqual(self.model.complete('zoop'), ['zoop']);
        assertArraysEqual(self.model.complete('zap!'), []);
    },

    /**
     * Test that L{Mantissa.AutoComplete.Model.complete} doesn't think the
     * empty string has any completions
     */
    function test_modelCompletionEmpty(self) {
        assertArraysEqual(self.model.complete(''), []);
    },

    /**
     * Test L{Mantissa.AutoComplete.Model.complete} when the string it is
     * passed is comma-separated
     */
    function test_modelCompletionCSV(self) {
        assertArraysEqual(self.model.complete('zz,yy,   aa'), ['aaa', 'aaab']);
        assertArraysEqual(self.model.complete(', aa'), ['aaa', 'aaab']);
        assertArraysEqual(self.model.complete('zoop, zoo'), ['zoop']);
    },

    /**
     * Test L{Mantissa.AutoComplete.Model.appendCompletion}
     */
    function test_modelAppendCompletion(self) {
        assertEqual(self.model.appendCompletion('a, b, cra', 'crabapple'),
                    'a, b, crabapple, ');
        assertEqual(self.model.appendCompletion('cra', 'crab!'), 'crab!, ');
    },

    /**
     * Test L{Mantissa.AutoComplete.Model.isCompletion}
     */
    function test_modelIsCompletion(self) {
        assert(self.model.isCompletion('foo', 'foooo'));
        assert(self.model.isCompletion('f', 'f'));
        assert(self.model.isCompletion('ab', 'abba'));
    },

    /**
     * Test L{Mantissa.AutoComplete.Model.isCompletion}, when the things we
     * pass it are not completions
     */
    function test_modelIsCompletionNeg(self) {
        assert(!self.model.isCompletion('foobar', 'foo'));
        assert(!self.model.isCompletion('f', 'g'));
        assert(!self.model.isCompletion('zao', 'zo'));
    },

    /**
     * Test L{Mantissa.AutoComplete.Controller} and its model/view
     * interactions by telling it to find out about completions for the
     * contents of our imaginary textbox.
     */
    function test_alnumKeypressWithCompletions(self) {
        var keypressListener = self.view.keypressListener;
        var keypressEvent = self.makeKeypressEvent(
            Mantissa.Test.TestAutoComplete.KEYCODE_ALNUM);

        self.view.setValue('abb');
        keypressListener(keypressEvent);

        assertArraysEqual(self.view.visibleCompletions, ['abba']);
        assertEqual(self.view.theSelectedCompletion, 0);
    },

    /**
     * Test that L{Mantissa.AutoComplete.Controller}'s keypress event handler
     * correctly interprets up/down keypresses as hints that the selection
     * should be moved up/down
     */
    function test_completionNavigation(self) {
        var keypressListener = self.view.keypressListener;

        self.view.setValue('a');
        keypressListener(self.makeKeypressEvent(
            Mantissa.Test.TestAutoComplete.KEYCODE_ALNUM));

        assertEqual(self.view.visibleCompletions.length, 5);
        assertEqual(self.view.theSelectedCompletion, 0);

        keypressListener(self.makeKeypressEvent(
            Mantissa.Test.TestAutoComplete.KEYCODE_DOWN));
        assertEqual(self.view.theSelectedCompletion, 1);

        keypressListener(self.makeKeypressEvent(
            Mantissa.Test.TestAutoComplete.KEYCODE_UP));
        assertEqual(self.view.theSelectedCompletion, 0);
    },

    /**
     * Test that L{Mantissa.AutoComplete.View.moveSelectionUp} and
     * L{Mantissa.AutoComplete.View.moveSelectionDown} correctly wrap the
     * selection around
     */
    function test_completionNavigationWraparound(self) {
        var keypressListener = self.view.keypressListener;

        self.view.setValue('a');
        keypressListener(self.makeKeypressEvent(
            Mantissa.Test.TestAutoComplete.KEYCODE_ALNUM));

        keypressListener(self.makeKeypressEvent(
            Mantissa.Test.TestAutoComplete.KEYCODE_UP));
        assertEqual(self.view.theSelectedCompletion, 4);

        keypressListener(self.makeKeypressEvent(
            Mantissa.Test.TestAutoComplete.KEYCODE_DOWN));
        assertEqual(self.view.theSelectedCompletion, 0);
    },

    /**
     * Test that L{Mantissa.AutoComplete.Controller} understands that ENTER
     * means we'd like to have the currently selected completion spliced onto
     * the current value of the view's imaginary textbox
     */
    function test_completionSelection(self) {
        var keypressListener = self.view.keypressListener;

        self.view.setValue('z');
        keypressListener(self.makeKeypressEvent(
            Mantissa.Test.TestAutoComplete.KEYCODE_ALNUM));

        assertArraysEqual(self.view.visibleCompletions, ['zoop']);

        keypressListener(self.makeKeypressEvent(
            Mantissa.Test.TestAutoComplete.KEYCODE_ENTER));

        assertEqual(self.view.getValue(), 'zoop, ');
        assertArraysEqual(self.view.visibleCompletions, []);
    });

/**
 * L{Mantissa.AutoComplete.View} subclass which doesn't depend on the presence
 * of any DOM functionality
 *
 * @ivar visibleCompletions: list of completions that would be being presented
 * to the user, if this was a real thing
 *
 * @ivar theSelectedCompletion: offset of the currently selected completion in
 * the completions list.  might be C{null} if nothing is selected
 *
 * @ivar keypressListener: function which the controller asked us to hook up
 * to keypress events
 */
Mantissa.Test.TestAutoComplete.MockAutoCompleteView = Mantissa.AutoComplete.View.subclass(
    'Mantissa.Test.TestAutoComplete.MockAutoCompleteView');
Mantissa.Test.TestAutoComplete.MockAutoCompleteView.methods(
    function __init__(self) {
        self._displayingCompletions = false;
        self._value = null;
        self.visibleCompletions = [];
        self.theSelectedCompletion = null;

        Mantissa.Test.TestAutoComplete.MockAutoCompleteView.upcall(
            self, '__init__', null, null);
    },

    /**
     * Override default implementation to store the function we get in an
     * instance variable, because there isn't any DOM node to attach it do
     */
    function hookupKeypressListener(self, f) {
        self.keypressListener = f;
    },

    /**
     * Override default implementation to store the value in an instance
     * variable, because there isn't any DOM node to stick it in
     */
    function setValue(self, v) {
        self._value = v;
    },

    /**
     * Override default implementation to return whatever the last thing
     * passed to L{setValue} was
     */
    function getValue(self) {
        return self._value;
    },

    /**
     * Override the default implementation to count the number of entries in
     * C{self.visibleCompletions}, instead of doing DOM stuff
     */
    function completionCount(self) {
        return self.visibleCompletions.length;
    },

    /**
     * Override default implementation to instead inspect our explicitly
     * managed display state
     */
    function displayingCompletions(self) {
        return self._displayingCompletions;
    },

    /**
     * Override default implementation to fiddle the appropriate instance
     * variables
     */
    function showCompletions(self, completions) {
        self.visibleCompletions = completions;
        self.theSelectedCompletion = 0;
        self._displayingCompletions = true;
    },

    /**
     * Again, override default implementation to store the value we get in an
     * instance variable for inspection
     */
    function _selectCompletion(self, offset) {
        self.theSelectedCompletion = offset;
    },

    /**
     * Override default implementation to remove DOM dependencies
     */
    function selectedCompletion(self) {
        return {offset: self.theSelectedCompletion,
                value: self.visibleCompletions[self.theSelectedCompletion]};
    },

    /**
     * Override default implementation to remove DOM dependencies
     */
    function emptyAndHideCompletions(self) {
        self.visibleCompletions = [];
        self.theSelectedCompletion = null;
        self._displayingCompletions = false;
    });
