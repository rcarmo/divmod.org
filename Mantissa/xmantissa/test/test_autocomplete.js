// Copyright (c) 2006 Divmod.
// See LICENSE for details.

// import Mantissa.AutoComplete

/**
 * Make a L{Mantissa.AutoComplete.Model} with some completions
 */
function makeModel() {
    return Mantissa.AutoComplete.Model(
            ['a', 'aaa', 'aaab', 'abba', 'abracadabra', 'zoop']);
}

var _KEYCODE_TAB = 9,
    _KEYCODE_ENTER = 13,
    _KEYCODE_UP = 38,
    _KEYCODE_DOWN = 40,
    _KEYCODE_ALNUM = 0;

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
function makeKeypressEvent(keyCode) {
    return {keyCode: keyCode};
}

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
var MockAutoCompleteView = Mantissa.AutoComplete.View.subclass('MockAutoCompleteView');
MockAutoCompleteView.methods(
    function __init__(self) {
        self._displayingCompletions = false;
        self._value = null;
        self.visibleCompletions = [];
        self.theSelectedCompletion = null;

        MockAutoCompleteView.upcall(self, '__init__', null, null);
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

/**
 * Make a L{Mantissa.AutoComplete.Controller} with a
 * L{Mantissa.AutoComplete.Model}, as obtained from L{makeModel}, and a
 * L{MockAutoCompleteView}
 *
 * @rype: L{Mantissa.AutoComplete.Controller}
 */
function makeController() {
    var view = MockAutoCompleteView(),
        model = makeModel();

    return Mantissa.AutoComplete.Controller(model, view,
            function(f, when) {
                f();
            });
}

runTests([
    /**
     * Test L{Mantissa.AutoComplete.Model.complete}
     */
    function test_modelCompletion() {
        var model = makeModel();
        assertArraysEqual(model.complete('ab'), ['abba', 'abracadabra']);
        assertArraysEqual(model.complete('zoop'), ['zoop']);
        assertArraysEqual(model.complete('zap!'), []);
    },

    /**
     * Test that L{Mantissa.AutoComplete.Model.complete} doesn't think the
     * empty string has any completions
     */
    function test_modelCompletionEmpty() {
        var model = makeModel();
        assertArraysEqual(model.complete(''), []);
    },

    /**
     * Test L{Mantissa.AutoComplete.Model.complete} when the string it is
     * passed is comma-separated
     */
    function test_modelCompletionCSV() {
        var model = makeModel();
        assertArraysEqual(model.complete('zz,yy,   aa'), ['aaa', 'aaab']);
        assertArraysEqual(model.complete(', aa'), ['aaa', 'aaab']);
        assertArraysEqual(model.complete('zoop, zoo'), ['zoop']);
    },

    /**
     * Test L{Mantissa.AutoComplete.Model.appendCompletion}
     */
    function test_modelAppendCompletion() {
        var model = makeModel();
        assertEqual(model.appendCompletion('a, b, cra', 'crabapple'),
                    'a, b, crabapple, ');
        assertEqual(model.appendCompletion('cra', 'crab!'), 'crab!, ');
    },

    /**
     * Test L{Mantissa.AutoComplete.Model.isCompletion}
     */
    function test_modelIsCompletion() {
        var model = makeModel();
        assert(model.isCompletion('foo', 'foooo'));
        assert(model.isCompletion('f', 'f'));
        assert(model.isCompletion('ab', 'abba'));
    },

    /**
     * Test L{Mantissa.AutoComplete.Model.isCompletion}, when the things we
     * pass it are not completions
     */
    function test_modelIsCompletionNeg() {
        var model = makeModel();
        assert(!model.isCompletion('foobar', 'foo'));
        assert(!model.isCompletion('f', 'g'));
        assert(!model.isCompletion('zao', 'zo'));
    },

    /**
     * Test L{Mantissa.AutoComplete.Controller} and its model/view
     * interactions by telling it to find out about completions for the
     * contents of our imaginary textbox.
     */
    function test_alnumKeypressWithCompletions() {
        var controller = makeController(),
            view = controller.view,
            keypressListener = view.keypressListener,
            keypressEvent = makeKeypressEvent(_KEYCODE_ALNUM);

        view.setValue('abb');
        keypressListener(keypressEvent);

        assertArraysEqual(view.visibleCompletions, ['abba']);
        assertEqual(view.theSelectedCompletion, 0);
    },

    /**
     * Test that L{Mantissa.AutoComplete.Controller}'s keypress event handler
     * correctly interprets up/down keypresses as hints that the selection
     * should be moved up/down
     */
    function test_completionNavigation() {
        var controller = makeController(),
            view = controller.view,
            keypressListener = view.keypressListener;

        view.setValue('a');
        keypressListener(makeKeypressEvent(_KEYCODE_ALNUM));

        assertEqual(view.visibleCompletions.length, 5);
        assertEqual(view.theSelectedCompletion, 0);

        keypressListener(makeKeypressEvent(_KEYCODE_DOWN));
        assertEqual(view.theSelectedCompletion, 1);

        keypressListener(makeKeypressEvent(_KEYCODE_UP));
        assertEqual(view.theSelectedCompletion, 0);
    },

    /**
     * Test that L{Mantissa.AutoComplete.View.moveSelectionUp} and
     * L{Mantissa.AutoComplete.View.moveSelectionDown} correctly wrap the
     * selection around
     */
    function test_completionNavigationWraparound() {
        var controller = makeController(),
            view = controller.view,
            keypressListener = view.keypressListener;

        view.setValue('a');
        keypressListener(makeKeypressEvent(_KEYCODE_ALNUM));

        keypressListener(makeKeypressEvent(_KEYCODE_UP));
        assertEqual(view.theSelectedCompletion, 4);

        keypressListener(makeKeypressEvent(_KEYCODE_DOWN));
        assertEqual(view.theSelectedCompletion, 0);
    },

    /**
     * Test that L{Mantissa.AutoComplete.Controller} understands that ENTER
     * means we'd like to have the currently selected completion spliced onto
     * the current value of the view's imaginary textbox
     */
    function test_completionSelection() {
        var controller = makeController(),
            view = controller.view,
            keypressListener = view.keypressListener;

        view.setValue('z');
        keypressListener(makeKeypressEvent(_KEYCODE_ALNUM));

        assertArraysEqual(view.visibleCompletions, ['zoop']);

        keypressListener(makeKeypressEvent(_KEYCODE_ENTER));

        assertEqual(view.getValue(), 'zoop, ');
        assertArraysEqual(view.visibleCompletions, []);
    }]);
