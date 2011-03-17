// -*- test-case-name: xmantissa.test.test_javascript -*-
// Copyright (c) 2007 Divmod.
// See LICENSE for details.

/**
 * Tests for L{Mantissa.Validate}
 */

// import Divmod.UnitTest
// import Mantissa.Validate

// import Nevow.Test.Util

/**
 *
 */
Mantissa.Test.TestValidate.ValidateTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestValidate.ValidateTests');
Mantissa.Test.TestValidate.ValidateTests.methods(
    /**
     * Create a L{SignupForm} associated with some very minimal DOM state,
     * sufficient only to test I{defaultUsername}.
     */
    function setUp(self) {
        self.faker = Nevow.Test.Util.Faker();
        self.node = document.createElement('div');
        self.node.id = 'athena:987';

        /*
         * passwordNode and submitNode are required just for __init__ to
         * succeed.
         */
        self.passwordNode = document.createElement('input');
        self.passwordNode.type = 'password';
        self.passwordNode.setAttribute('name', 'password');
        self.node.appendChild(self.passwordNode);

        self.submitNode = document.createElement('input');
        self.submitNode.type = 'submit';
        self.submitNode.setAttribute('type', 'submit');
        self.node.appendChild(self.submitNode);

        /*
         * This node will actually be fiddled with to test the behavior of
         * defaultUsername.
         */
        self.realNameNode = document.createElement('input');
        self.realNameNode.type = 'text';
        self.realNameNode.setAttribute('name', 'realName');
        self.realNameNode.value = '';
        self.node.appendChild(self.realNameNode);

        self.signup = Mantissa.Validate.SignupForm(self.node);
    },

    /**
     * Restore all fake state.
     */
    function tearDown(self) {
        self.faker.stop();
    },

    /**
     * Successful submission of the form ought to hide the 'progress' message,
     * then show the 'success' message associated with this form.  Unlike
     * other live forms, the success message includes a link to the next step,
     * so there should be no timed event to remove it.
     */
    function test_hideAndShow(self) {
        var timeouts = [];
        var progressHidden = false;
        var successShown = false;
        self.faker.fake("setTimeout", function (thunk, timeout) {
            timeouts.push(thunk);
        });
        self.signup.hideProgressMessage = function () {
            progressHidden = true;
        };
        self.signup.showSuccessMessage = function () {
            successShown = true;
        };
        self.signup.hideSuccessMessage = function () {
            successShown = false;
        }
        self.signup.submitSuccess();
        self.assert(progressHidden);
        self.assert(successShown);
        for (var i = 0; i < timeouts.length; i++) {
            timeouts[i]();
        }
        self.assert(successShown);
    },

    /**
     * L{SignupForm.defaultUsername} should not change the value of the
     * I{input} node it is passed if it already has a non-empty value.
     */
    function test_defaultUsernameRespectsExistingValue(self) {
        var username = "bob";
        var usernameNode = document.createElement('input');
        usernameNode.value = username;
        self.signup.defaultUsername(usernameNode);
        self.assertIdentical(usernameNode.value, username);
    },

    /**
     * L{SignupForm.defaultUsername} should set the value of the I{input} node
     * it is passed to a string based on its real name field if the L{input}
     * node has no value.
     */
    function test_defaultUsernameFillsEmptyInput(self) {
        var usernameNode = document.createElement('input');
        usernameNode.value = '';
        self.realNameNode.value = "Alice Allison";
        self.signup.defaultUsername(usernameNode);
        self.assertIdentical(usernameNode.value, "alice.allison");
    });
