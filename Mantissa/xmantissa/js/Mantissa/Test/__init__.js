
// import Nevow.Athena.Test

// import Mantissa
// import Mantissa.ScrollTable
// import Mantissa.Admin


Mantissa.Test.Forms = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.Forms');
Mantissa.Test.Forms.methods(
    function test_formSubmission(self) {
        return self.childWidgets[0].submit();
    });

Mantissa.Test.StatsTest = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.StatsTest');
Mantissa.Test.StatsTest.methods(
    function test_statsGraph(self) {
        return self.callRemote('run');
    });

Mantissa.Test.UserInfoSignup = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.UserInfoSignup');
Mantissa.Test.UserInfoSignup.methods(
    function test_signup(self) {
        // Ensure that filling out the signup form in a strange order
        // doesn't prevent it from being submittable.
        var f = self.childWidgets[0];
        var button = f.nodeByAttribute("name", "__submit__");
        f.node.firstName.value = "Fred";
        f.node.firstName.onkeyup();
        f.node.firstName.onblur();
        f.node.lastName.value = "Foobar";
        f.node.lastName.onkeyup();
        f.node.lastName.onblur();
        f.node.username.onfocus();
        // this is the onkeyup for the username field --
        // doing this by hand to get at the deferred
        return Nevow.Athena.Widget.get(f.node.username).verifyUsernameAvailable(
            f.node.username).addCallback(function(x) {
                    f.node.password.value = "x";
                    f.node.password.onkeyup();
                    f.node.password.onblur();
                    f.node.confirmPassword.value = "foobaz";
                    f.node.confirmPassword.onkeyup();
                    f.node.confirmPassword.onblur();
                    // The password is invalid and there's no email address.
                    // The form shouldn't be submittable.
                    self.assertEquals(f.submitButton.disabled, true);
                    f.node.emailAddress.value = "fred@example.com";
                    f.node.emailAddress.onkeyup();
                    f.node.emailAddress.onblur();
                    // The password is still invalid, so still not ready
                    self.assertEquals(f.submitButton.disabled, true);
                    f.node.password.value = "foobaz";
                    f.node.password.onkeyup();
                    f.node.password.onblur();

                    /*
                     * XXX - I think this is a bug.  You shouldn't have to
                     * revisit the confirm field if the value just entered into
                     * the password field already matches it.
                     */
                    f.node.confirmPassword.onblur();

                    // The password is now valid and all the fields are filled.
                    // It should be ready to submit.
                    self.assertEquals(f.submitButton.disabled, false);
                });
    });
Mantissa.Test.SignupLocalpartValidation = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.SignupLocalpartValidation');
Mantissa.Test.SignupLocalpartValidation.methods(
    /*
     * Ensure that the username is a valid email localpart, even if
     * the firstname and lastname it's generated from contain invalid
     * characters.
     */
    function test_validLocalpart(self) {
        var f = self.childWidgets[0];
        var button = f.nodeByAttribute("name", "__submit__");
        f.node.firstName.value = "Fred@Home";
        f.node.firstName.onkeyup();
        f.node.firstName.onblur();
        f.node.lastName.value = "Foo bar";
        f.node.lastName.onkeyup();
        f.node.lastName.onblur();
        f.node.username.onfocus();
	self.assertEquals(f.node.username.value, "fred_home.foo_bar");
    });

Mantissa.Test.SignupValidationInformation = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.SignupValidationInformation');
Mantissa.Test.SignupValidationInformation.methods(
    function setUp(self) {
        var d = self.callRemote('makeWidget');
        d.addCallback(
            function (result) {
                return self.addChildWidgetFromWidgetInfo(result);
            });
        d.addCallback(
            function (widget) {
                self.widget = widget;
                self.node.appendChild(widget.node);
            });
        return d;
    },


    /**
     * Set the field called C{name} to C{value}, as if the user had typed the
     * name in and hit <tab>.
     */
    function setField(self, name, value) {
        var field = self.widget.node[name];
        field.onfocus();
        field.value = value;
        field.onkeyup();
        field.onblur();
    },


    /**
     * Focus on the given field.
     */
    function focusOn(self, name) {
        var field = self.widget.node[name];
        field.onfocus();
    },


    /**
     * Return the warning that is currently being displayed to the user.
     */
    function getWarning(self) {
        var node = self.widget.nodeByAttribute('class', 'validation-message');
        return MochiKit.DOM.scrapeText(node);
    },


    /**
     * Test that the form's status message is initially blank.
     */
    function test_initialMessage(self) {
        var d = self.setUp();
        return d.addCallback(
            function (ignored) {
                self.assertEquals(self.getWarning(),
                                  Mantissa.Validate.ERRORS['initial']);
            });
    },


    /**
     * Test that the form's status message stays blank after good input.
     */
    function test_goodInput(self) {
        var d = self.setUp();
        return d.addCallback(
            function (ignored) {
                self.setField('firstName', 'Jonathan');
                self.assertEquals(self.getWarning(),
                                  Mantissa.Validate.ERRORS['input-valid']);
                self.focusOn('firstName');
                self.assertEquals(self.getWarning(),
                                  Mantissa.Validate.ERRORS['input-valid']);
            });
    },


    /**
     * Test that the form's status message reports the error in a bad input
     * value.
     */
    function test_badInput(self) {
        var d = self.setUp();
        return d.addCallback(
            function (ignored) {
                self.setField('firstName', '');
                self.assertEquals(self.getWarning(),
                                  Mantissa.Validate.ERRORS['input-empty']);
            });
    },


    /**
     * Test that the form's status message reports the error from the currently
     * focused input field, even if there are multiple bad inputs and some good
     * inputs.
     */
    function test_mixedInput(self) {
        var d = self.setUp();
        return d.addCallback(
            function (ignored) {
                self.setField('firstName', '');
                self.setField('password', ' ');
                self.setField('emailAddress', 'test@example.com');
                self.focusOn('emailAddress');
                self.assertEquals(self.getWarning(),
                                  Mantissa.Validate.ERRORS['input-valid']);
                self.focusOn('password');
                self.assertEquals(self.getWarning(),
                                  Mantissa.Validate.ERRORS['password-weak']);
                self.focusOn('firstName');
                self.assertEquals(self.getWarning(),
                                  Mantissa.Validate.ERRORS['input-empty']);
            });
    },


    /**
     * C{username} has its own onfocus event. Make sure that it still has its
     * status updated if it is invalid.
     */
    function test_badUsername(self) {
        // we have to call the verify* method directly because it returns a
        // Deferred that the event handlers never get (I think) -- jml.
        var d = self.setUp(self);
        d.addCallback(
            function (ignored) {
                var field = self.widget.node.username;
                field.value = 'bad';
                return self.widget.verifyUsernameAvailable(field);
            });
        return d.addCallback(
            function (ignored) {
                self.focusOn('username');
                self.assertEquals(self.getWarning(), 'bad username');
            });
    },


    /**
     * The username field has an asynchronous validation function. That means
     * that the user might find out about its validity while they are entering
     * data in another field.
     *
     * Check that we do I{not} change the status message to report on a field
     * which does not have focus. Stated positively, we should only display the
     * status of the field which currently has focus.
     */
    function test_onlyWhenFocused(self) {
        var d = self.setUp(self);
        d.addCallback(
            function (ignored) {
                // set the value of username, then set firstName, focus it,
                // _then_ evaluate username. This duplicates the likely order
                // of events when a user provides data for username, hits tab,
                // then begins typing.
                var field = self.widget.node.username;
                field.value = 'bad';
                self.setField('firstName', 'Jonathan');
                self.focusOn('firstName');
                return self.widget.verifyUsernameAvailable(field);
            });
        return d.addCallback(
            function (ignored) {
                self.assertEquals(self.getWarning(),
                                  Mantissa.Validate.ERRORS['input-valid']);
            });
    });



Mantissa.Test.Text = Mantissa.Test.Forms.subclass('Mantissa.Test.Text');

Mantissa.Test.MultiText = Mantissa.Test.Forms.subclass('Mantissa.Test.MultiText');

Mantissa.Test.TextArea = Mantissa.Test.Forms.subclass('Mantissa.Test.TextArea');

Mantissa.Test.Select = Mantissa.Test.Forms.subclass('Mantissa.Test.Select');

Mantissa.Test.ChoiceMultiple = Mantissa.Test.Forms.subclass('Mantissa.Test.ChoiceMultiple');

Mantissa.Test.Choice = Mantissa.Test.Forms.subclass('Mantissa.Test.Choice');

Mantissa.Test.Traverse = Mantissa.Test.Forms.subclass('Mantissa.Test.Traverse');

Mantissa.Test.FormName = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.FormName');
/**
 * Test that the form name gets communicated intact to
 * L{Mantissa.LiveForm.FormWidget}
 */
Mantissa.Test.FormName.methods(
    /**
     * Check that the C{formName} attributes on our form, and on its child
     * form are set correctly
     */
    function test_attribute(self) {
        var outer = self.childWidgets[0],
            inner = outer.childWidgets[0];
        self.assertEquals(outer.formName, null);
        self.assertEquals(inner.formName, 'inner-form');
    });

/**
 * Tests for L{Mantissa.LiveForm.FormWidget.setInputValues} and related
 * functionality
 */
Mantissa.Test.SetInputValues = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.SetInputValues');
Mantissa.Test.SetInputValues.methods(
    /**
     * Test that setInputValues() doesn't change anything if passed the
     * current values of the inputs
     */
    function test_noop(self) {
        var form  = self.childWidgets[0];
        form.setInputValues(form.gatherInputs());
        self._checkGatherInputs()
    },

    /**
     * Reverse/invert all values, then submit the form.  The server makes some
     * assertions for us.
     */
    function test_submission(self) {
        var inverted = {choice: ["1"],
                        choiceMult: [["2", "3"]],
                        text: ["dlrow olleh"],
                        textArea: ["2 dlrow olleh"],
                        passwd: ["yek terces"],
                        checkbox: [false]};
        var form = self.childWidgets[0];
        form.setInputValues(inverted);
        return form.submit();
    });

Mantissa.Test.OnlyNick = Mantissa.Test.Forms.subclass('Mantissa.Test.OnlyNick');
Mantissa.Test.NickNameAndEmailAddress = Mantissa.Test.Forms.subclass('Mantissa.Test.NickNameAndEmailAddress');

Mantissa.Test.ScrollTableModelTestCase = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.ScrollTableModelTestCase');
Mantissa.Test.ScrollTableModelTestCase.methods(
    /**
     * Create a ScrollModel to run tests against.
     *
     * For now, setUp is /not/ a fixture provided by the harness. Each test
     * method invokes it explicitly.
     */
    function setUp(self) {
        self.model = Mantissa.ScrollTable.ScrollModel();
    },

    /**
     * Test that new rows can be added to a ScrollModel.
     */
    function test_setRowData(self) {
        self.setUp();

        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});
        self.model.setRowData(1, {__id__: 'b', baz: 'quux'});

        self.assertEqual(self.model.getRowData(0).__id__, 'a');
        self.assertEqual(self.model.getRowData(1).__id__, 'b');

        /*
         * Negative updates must be rejected.
         */
        var error = self.assertThrows(
            Divmod.IndexError,
            function() { self.model.setRowData(-1, {__id__: 'c'}); });
        self.assertEqual(
            error.message,
            "Specified index (-1) out of bounds in setRowData.");
    },

    /**
     * Test that the correct number of rows is returned by
     * L{ScrollModel.rowCount}.
     */
    function test_rowCount(self) {
        self.setUp();

        self.assertEqual(self.model.rowCount(), 0);
        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});
        self.assertEqual(self.model.rowCount(), 1);
        self.model.setRowData(1, {__id__: 'b', baz: 'quux'});
        self.assertEqual(self.model.rowCount(), 2);
    },

    /**
     * Test that the index of a particular row can be found with its webID
     * using L{ScrollModel.findIndex}.
     */
    function test_findIndex(self) {
        self.setUp();

        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});
        self.model.setRowData(1, {__id__: 'b', baz: 'quux'});

        self.assertEqual(self.model.findIndex('a'), 0);
        self.assertEqual(self.model.findIndex('b'), 1);

        var error = self.assertThrows(
            Mantissa.ScrollTable.NoSuchWebID,
            function() { self.model.findIndex('c'); });
        self.assertEqual('c', error.webID);
        self.assertEqual(error.toString(), 'WebID c not found');
    },

    /**
     * Test that an array of indices which actually have row data can be
     * retrieved from the ScrollModel.
     */
    function test_getRowIndices(self) {
        self.setUp();

        self.model.setRowData(0, {__id__: 'a'});
        self.model.setRowData(3, {__id__: 'b'});
        self.assertArraysEqual(self.model.getRowIndices(), [0, 3]);
    },

    /**
     * Test that L{Mantissa.ScrollTable.ScrollingWidget.getRowIndices} returns
     * the indices in ascending order, even if rows were added out of order
     */
    function test_getRowIndicesOrder(self) {
        self.setUp();

        self.model.setRowData(10, {__id__: '10'});
        self.model.setRowData(0, {__id__: '0'});
        self.model.setRowData(3, {__id__: '3'});

        self.assertArraysEqual(self.model.getRowIndices(), [0, 3, 10]);
    },

    /**
     * Test that the data associated with a particular row can be discovered by
     * that row's index in the model using L{ScrollModel.getRowData}.
     */
    function test_getRowData(self) {
        self.setUp();

        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});
        self.model.setRowData(1, {__id__: 'b', baz: 'quux'});

        self.assertEqual(self.model.getRowData(0).foo, 'bar');
        self.assertEqual(self.model.getRowData(1).baz, 'quux');

        var error;

        error = self.assertThrows(
            Divmod.IndexError,
            function() { self.model.getRowData(-1); });
        self.assertEqual(
            error.message,
            "Specified index (-1) out of bounds in getRowData.");

        error = self.assertThrows(
            Divmod.IndexError,
            function() { self.model.getRowData(2); });
        self.assertEqual(
            error.message,
            "Specified index (2) out of bounds in getRowData.");

        /*
         * The array is sparse, so valid indexes might not be
         * populated.  Requesting these should return undefined rather
         * than throwing an error.
         */
        self.model.setRowData(3, {__id__: 'd'});

        self.assertEqual(self.model.getRowData(2), undefined);
    },

    /**
     * Test that the data associated with a particular webID can be discovered
     * from that webID using L{ScrollModel.findRowData}.
     */
    function test_findRowData(self) {
        self.setUp();

        /*
         * XXX This should populate the model's rows using a public API
         * of some sort.
         */
        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});
        self.model.setRowData(1, {__id__: 'b', baz: 'quux'});

        self.assertEqual(self.model.findRowData('a').foo, 'bar');
        self.assertEqual(self.model.findRowData('b').baz, 'quux');

        var error = self.assertThrows(
            Mantissa.ScrollTable.NoSuchWebID,
            function() { self.model.findRowData('c'); });
        self.assertEqual(error.webID, 'c');
    },

    /**
     * Test that we can advance through a model's rows with
     * L{ScrollModel.findNextRow}.
     */
    function test_findNextRow(self) {
        self.setUp();

        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});
        self.model.setRowData(1, {__id__: 'b', baz: 'quux'});
        self.model.setRowData(2, {__id__: 'c', red: 'green'});
        self.model.setRowData(3, {__id__: 'd', blue: 'yellow'});
        self.model.setRowData(4, {__id__: 'e', white: 'black'});
        self.model.setRowData(5, {__id__: 'f', brown: 'puce'});

        /*
         * We should be able to advance without a predicate
         */
        self.assertEqual(self.model.findNextRow('a'), 'b');
        self.assertEqual(self.model.findNextRow('b'), 'c');

        /*
         * Going off the end should result in a null result.
         */
        self.assertEqual(self.model.findNextRow('f'), null);

        /*
         * A predicate should be able to cause rows to be skipped.
         */
        self.assertEqual(
            self.model.findNextRow(
                'a',
                function(idx, row, node) {
                    if (row.__id__ == 'b') {
                        return false;
                    }
                    return true;
                }),
            'c');
    },

    /**
     * Like L{test_findNextRow}, but for L{ScrollModel.findPrevRow}.
     */
    function test_findPrevRow(self) {
        self.setUp();

        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});
        self.model.setRowData(1, {__id__: 'b', baz: 'quux'});
        self.model.setRowData(2, {__id__: 'c', red: 'green'});
        self.model.setRowData(3, {__id__: 'd', blue: 'yellow'});
        self.model.setRowData(4, {__id__: 'e', white: 'black'});
        self.model.setRowData(5, {__id__: 'f', brown: 'puce'});

        /*
         * We should be able to regress without a predicate
         */
        self.assertEqual(self.model.findPrevRow('f'), 'e');
        self.assertEqual(self.model.findPrevRow('e'), 'd');

        /*
         * Going off the beginning should result in a null result.
         */
        self.assertEqual(self.model.findPrevRow('a'), null);

        /*
         * A predicate should be able to cause rows to be skipped.
         */
        self.assertEqual(
            self.model.findPrevRow(
                'f',
                function(idx, row, node) {
                    if (row.__id__ == 'e') {
                        return false;
                    }
                    return true;
                }),
            'd');
    },

    /**
     * Test that rows can be removed from the model and that the model remains
     * in a consistent state.
     */
    function test_removeRowFromMiddle(self) {
        self.setUp();

        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});
        self.model.setRowData(1, {__id__: 'b', baz: 'quux'});
        self.model.setRowData(2, {__id__: 'c', red: 'green'});
        self.model.setRowData(3, {__id__: 'd', blue: 'yellow'});
        self.model.setRowData(4, {__id__: 'e', white: 'black'});
        self.model.setRowData(5, {__id__: 'f', brown: 'puce'});

        /*
         * Remove something from the middle and make sure only
         * everything after it gets shuffled.
         */
        self.model.removeRow(2);

        /*
         * Things before it should have been left alone.
         */
        self.assertEqual(self.model.getRowData(0).__id__, 'a');
        self.assertEqual(self.model.getRowData(1).__id__, 'b');

        /*
         * It should be missing and things after it should have been
         * moved down one index.
         */
        self.assertEqual(self.model.getRowData(2).__id__, 'd');
        self.assertEqual(self.model.getRowData(3).__id__, 'e');
        self.assertEqual(self.model.getRowData(4).__id__, 'f');

        /*
         * There should be nothing at the previous last index, either.
         */
        var error;

        error = self.assertThrows(
            Divmod.IndexError,
            function() { self.model.getRowData(5); });
        self.assertEqual(
            error.message,
            "Specified index (5) out of bounds in getRowData.");

        /*
         * Count should have decreased by one as well.
         */
        self.assertEqual(self.model.rowCount(), 5);

        /*
         * Finding indexes from web IDs should reflect the new state as well.
         */
        self.assertEqual(self.model.findIndex('a'), 0);
        self.assertEqual(self.model.findIndex('b'), 1);
        self.assertEqual(self.model.findIndex('d'), 2);
        self.assertEqual(self.model.findIndex('e'), 3);
        self.assertEqual(self.model.findIndex('f'), 4);

        /*
         * And the removed row should not be discoverable that way.
         */
        error = self.assertThrows(
            Mantissa.ScrollTable.NoSuchWebID,
            function() { self.model.findIndex('c'); });
        self.assertEqual(error.webID, 'c');
    },

    /**
     * Test that rows can be removed from the end of the model and that the
     * model remains in a consistent state.
     */
    function test_removeRowFromEnd(self) {
        self.setUp();

        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});
        self.model.setRowData(1, {__id__: 'b', baz: 'quux'});
        self.model.setRowData(2, {__id__: 'c', red: 'green'});

        /*
         * Remove something from the middle and make sure only
         * everything after it gets shuffled.
         */
        self.model.removeRow(2);

        /*
         * Things before it should have been left alone.
         */
        self.assertEqual(self.model.getRowData(0).__id__, 'a');
        self.assertEqual(self.model.getRowData(1).__id__, 'b');

        /*
         * There should be nothing at the previous last index, either.
         */
        var error;
        error = self.assertThrows(
            Divmod.IndexError,
            function() { self.model.getRowData(2); });
        self.assertEqual(
            error.message,
            "Specified index (2) out of bounds in getRowData.");

        /*
         * Count should have decreased by one as well.
         */
        self.assertEqual(self.model.rowCount(), 2);

        /*
         * Finding indexes from web IDs should reflect the new state as well.
         */
        self.assertEqual(self.model.findIndex('a'), 0);
        self.assertEqual(self.model.findIndex('b'), 1);

        /*
         * And the removed row should not be discoverable that way.
         */
        error = self.assertThrows(
            Mantissa.ScrollTable.NoSuchWebID,
            function() { self.model.findIndex('c'); });
        self.assertEqual(error.webID, 'c');
    },

    /**
     * Test that removeRow returns an object with index and row properties
     * which refer to the appropriate objects.
     */
    function test_removeRowReturnValue(self) {
        self.setUp();

        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});

        var row = self.model.removeRow(0);
        self.assertEqual(row.__id__, 'a');
        self.assertEqual(row.foo, 'bar');
    },

    /**
     * Test that the empty method gets rid of all the rows.
     */
    function test_empty(self) {
        self.setUp();

        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});
        self.model.empty();
        self.assertEqual(self.model.rowCount(), 0);

        var error;

        error = self.assertThrows(
            Divmod.IndexError,
            function() { self.model.getRowData(0); });
        self.assertEqual(
            error.message,
            "Specified index (0) out of bounds in getRowData.");

        error = self.assertThrows(
            Mantissa.ScrollTable.NoSuchWebID,
            function() { self.model.findIndex('a'); });
        self.assertEqual(error.webID, 'a');
    });


Mantissa.Test.ScrollTableViewTestBase = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.ScrollTableViewTestBase');
Mantissa.Test.ScrollTableViewTestBase.methods(
    /**
     * Retrieve a ScrollingWidget from the server to use for the running test
     * method.
     */
    function setUp(self, testMethodName, rowCount /* = 10 */) {
        if (rowCount === undefined) {
            rowCount = 10;
        }
        var result = self.callRemote('getScrollingWidget', testMethodName, rowCount);
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                self.scrollingWidget = widget;
                self.node.appendChild(widget.node);
                return widget.initializationDeferred;
            });
        return result;
    });

Mantissa.Test.ScrollTableViewTestCase = Mantissa.Test.ScrollTableViewTestBase.subclass('Mantissa.Test.ScrollTableViewTestCase');
Mantissa.Test.ScrollTableViewTestCase.methods(
    /**
     * Test that a ScrollingWidget has a model with some rows after its
     * initialization Deferred fires.
     */
    function test_initialize(self) {
        return self.setUp('initialize', 30).addCallback(function() {
                self.assertEqual(self.scrollingWidget.model.rowCount(), 30);
            });
    },

    /**
     * Test that the scrolled method returns a Deferred which fires when some
     * rows have been requested from the server, perhaps.
     */
    function test_scrolled(self) {
        var result = self.setUp('scrolled', 30);
        result.addCallback(
            function(ignored) {
                var scrolled = self.scrollingWidget.scrolled();
                self.failUnless(scrolled instanceof Divmod.Defer.Deferred);
                return scrolled;
            });
        return result;
    },

    /**
     * Test that the scrolltable can have its elements completely dropped and
     * reloaded from the server with the L{ScrollingWidget.emptyAndRefill}
     * method.
     */
    function test_emptyAndRefill(self) {
        var result = self.setUp('emptyAndRefill', 100);
        result.addCallback(function() {
                /*
                 * Tell the server to lose some rows so that we will be able to
                 * notice emptyAndRefill() actually did something.
                 */
                return self.callRemote('changeRowCount', 'emptyAndRefill', 5);
            });
        result.addCallback(function() {
                return self.scrollingWidget.emptyAndRefill();
            });
        result.addCallback(function() {
                self.assertEqual(self.scrollingWidget.model.rowCount(), 5);
            });
        return result;
    },

    /**
     * Test that the scrolltable's empty() method removes all row nodes
     * and empties the model
     */
    function test_empty(self) {
        return self.setUp('empty', 30).addCallback(
            function() {
                self.scrollingWidget.empty();
                self.assertEqual(
                    self.scrollingWidget._scrollViewport.childNodes.length, 0);
                self.assertEqual(
                    self.scrollingWidget.model.rowCount(), 0);
            });
    },


    /**
     * Test that emptying a ScrollingWidget also resets its scroll position
     * tracking.
     */
    function test_emptyScrollPosition(self) {
        return self.setUp('emptyScrollPosition', 30).addCallback(
            function cbSetUp(ignored) {
                /*
                 * We start at the top.
                 */
                self.assertEqual(self.scrollingWidget.lastScrollPos, 0);

                /*
                 * Go down a little bit so the rest of this test is meaningful.
                 */
                var viewport = self.scrollingWidget._scrollViewport;
                var scrollTop = Math.floor(viewport.scrollHeight / 2);
                var onscroll = viewport.onscroll;
                viewport.onscroll = undefined;
                viewport.scrollTop = scrollTop;
                viewport.onscroll = onscroll;
                var scrolled = self.scrollingWidget.scrolled();
                scrolled.addCallback(
                    function cbScrolled(ignored) {
                        /*
                         * Sanity check.
                         */
                        self.assertNotEqual(
                            self.scrollingWidget.lastScrollPos, 0);

                        /*
                         * After being emptied we should be at the top again.
                         */
                        self.scrollingWidget.empty();
                        self.assertEqual(
                            self.scrollingWidget.lastScrollPos, 0);
                    });
                return scrolled;
            });
    },


    /**
     * Check that L{scrolled} behaves correctly even if it cannot get
     * some rows.
     */
    function test_scrolledWhenError(self) {
        var d = self.setUp('scrolledWhenError', 30);
        var _getSomeRows;
        d.addCallback(
            function(ignored) {
                _getSomeRows = self.scrollingWidget._getSomeRows;
                self.scrollingWidget._getSomeRows = function () {
                    return Divmod.Defer.fail(
                        Divmod.Error("deliberate failure"));
                };
                return self.scrollingWidget.scrolled();
            });
        d = self.assertFailure(d, [Divmod.Error]);
        d.addCallback(
            function(ignored) {
                self.assertEqual(self.scrollingWidget._requestWaiting,
                                 false);
            });
        d.addBoth(
            function(passthru) {
                self.scrollingWidget._getSomeRows = _getSomeRows;
                return passthru;
            });
        return d;
    },


    /**
     * Test that the scrolltable's refill method refills an empty scrolltable
     */
     function test_refill(self) {
        var assertTotalRowCount = function(count) {
            self.assertEqual(
                self.scrollingWidget.model.totalRowCount(), count);
        }
        var makeTestCallback = function(rowCount) {
            return function() {
                self.scrollingWidget.empty();
                return self.callRemote('changeRowCount', 'refill', rowCount).addCallback(
                    function() {
                        return self.scrollingWidget.refill();
                }).addCallback(
                    function() {
                        assertTotalRowCount(rowCount);
                });
            }
        }

        var D = self.setUp('refill', 10);

        D.addCallback(function() {
            assertTotalRowCount(10);
        });

        var rowCounts = [4, 40, 4];

        for(var i = 0; i < rowCounts.length; i++) {
            D.addCallback(makeTestCallback(rowCounts[i]));
        }

        return D;
    },


    /**
     * Test that removing a row from a ScrollingWidget removes it from the
     * underlying model and removes the display nodes associated with it from
     * the document.  The nodes of rows after the removed row should also have
     * their position adjusted to fill the gap.
     */
    function test_removeRow(self) {
        var result = self.setUp('removeRow', 30);
        result.addCallback(function() {
                var firstRow = self.scrollingWidget.model.getRowData(0);
                var nextRow = self.scrollingWidget.model.getRowData(2);
                var removedRow = self.scrollingWidget.removeRow(1);
                var movedRow = self.scrollingWidget.model.getRowData(1);

                self.assertEqual(nextRow.__id__, movedRow.__id__);
                self.assertEqual(removedRow.__node__.parentNode, null);

                var viewport = self.scrollingWidget._scrollViewport;
                self.assertEqual(viewport.childNodes[0], firstRow.__node__);
                self.assertEqual(viewport.childNodes[1], movedRow.__node__);
            });
        return result;
    }
    );



Mantissa.Test.FrobAction = Mantissa.ScrollTable.Action.subclass("Mantissa.Test.FrobAction");
/**
 * Action which is only enabled for even numbered rows
 */
Mantissa.Test.FrobAction.methods(
    function __init__(self) {
        Mantissa.Test.FrobAction.upcall(
            self, "__init__", "frob", "Frob");
    },

    function enableForRow(self, row) {
        return row.column % 2 == 0;
    });

Mantissa.Test.ScrollTableWithActions = Mantissa.ScrollTable.ScrollingWidget.subclass('Mantissa.Test.ScrollTableWithActions');
/**
 * L{Mantissa.ScrollTable.ScrollingWidget} subclass with two actions
 */
Mantissa.Test.ScrollTableWithActions.methods(
    function __init__(self, node, metadata) {
        /* make an action whose handler refreshes the scrolltable */
        self.deleteAction = Mantissa.ScrollTable.Action(
                                "delete", "Delete",
                                function(scrollingWidget, row, result) {
                                    return scrollingWidget.emptyAndRefill();
                                });
        self.actions = [self.deleteAction, Mantissa.Test.FrobAction()];
        Mantissa.Test.ScrollTableWithActions.upcall(self, "__init__", node, metadata);
    });

Mantissa.Test.ScrollTableActionsTestCase = Mantissa.Test.ScrollTableViewTestBase.subclass('Mantissa.Test.ScrollTableActionsTestCase');
/**
 * Test scrolltable actions
 */
Mantissa.Test.ScrollTableActionsTestCase.methods(
    /**
     * Test that the node created by L{Mantissa.ScrollTable.Action.toNode}
     * looks reasonably correct
     */
    function test_actionNode(self) {
        return self.setUp('actionNode').addCallback(
            function() {
                var scroller = self.scrollingWidget;
                var node = scroller.deleteAction.toNode(
                                scroller, scroller.model.getRowData(0));
                self.failUnless(node.onclick);
                self.assertEqual(node.firstChild.nodeValue,
                                 scroller.deleteAction.displayName);
            });
    },

    /**
     * Test that remote actions do what they're supposed to
     */
    function test_actions(self) {
        return self.setUp('actions').addCallback(
            function() {
                var scroller = self.scrollingWidget;
                var rowData = scroller.model.getRowData(0);
                var D = scroller.deleteAction.enact(scroller, rowData);
                return D.addCallback(
                    function() {
                        self.assertThrows(
                            Mantissa.ScrollTable.NoSuchWebID,
                            function() {
                                alert(scroller.model.findIndex(rowData.__id__));
                            });

                    });
            });
    },

    /**
     *  Test that L{Mantissa.ScrollTable.Action.enableForRow} works
     */
    function test_enablement(self) {
        return self.setUp('enablement').addCallback(
            function() {
                var scroller = self.scrollingWidget;

                /* even number, no "Frob" action */
                var actions = scroller.getActionsForRow(
                                scroller.model.getRowData(1));

                self.assertEqual(actions.length, 1);
                self.assertEqual(actions[0].name, "delete");

                /* odd number, "Frob" action */
                actions = scroller.getActionsForRow(
                                scroller.model.getRowData(2));

                self.assertEqual(actions.length, 2);
                self.assertEqual(actions[0].name, "delete");
                self.assertEqual(actions[1].name, "frob");
            });
    });

Mantissa.Test.ScrollTablePlaceholderRowsTestCase = Mantissa.Test.ScrollTableViewTestBase.subclass('Mantissa.Test.ScrollTablePlaceholderRowsTestCase');
/**
 * Tests for the behaviour of L{Mantissa.ScrollTable.ScrollingWidget} with
 * regard to placeholder rows
 */
Mantissa.Test.ScrollTablePlaceholderRowsTestCase.methods(
    /**
     * Check that the structure of placeholder rows in C{self.scrollingWidget}
     * match the objects in C{expected}
     *
     * @param expected: array of objects with "start" and "stop" members,
     * which correspond to the objects in
     * L{Mantissa.ScrollTable.ScrollingWidget}'s placeholder range list
     */
    function _checkPlaceholders(self, expected) {
        var pmodel = self.scrollingWidget.placeholderModel;
        self.assertEqual(expected.length, pmodel.getPlaceholderCount());
        for(var placeholder, i = 0; i < expected.length; i++) {
            placeholder = pmodel.getPlaceholderWithIndex(i);
            if(placeholder.start != expected[i].start ||
                placeholder.stop != expected[i].stop) {
                self.fail("expected start/stop of " +
                            [expected[i].start, expected[i].stop].toSource() +
                            " but got " +
                            [placeholder.start, placeholder.stop].toSource());
            }
        }
    },

    function _prepareScrolltable(self) {
        /* we want to emulate the initial row loading process, while
         * being in control of exactly how many rows get added at what
         * time, instead of depending on the relative heights of the
         * rows and the viewport, so we empty the scrolltable after
         * the initial load. */
        self.scrollingWidget.empty();

        /* and add one big placeholder row */
        self.scrollingWidget.padViewportWithPlaceholderRow(
            self.scrollingWidget.model.totalRowCount());

        /* which is the same situation as when the scrolltable has got
         * the table metadata (number of rows, etc) but hasn't yet
         * requested any */
        self.assertEqual(self.scrollingWidget.model.rowCount(), 0);
    },

    /**
     * Test that storing a row splits the initial placeholder
     */
    function test_storingARowSplitsInitialPlaceholder(self) {
        return self.setUp('storingARowSplitsInitialPlaceholder', 100).addCallback(
            function() {
                var scroller = self.scrollingWidget;

                self._prepareScrolltable(scroller);

                /* make one row at offset #1 */
                scroller._storeRows(1, 1, [{column: "1", __id__: "1"}]);

                /* which should split the placeholder row into two - one
                 * extending from 0-1 and one from 2-100 */
                self._checkPlaceholders([{start: 0, stop: 1}, {start: 2, stop: 100}]);
            });
    },

    /**
     * Test storing two rows in the middle of a placeholder splits it
     */
    function test_storingRowsSplitsPlaceholder(self) {
        return self.setUp('storingRowsSplitsPlaceholder', 100).addCallback(
            function() {
                var scroller = self.scrollingWidget;

                self._prepareScrolltable(scroller);

                /* make one row to split the placeholder */
                scroller._storeRows(1, 1, [{column: "1", __id__: "1"}]);

                /* put another row right after the last one */
                scroller._storeRows(2, 2, [{column: "2", __id__: "2"}]);

                /* number of placeholders shouldn't have changed, since we
                 * didn't need to split any, just needed to adjust the height of
                 * one */
                self._checkPlaceholders([{start: 0, stop: 1}, {start: 3, stop: 100}]);

                /* put another row two rows after the last one */
                scroller._storeRows(4, 4, [{column: "4", __id__: "4"}]);

                /* which should split the 3-100 placeholder */
                self._checkPlaceholders([{start: 0, stop: 1},
                                         {start: 3, stop: 4},
                                         {start: 5, stop: 100}]);
        });
    },

    /**
     * Test that storing rows at the end of the scrolltable shortens the last
     * placeholder
     */
    function test_storingRowsAtEndShortensLastPlaceholder(self) {
        return self.setUp('storingRowsAtEndShortsLastPlaceholder', 100).addCallback(
            function () {
                var scroller = self.scrollingWidget;

                self._prepareScrolltable(scroller);

                scroller._storeRows(1, 1, [{column: "1", __id__: "1"}]);

                /* put 2 rows at the end */
                scroller._storeRows(98, 99, [{column: "98", __id__: "98"},
                                             {column: "99", __id__: "99"}]);

                /* which should shorten the last placeholder */
                self._checkPlaceholders([{start: 0, stop: 1},
                                         {start: 2, stop: 98}]);
            });
    },

    /**
     * Test that the number of placeholder rows and their heights match what
     * we expect.  Do this by looking at the DOM.
     */
    function test_placeholderNodes(self) {
        return self.setUp('placeholderNodes', 100).addCallback(
            function() {
                var scroller = self.scrollingWidget;
                var sviewport = scroller._scrollViewport;

                scroller.empty();
                scroller.padViewportWithPlaceholderRow(
                    scroller.model.totalRowCount());

                self.assertEqual(sviewport.childNodes.length, 1);
                self.assertEqual(parseInt(sviewport.firstChild.style.height),
                                 (scroller.model.totalRowCount()
                                    * scroller._rowHeight));
                self.assertEqual(sviewport.firstChild.className,
                                 "placeholder-scroll-row");

                /* split the placeholder */
                scroller._storeRows(1, 1, [{column: "1", __id__: "1"}]);

                self.assertEqual(sviewport.childNodes.length, 3);
                self.assertEqual(sviewport.firstChild.className,
                                 "placeholder-scroll-row");
                self.assertEqual(parseInt(sviewport.firstChild.style.height),
                                 scroller._rowHeight);

                /* the second row should be the one we inserted, not a
                 * placeholder */
                self.assertEqual(sviewport.childNodes[1].className,
                                 "scroll-row");

                self.assertEqual(sviewport.childNodes[2].className,
                                 "placeholder-scroll-row");
                self.assertEqual(parseInt(sviewport.childNodes[2].style.height),
                                 ((scroller.model.totalRowCount() - 2)
                                    * scroller._rowHeight));
            });
    },

    /**
     * For a scrolltable like this:
     * | X: REAL ROW    |
     * | Y: PLACEHOLDER |
     * | Z: REAL ROW    |
     * Check that the placeholder is removed, and no more placeholders are
     * created when the row at index Y is populated
     */
    function test_surroundedRow(self) {
        return self.setUp('surroundedRow', 100).addCallback(
            function() {
                var scroller = self.scrollingWidget;

                scroller.empty();
                scroller.padViewportWithPlaceholderRow(scroller.model.totalRowCount());

                scroller._storeRows(0, 0, [{column: "0", __id__: "0"}]);
                scroller._storeRows(2, 2, [{column: "2", __id__: "2"}]);

                /* now index 1 should be a placeholder */
                self._checkPlaceholders([{start: 1, stop: 2}, {start: 3, stop: 100}]);

                /* insert a row there */
                scroller._storeRows(1, 1, [{column: "1", __id__: "1"}]);

                /* and the placeholder should be gone entirely */
                self._checkPlaceholders([{start: 3, stop: 100}]);
            });
    },

    /**
     * Store C{howMany} consecutive rows in our scrolltable, with the first at
     * index C{startingAt}
     *
     * @param startingAt: index of first row
     * @type startingAt: integer
     *
     * @param howMany: number of rows
     * @type howMany: integer
     */
    function _storeConsecutiveRows(self, startingAt, howMany) {
        var rows = [];
        for(var i = startingAt; i < startingAt+howMany; i++) {
            rows.push({column: i.toString(), __id__: toString()});
        }
        self.scrollingWidget._storeRows(startingAt, startingAt+howMany, rows);
    },

    /**
     * Test that L{Mantissa.ScrollTable.ScrollingWidget.removeRow} correctly
     * modifies the start/stop indices of placeholders that start after the
     * index of the removed row
     */
    function test_removeRow(self) {
        return self.setUp('removeRow', 100).addCallback(
            function() {
                var scroller = self.scrollingWidget;

                scroller.empty();
                scroller.padViewportWithPlaceholderRow(scroller.model.totalRowCount());

                self._storeConsecutiveRows(0, 10);

                self._checkPlaceholders([{start: 10, stop: 100}]);

                scroller.removeRow(0);

                self._checkPlaceholders([{start: 9, stop: 99}]);
            });
    },

    /**
     * Same as C{test_removeRow}, but remove multiple rows and fill the
     * scrolltable
     */
    function test_removeRow2(self) {
        return self.setUp('removeRow2', 100).addCallback(
            function() {
                var scroller = self.scrollingWidget;

                scroller.empty();
                scroller.padViewportWithPlaceholderRow(scroller.model.totalRowCount());

                self._storeConsecutiveRows(0, 10);

                scroller.removeRow(0);

                self._storeConsecutiveRows(9, 90);

                scroller.removeRow(82);

                self._checkPlaceholders([]);
            });
    });


Mantissa.Test.GeneralPrefs = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.GeneralPrefs');
/**
 * Client-side half of xmantissa.test.livetest_prefs.GeneralPrefs
 */
Mantissa.Test.GeneralPrefs.methods(
    /**
     * Change the values of our preferences, submit the form,
     * and then call the python class with the new values so
     * it can make sure it agrees with us
     */
    function test_persistence(self) {
        /**
         * Change the value of the <select> with name C{inputName}
         * by selecting the first <option> inside it which doesn't
         * represent the current value.
         */
        var changeSelectValue = function(inputName) {
            var input = self.firstNodeByAttribute("name", inputName);
            var options = input.getElementsByTagName("option");
            for(var i = 0; i < options.length; i++) {
                if(options[i].value != input.value) {
                    input.selectedIndex = i;
                    /* ChoiceInput sets the value of the options
                     * to their offset in the choice list, so we
                     * don't want to use that */
                    return options[i].firstChild.nodeValue;
                }
            }
        }

        var itemsPerPageValue = parseInt(changeSelectValue("itemsPerPage"));
        var timezoneValue = changeSelectValue("timezone");
        timezoneValue = timezoneValue.replace(/^\s+/, "").replace(/\s+$/, "");

        var liveform = Nevow.Athena.Widget.get(
                        self.firstNodeByAttribute(
                            "athena:class",
                            "Mantissa.Preferences.PrefCollectionLiveForm"));

        return liveform.submit().addCallback(
            function() {
                return self.callRemote("checkPersisted", itemsPerPageValue, timezoneValue);
            });
    });


Mantissa.Test.PrefCollectionTestCase = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.PrefCollectionTestCase');
Mantissa.Test.PrefCollectionTestCase.methods(
    /**
     * Test that the original form remains unchanged after the submit button
     * is pressed.
     */
    function test_submitPreservesForm(self) {
        var widget = self.childWidgets[0];
        var html = MochiKit.DOM.toHTML(widget.node);
        var d = widget.submit();
        d.addCallback(
            function(ignored) {
                self.assertEqual(MochiKit.DOM.toHTML(widget.node), html);
            });
        return d;
    });


Mantissa.Test.UserBrowserTestCase = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.UserBrowserTestCase');
Mantissa.Test.UserBrowserTestCase.methods(
    /**
     * Retrieve a LocalUserBrowser from the server and add it as a child to
     * ourself.  Return a Deferred which fires when this has been completed.
     */
    function setUp(self) {
        var result = self.callRemote('getUserBrowser');
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                self.userBrowser = widget;
            });
        return result;
    },

    function _endowDepriveFormTest(self, action) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.userBrowser._updateUserDetail(0, 'action');
            });
        result.addCallback(
            function(ignored) {
                var childWidgets = self.userBrowser.childWidgets;
                var fragment = childWidgets[childWidgets.length - 1];
                childWidgets = fragment.childWidgets;
                var form = childWidgets[childWidgets.length - 1];
                self.failUnless(form instanceof Mantissa.LiveForm.FormWidget);

            });
        return result;
    },

    /**
     * Test that an endow form can be summoned by acting on a row in the user
     * browser.
     */
    function test_endowFormCreation(self) {
        return self._endowDepriveFormTest('endow');
    },

    /**
     * Similar to L{test_depriveFormCreation}, but for the deprive form rather
     * than the endow form.
     */
    function test_depriveFormCreation(self) {
        return self._endowDepriveFormTest('deprive');
    });


Mantissa.Test.EchoingFormWidget = Mantissa.LiveForm.FormWidget.subclass('Mantissa.Test.EchoingFormWidget');
/**
 * Trivial L{Mantissa.LiveForm.FormWidget} subclass which renders the response
 * provided to the success handler
 */
Mantissa.Test.EchoingFormWidget.methods(
    /**
     * Don't reset on form submission.
     */
    function reset(self) {
    },

    function submitSuccess(self, result) {
        var div = document.createElement("div");
        div.appendChild(document.createTextNode(result));
        document.body.appendChild(div);
        return Mantissa.Test.EchoingFormWidget.upcall(
            self, 'submitSuccess', result);
    });
