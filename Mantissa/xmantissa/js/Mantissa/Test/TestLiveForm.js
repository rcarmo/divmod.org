
/**
 * Tests for L{Mantissa.LiveForm}.
 */

// import Divmod.UnitTest
// import Nevow.Test.WidgetUtil
// import Mantissa.LiveForm

Mantissa.Test.TestLiveForm._MockFormWidget = Divmod.Class.subclass('Mantissa.Test.TestLiveForm._MockFormWidget');
/**
 * A mock L{Mantissa.LiveForm.FormWidget} subclass which defines just enough
 * attributes to convince the cursory check in
 * L{Mantissa.LiveForm.FormWidget._getSubForms}.
 *
 * @ivar submissionResults: A list with one member corresponding to the
 * C{result} parameter passed to each L{submitSuccess} call.
 * @type submissionResults: C{Array}
 *
 * @ivar inputs: A mapping which will be returned from L{gatherInputs}.
 * Defaults to an empty mapping.
 * @type inputs: C{Object}
 */
Mantissa.Test.TestLiveForm._MockFormWidget.methods(
    function __init__(self, formName, inputs/*={}*/) {
        self.formName = formName;
        self.submissionResults = [];
        if(inputs === undefined) {
            inputs = {};
        }
        self.inputs = inputs;
    },

    /**
     * Return L{inputs}.
     */
    function gatherInputs(self) {
        return self.inputs;
    },

    /**
     * Append C{result} to L{submissionResults}.
     */
    function submitSuccess(self, result) {
        self.submissionResults.push(result);
    });

Mantissa.Test.TestLiveForm.SubFormWidgetTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestLiveForm.SubFormWidgetTests');
/**
 * Tests for L{Mantissa.LiveForm.SubFormWidget}.
 */
Mantissa.Test.TestLiveForm.SubFormWidgetTests.methods(
    function setUp(self) {
        self.node = Nevow.Test.WidgetUtil.makeWidgetNode();
        self.widget = Mantissa.LiveForm.SubFormWidget(self.node, 'formName');
    },

    /**
     * L{Mantissa.LiveForm.SubFormWidget} should have a C{formName} attribute.
     */
    function test_formName(self) {
        self.assertIdentical(self.widget.formName, 'formName');
    },

    /**
     * L{Mantissa.LiveForm.SubFormWidget.submitSuccess} should call
     * C{submitSuccess} on its child widgets.
     */
    function test_submitSuccess(self) {
        var firstWidget = Mantissa.Test.TestLiveForm._MockFormWidget('foo');
        var secondWidget = Mantissa.Test.TestLiveForm._MockFormWidget('bar');

        self.widget.childWidgets = [firstWidget, secondWidget];

        var RESULT = 'result!';
        self.widget.submitSuccess(RESULT);

        self.assertIdentical(firstWidget.submissionResults.length, 1);
        self.assertIdentical(firstWidget.submissionResults[0], RESULT);

        self.assertIdentical(secondWidget.submissionResults.length, 1);
        self.assertIdentical(secondWidget.submissionResults[0], RESULT);
    },

    /**
     * Make an <input> node with the specified attributes.
     *
     * @type attributes: C{Object}
     * @param attributes: Mapping of attribute names to attribute values.
     *
     * @rtype: node
     */
    function _makeInputNode(self, attributes) {
        var input = document.createElement("input");
        for(var attrName in attributes) {
            input.setAttribute(attrName, attributes[attrName]);
            input[attrName] = attributes[attrName];
        }
        return input;
    },

    /**
     * Utility for testing how L{Mantissa.LiveForm.SubFormWidget.gatherInputs}
     * extracts values from various kinds of <input> nodes.
     *
     * @type inputNodeAttributes: C{Object}
     * @param inputNodeAttributes: Mapping of attribute names to attribute
     * values.  These pairs will be turned into attributes on the <input> node
     * that we create.
     *
     * @param value: The value that C{gatherInputs} is expected to extract from
     * the input node.
     */
    function _doGatherInputsTest(self, inputNodeAttributes, value) {
        self.node.appendChild(self._makeInputNode(inputNodeAttributes));
        var resultInputs = self.widget.gatherInputs();
        var resultInputValues = resultInputs[inputNodeAttributes.name];
        self.assertIdentical(resultInputValues.length, 1);
        self.assertIdentical(resultInputValues[0], value);
    },

    /**
     * L{Mantissa.LiveForm.SubFormWidget.gatherInputs} should include text
     * inputs in its mapping.
     */
    function test_gatherInputsIncludesTextInputs(self) {
        var INPUT_VALUE = "this is the input value.";
        self._doGatherInputsTest(
            {type: "text", name: "input", value: INPUT_VALUE}, INPUT_VALUE)
    },

    /**
     * L{Mantissa.LiveForm.SubFormWidget.gatherInputs} should include password
     * inputs in its mapping.
     */
    function test_gatherInputsIncludesPasswordInputs(self) {
        var INPUT_VALUE = "this is the secret input value.";
        self._doGatherInputsTest(
            {type: "password", name: "input", value: INPUT_VALUE}, INPUT_VALUE)
    },

    /**
     * L{Mantissa.LiveForm.SubFormWidget.gatherInputs} should include checked
     * checkbox inputs in its mapping.
     */
    function test_gatherInputsIncludesCheckedCheckboxInputs(self) {
        self._doGatherInputsTest(
            {type: "checkbox", name: "input", checked: true}, true);
    },

    /**
     * L{Mantissa.LiveForm.SubFormWidget.gatherInputs} should include unchecked
     * checkbox inputs in its mapping.
     */
    function test_gatherInputsIncludesUncheckedCheckboxInputs(self) {
        self._doGatherInputsTest(
            {type: "checkbox", name: "input", checked: false}, false);
    },

    /**
     * L{Mantissa.LiveForm.SubFormWidget.gatherInputs} should include checked
     * radio button inputs in its mapping.
     */
    function test_gatherInputsIncludesCheckedRadioInputs(self) {
        self._doGatherInputsTest(
            {type: "radio", name: "input", checked: true}, true);
    },

    /**
     * L{Mantissa.LiveForm.SubFormWidget.gatherInputs} should include unchecked
     * radio button inputs in its mapping.
     */
    function test_gatherInputsIncludesUncheckedCheckboxInputs(self) {
        self._doGatherInputsTest(
            {type: "radio", name: "input", checked: false}, false);
    },

    /**
     * L{Mantissa.LiveForm.SubFormWidget.gatherInputs} should include textareas
     * in its mapping.
     */
    function test_gatherInputsIncludesTextareaInputs(self) {
        var TEXTAREA_NAME = "textarea-name";
        var TEXTAREA_VALUE = "this is some long, free-form text";

        var textareaNode = document.createElement("textarea");
        textareaNode.setAttribute("name", TEXTAREA_NAME);
        textareaNode["name"] = TEXTAREA_NAME;
        // is it standard that the "value" property of textarea nodes can be
        // used instead of node.firstChild.nodeValue?
        textareaNode.setAttribute("value", TEXTAREA_VALUE);
        textareaNode["value"] = TEXTAREA_VALUE;

        self.node.appendChild(textareaNode);

        var result = self.widget.gatherInputs();
        self.assertIdentical(result[TEXTAREA_NAME].length, 1);
        self.assertIdentical(result[TEXTAREA_NAME][0], TEXTAREA_VALUE);
    },

    /**
     * Make a <select> node, with one <option> child for each item in C{options}.
     *
     * @type name: C{String}
     * @param name: The value of the I{name} attribute on the created node.
     *
     * @type options: C{Array}
     * @param options: The available options.
     *
     * @rtype: node
     */
    function _makeSelectNode(self, name, options) {
        var selectNode = document.createElement("select");
        selectNode.setAttribute("name", name);
        selectNode["name"] = name;
        for(var i = 0; i < options.length; i++) {
            var optionNode = document.createElement("option");
            optionNode.setAttribute("value", options[i]);
            optionNode["value"] = options[i];
            optionNode.appendChild(document.createTextNode(options[i]));
            selectNode.appendChild(optionNode);
        }
        selectNode.options = selectNode.childNodes; // XXX
        return selectNode;
    },

    /**
     * L{Mantissa.LiveForm.SubFormWidget.gatherInputs} should include
     * single-select inputs in its mapping.
     */
    function test_gatherInputsIncludesSingleSelectInputs(self) {
        var SELECT_NAME = "select-name";
        var selectNode = self._makeSelectNode(SELECT_NAME, ["one", "two"]);
        selectNode.setAttribute("type", "select-one");
        selectNode["type"] = "select-one";
        selectNode.setAttribute("value", "two");
        selectNode["value"] = "two";
        self.node.appendChild(selectNode);

        var result = self.widget.gatherInputs();
        self.assertIdentical(result[SELECT_NAME].length, 1);
        self.assertIdentical(result[SELECT_NAME][0], "two");
    },

    /**
     * L{Mantissa.LiveForm.SubFormWidget.gatherInputs} should include
     * multi-select inputs in its mapping.
     */
    function test_gatherInputsIncludesMultipleSelectInputs(self) {
        var SELECT_NAME = "select-name";
        var selectNode = self._makeSelectNode(SELECT_NAME, ["one", "two", "three"]);
        selectNode.childNodes[0].setAttribute("selected", true);
        selectNode.childNodes[0]["selected"] = true;
        selectNode.childNodes[1].setAttribute("selected", false);
        selectNode.childNodes[1]["selected"] = false;
        selectNode.childNodes[2].setAttribute("selected", true);
        selectNode.childNodes[2]["selected"] = true;
        self.node.appendChild(selectNode);

        var result = self.widget.gatherInputs();
        self.assertIdentical(result[SELECT_NAME].length, 1);
        self.assertIdentical(result[SELECT_NAME][0].length, 2);
        self.assertIdentical(result[SELECT_NAME][0][0], "one");
        self.assertIdentical(result[SELECT_NAME][0][1], "three");
    },

    /**
     * L{Mantissa.LiveForm.SubFormWidget.gatherInputs} should include subforms
     * in its mapping.
     */
    function test_gatherInputsIncludesSubForms(self) {
        var INPUTS = {foo: ['bar']};
        var FORM_NAME = 'formName';
        self.widget.childWidgets = [
            Mantissa.Test.TestLiveForm._MockFormWidget(FORM_NAME, INPUTS)];
        var result = self.widget.gatherInputs();
        self.assertIdentical(result[FORM_NAME].length, 1);
        self.assertIdentical(result[FORM_NAME][0], INPUTS);
    },

    /**
     * L{Mantissa.LiveForm.SubFormWidget.setInputValues} should throw
     * L{Mantissa.LiveForm.NodeCountMismatch} if it is passed a number of
     * values for an input name that is different to the number of actual
     * inputs by that name.
     */
    function test_setInputValuesNodeCountMismatch(self) {
        self.node.appendChild(
            self._makeInputNode(
                {name: "foo", type: "text", value: "hi"}));
        // too many
        self.assertThrows(
            Mantissa.LiveForm.NodeCountMismatch,
            function() {
                self.widget.setInputValues({foo: ["bye", "bye"]});
            });
        self.node.appendChild(
            self._makeInputNode(
                {name: "foo", type: "text", value: "hello"}));
        // too few
        self.assertThrows(
            Mantissa.LiveForm.NodeCountMismatch,
            function() {
                self.widget.setInputValues({foo: ["ok"]});
            });
    },

    /**
     * L{Mantissa.LiveForm.SubFormWidget.setInputValues} should throw
     * L{Mantissa.LiveForm.BadInputName} if it passed an input name for which
     * there are no corresponding inputs.
     */
    function test_setInputValuesBadInputName(self) {
        self.assertThrows(
            Mantissa.LiveForm.BadInputName,
            function() {
                self.widget.setInputValues({foo: ["hi"]});
            });
    });

/**
 * Tests for L{Mantissa.LiveForm.FormWidget}.
 */
Mantissa.Test.TestLiveForm.FormWidgetTests = Mantissa.Test.TestLiveForm.SubFormWidgetTests.subclass(
    'Mantissa.Test.TestLiveForm.FormWidgetTests');
Mantissa.Test.TestLiveForm.FormWidgetTests.methods(
    /**
     * Create a L{Mantissa.LiveForm.FormWidget} with a simple node.
     */
    function setUp(self) {
        self.node = document.createElement('span');
        self.node.id = 'athena:123';
        document.body.appendChild(self.node);
        self.widget = Mantissa.LiveForm.FormWidget(self.node, 'formName');
        self.progressMessage = 'visible';
        self.widget.hideProgressMessage = function() {
            self.progressMessage = 'hidden';
        };
    },

    /**
     * Remove from the document the node which was added by setUp.
     */
    function tearDown(self) {
        document.body.removeChild(self.node);
    },

    /**
     * L{Mantissa.LiveForm.FormWidget.submitFailure} should dispatch
     * L{Mantissa.LiveForm.InputError} errors to
     * L{Mantissa.LiveForm.FormWidget.displayInputError}.
     */
    function test_handleInputErrorFailure(self) {
        var error = Mantissa.LiveForm.InputError("bogus input");
        var failure = Divmod.Defer.Failure(error);
        var inputErrors = [];
        self.widget.displayInputError = function stubDisplayInputError(err) {
            inputErrors.push(err);
        };
        self.widget.submitFailure(failure);
        self.assertIdentical(inputErrors.length, 1);
        self.assertIdentical(inputErrors[0], error);
        self.assertIdentical(self.progressMessage, 'hidden');
    },

    /**
     * L{Mantissa.LiveForm.FormWidget.submitFailure} should not dispatch
     * exceptions which do not derive from L{Mantissa.LiveForm.InputError} to
     * L{Mantissa.LiveForm.FormWidget.displayInputError}.
     */
    function test_handleOtherFailure(self) {
        var failure = Divmod.Defer.Failure(Divmod.Error("random failure"));
        var inputErrors = [];
        self.widget.displayInputError = function stubDisplayInputError(err) {
            inputErrors.push(err);
        };
        self.widget.submitFailure(failure);
        self.assertIdentical(inputErrors.length, 0);
        self.assertIdentical(self.progressMessage, 'hidden');
    },

    /**
     * L{Mantissa.LiveForm.FormWidget.displayInputError} should replace the
     * contents of the node beneath the widget with the I{class} of
     * I{input-error-message} with the string of the failure.
     */
    function test_displayInputError(self) {
        var messageNode = document.createElement('span');
        messageNode.id = 'athenaid:123-input-error-message';
        messageNode.appendChild(document.createElement('span'));
        self.node.appendChild(messageNode);
        self.widget.displayInputError(
            Mantissa.LiveForm.InputError('bogus input'));
        self.assertIdentical(messageNode.childNodes.length, 1);
        self.assertIdentical(
            messageNode.childNodes[0].nodeValue,
            'bogus input');
    },

    /**
     * L{Mantissa.LiveForm.FormWidget.displayInputError} should do nothing if
     * no status node can be found.
     */
    function test_missingStatusNode(self) {
        self.widget.displayInputError(
            Mantissa.LiveForm.InputError('bogus input'));
        self.assertIdentical(
            self.widget.node.childNodes.length, 0);
    });



Mantissa.Test.TestLiveForm.RepeatableFormTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestLiveForm.RepeatableFormTests');
/**
 * Tests for L{Mantissa.LiveForm.RepeatableForm}.
 */
Mantissa.Test.TestLiveForm.RepeatableFormTests.methods(
    function setUp(self) {
        self.node = document.createElement('span');
        self.node.id = 'athena:123';
        document.body.appendChild(self.node);
        self.repeatableForm = Mantissa.LiveForm.RepeatableForm(self.node, 'xyz');
    },

    /**
     * L{Mantissa.LiveForm.RepeatableForm.gatherInputs} should accumulate the
     * results of calling C{gatherInputs} on its child widgets, if they appear
     * to be in the document.
     */
    function test_gatherInputsAccumulates(self) {
        var fakeChild = {
            gatherInputs: function() {
                return {'foo': 'bar1'};
            },
            node: {parentNode: document.createElement('div')}
        };
        var fakeChild2 = {
            gatherInputs: function() {
                return {'foo': 'bar2'};
            },
            node: {parentNode: document.createElement('div')}
        };
        var fakeChildToIgnore = {
            gatherInputs: function() {
                return {'foo': 'bar3'}
            },
            node: {parentNode: null}
        };
        self.repeatableForm.childWidgets.push(fakeChild);
        self.repeatableForm.childWidgets.push(fakeChild2);
        var inputs = self.repeatableForm.gatherInputs();
        self.assertIdentical(inputs.length, 2);
        self.assertIdentical(inputs[0]['foo'], 'bar1');
        self.assertIdentical(inputs[1]['foo'], 'bar2');
    },

    /**
     * L{Mantissa.LiveForm.RepeatableForm.submitSuccess} should forward the
     * call to all of its child widgets.
     */
    function test_submitSuccess(self) {
        var firstChildWidget = Mantissa.Test.TestLiveForm._MockFormWidget('formName');
        var secondChildWidget = Mantissa.Test.TestLiveForm._MockFormWidget('otherFormName');
        self.repeatableForm.childWidgets = [firstChildWidget, secondChildWidget];

        var RESULT = 'the result.';
        self.repeatableForm.submitSuccess(RESULT);
        self.assertIdentical(firstChildWidget.submissionResults.length, 1);
        self.assertIdentical(firstChildWidget.submissionResults[0], RESULT);

        self.assertIdentical(secondChildWidget.submissionResults.length, 1);
        self.assertIdentical(secondChildWidget.submissionResults[0], RESULT);
    },

    /**
     * L{Mantissa.LiveForm.RepeatableForm.formName} should be set the second
     * argument given to the constructor.
     */
    function test_formNameDefined(self) {
        self.assertIdentical(self.repeatableForm.formName, 'xyz');
    });


Mantissa.Test.TestLiveForm.RepeatedLiveFormWrapperTestCase = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestLiveForm.RepeatedLiveFormWrapperTestCase');
/**
 * Tests for L{Mantissa.LiveForm.RepeatedLiveFormWrapper}.
 */
Mantissa.Test.TestLiveForm.RepeatedLiveFormWrapperTestCase.methods(
    function setUp(self) {
        self.node = Nevow.Test.WidgetUtil.makeWidgetNode();
        self.identifier = -42;
        self.widget = Mantissa.LiveForm.RepeatedLiveFormWrapper(
            self.node, 'formName', self.identifier);
    },

    /**
     * L{Mantissa.LiveForm.RepeatedLiveFormWrapper} should define a
     * C{submitSuccess} method.
     */
    function test_submitSuccess(self) {
        var result = 'the result.';
        var childForm = Mantissa.Test.TestLiveForm._MockFormWidget('foo');
        self.widget.childWidgets = [childForm];
        self.widget.submitSuccess(result);
        self.assertIdentical(childForm.submissionResults.length, 1);
        self.assertIdentical(childForm.submissionResults[0], result);
    },

    /**
     * L{Mantissa.LiveForm.RepeatedLiveFormWrapper.gatherInputs} should defer
     * to its child widget's implementation, as well as sticking the
     * C{identifier} initarg into its result.
     */
    function test_gatherInputs(self) {
        self.widget.childWidgets.push(
            {gatherInputs: function() {
                return {foo: ['baz']};
            }});
        var result = self.widget.gatherInputs();
        self.assertIdentical(result['foo'].length, 1);
        self.assertIdentical(result['foo'][0], 'baz');
        self.assertIdentical(result['__repeated-liveform-id__'], self.identifier);
    });
