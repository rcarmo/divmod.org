// import Nevow.Athena.Test

// import Quotient.Throbber
// import Quotient.Message
// import Quotient.Mailbox
// import Quotient.Compose

Nevow.Athena.Test.TestCase.subclass(Quotient.Test, '_QuotientTestBase').methods(
    /**
     * Construct and return a string giving a relative URL to the Quotient
     * static content indicated by C{path}.
     */
    function staticURL(self, path) {
        return '/static/Quotient' + path;
    });



Quotient.Test.ThrobberTestCase = Nevow.Athena.Test.TestCase.subclass('Quotient.Test.ThrobberTestCase');
Quotient.Test.ThrobberTestCase.methods(
    function setUp(self) {
        self.throbberNode = document.createElement('div');
        self.throbberNode.style.display = 'block';
        self.node.appendChild(self.throbberNode);
        self.throbber = Quotient.Throbber.Throbber(self.throbberNode);
    },

    /**
     * Test that the L{Throbber.startThrobbing} method sets the wrapped node's
     * style so that it is visible.
     */
    function test_startThrobbing(self) {
        self.setUp();

        self.throbber.startThrobbing();
        self.assertEqual(self.throbberNode.style.display, '');
    },

    /**
     * Test that the L{Throbber.stopThrobbing} method sets the wrapped node's
     * style so that it is invisible.
     */
    function test_stopThrobbing(self) {
        self.setUp();

        self.throbber.stopThrobbing();
        self.assertEqual(self.throbberNode.style.display, 'none');
    });


/**
 * Testable stand-in for the real throbber class.  Used by tests to assert that
 * the throbber is manipulated properly.
 */
Quotient.Test.TestThrobber = Divmod.Class.subclass("Quotient.Test.TestThrobber");
Quotient.Test.TestThrobber.methods(
    function __init__(self) {
        self.throbbing = false;
    },

    function startThrobbing(self) {
        self.throbbing = true;
    },

    function stopThrobbing(self) {
        self.throbbing = false;
    });


/**
 * Tests for L{Quotient.Mailbox.Status}
 */
Quotient.Test.MailboxStatusTestCase = Nevow.Athena.Test.TestCase.subclass('Quotient.Test.MailboxStatusTestCase');
Quotient.Test.MailboxStatusTestCase.methods(
    /**
     * Make a node that contains the stuff that the status widget wants, and
     * return a status widget
     */
    function setUp(self) {
        var node = document.createElement('div'),
            throbber = document.createElement('div'),
            status = document.createElement('div');

        throbber.className = 'throbber';
        throbber.style.display = 'none';
        node.appendChild(throbber);

        status.className = 'mailbox-status';
        node.appendChild(status);

        self.node.appendChild(node);

        self.throbberNode = throbber;
        self.statusNode = status;

        return Quotient.Mailbox.Status(node);
    },

    /**
     * Test L{Quotient.Mailbox.Status.showStatusUntilFires}
     */
    function test_showStatusUntilFires(self) {
        var statusWidget = self.setUp();

        self.assertEqual(self.throbberNode.style.display, "none");
        self.assertEqual(self.statusNode.childNodes.length, 0);

        var deferred = Divmod.Defer.Deferred();

        var STATUS_MSG = "A message";

        statusWidget.showStatusUntilFires(deferred, STATUS_MSG);

        self.assertEqual(self.throbberNode.style.display, "");
        self.assertEqual(self.statusNode.childNodes.length, 1);
        self.assertEqual(self.statusNode.firstChild.nodeValue, STATUS_MSG);

        var CALLBACK_VALUE = 624;

        deferred.addCallback(
            function(result) {
                self.assertEqual(result, CALLBACK_VALUE);

                self.assertEqual(self.throbberNode.style.display, "none");
                self.assertEqual(self.statusNode.childNodes.length, 0);
            });

        deferred.callback(CALLBACK_VALUE);
        return deferred;
    });



Quotient.Test.ScrollTableTestCase = Nevow.Athena.Test.TestCase.subclass('Quotient.Test.ScrollTableTestCase');
Quotient.Test.ScrollTableTestCase.methods(
    /**
     * Find the ScrollWidget which is a child of this test and save it as a
     * convenient attribute for test methods to use.
     */
    function setUp(self) {
        self.scrollWidget = null;
        for (var i = 0; i < self.childWidgets.length; ++i) {
            if (self.childWidgets[i] instanceof Quotient.Mailbox.ScrollingWidget) {
                self.scrollWidget = self.childWidgets[i];
                break;
            }
        }
        self.assertNotEqual(self.scrollWidget, null, "Could not find ScrollingWidget.")
    },
    /**
     * Test receipt of timestamps from the server and their formatting.
     */
    function test_massageTimestamp(self) {
        self.setUp();
        self.callRemote('getTimestamp').addCallback(function (timestamp) {
                var date = new Date(timestamp*1000);
                self.assertEqual(self.scrollWidget.massageColumnValue(
                            "", "timestamp",
                            timestamp + date.getTimezoneOffset() * 60),
                                 "12:00 AM")});
    },
    /**
     * Test the custom date formatting method used by the Mailbox ScrollTable.
     */
    function test_formatDate(self) {
        self.setUp();

        var now;

        /*
         * August 21, 2006, 1:36:10 PM
         */
        var when = new Date(2006, 7, 21, 13, 36, 10);

        /*
         * August 21, 2006, 5:00 PM
         */
        now = new Date(2006, 7, 21, 17, 0, 0);
        self.assertEqual(
            self.scrollWidget.formatDate(when, now), '1:36 PM',
            "Different hour context failed.");

        self.assertEqual(
            self.scrollWidget.formatDate(new Date(2006, 7, 21, 13, 1, 10),
                                         now), '1:01 PM');
        /*
         * August 22, 2006, 12:00 PM
         */
        now = new Date(2006, 7, 22, 12, 0, 0);
        self.assertEqual(
            self.scrollWidget.formatDate(when, now), 'Aug 21',
            "Different day context failed.");

        /*
         * September 22, 2006, 12:00 PM
         */
        now = new Date(2006, 8, 22, 12, 0, 0);
        self.assertEqual(
            self.scrollWidget.formatDate(when, now), 'Aug 21',
            "Different month context failed.");

        /*
         * January 12, 2007, 9:00 AM
         */
        now = new Date(2007, 1, 12, 9, 0, 0);
        self.assertEqual(
            self.scrollWidget.formatDate(when, now), '2006-08-21',
            "Different year context failed.");
    });


Quotient.Test._QuotientTestBase.subclass(Quotient.Test, 'ScrollingWidgetTestCase').methods(
    function setUp(self) {
        var result = self.callRemote('getScrollingWidget', 5);
        result.addCallback(function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(function(widget) {
                self.scrollingWidget = widget;
                self.node.appendChild(widget.node);

                /*
                 * XXX Clobber these methods, since our ScrollingWidget doesn't
                 * have a widgetParent which implements the necessary methods.
                 */
                widget.decrementActiveMailViewCount = function() {};

                return widget.initializationDeferred;
            });
        return result;
    },


    /**
     * Test that a row can be added to the group selection with
     * L{ScrollingWidget.groupSelectRow}.
     */
    function test_groupSelectRow(self) {
        return self.setUp().addCallback(function() {
                var widget = self.scrollingWidget;
                var model = widget.model;
                var webID = model.getRowData(0).__id__;
                widget.groupSelectRow(webID);
                self.failUnless(
                    model.isSelected(webID),
                    "Expected selected webID to be selected.");
            });
    },

    /**
     * Test that a row can be removed from the group selection with
     * L{ScrollingWidget.groupSelectRow}.
     */
    function test_groupUnselectRow(self) {
        return self.setUp().addCallback(function() {
                var widget = self.scrollingWidget;
                var model = widget.model;
                var webID = model.getRowData(0).__id__;
                model.selectRow(webID);
                widget.groupSelectRow(webID);
                self.failIf(
                    model.isSelected(webID),
                    "Expected selected webID to not be selected.");
            });
    },

    /**
     * Test that the height of the node returned by
     * L{Quotient.Mailbox.ScrollingWidget._getRowGuineaPig} isn't set
     */
    function test_guineaPigHeight(self) {
        var result = self.setUp();
        result.addCallback(
            function() {
                var row = self.scrollingWidget._getRowGuineaPig();
                self.failIf(row.style.height);
                var div = row.getElementsByTagName("div")[0];
                self.failIf(div.style.height);
            });
        return result;
    },


    /**
     * Test that the DOM for a row without 'everDeferred' has no boomerang.
     */
    function test_noBoomerang(self) {
        var d = self.setUp();
        return d.addCallback(
            function(ignored) {
                var data = self.scrollingWidget.model.getRowData(0);
                // sanity check
                self.assertEqual(data['everDeferred'], false);
                var dom = self.scrollingWidget.findCellElement(data);
                Divmod.msg(MochiKit.DOM.emitHTML(dom));
                self.assertEqual(dom.childNodes.length, 2);
            });
    },


    /**
     * Test that the DOM for a row with 'everDeferred' contains an image
     * of a boomerang.
     */
    function test_deferredHasBoomerang(self) {
        var d = self.setUp();
        return d.addCallback(
            function(ignored) {
                var data = self.scrollingWidget.model.getRowData(0);
                data['everDeferred'] = true;
                var dom = self.scrollingWidget.makeCellElement('senderDisplay',
                                                               data);
                self.assertEqual(dom.childNodes[2].getAttribute('src'),
                                 self.staticURL('/images/boomerang.gif'));
            });
    },


    /**
     * Test that we can add a boomerang and an 'everDeferred' status to a
     * row after it has been built.
     */
    function test_deferredGainsBoomerang(self) {
        var d = self.setUp();
        return d.addCallback(
            function(ignored) {
                var data = self.scrollingWidget.model.getRowData(0);
                self.scrollingWidget.setAsDeferred(data);
                self.assertEqual(data['everDeferred'], true);
                var dom = self.scrollingWidget.findCellElement(data);
                self.assertEqual(dom.childNodes[2].getAttribute('src'),
                                 self.staticURL('/images/boomerang.gif'));
            });
    },


    /**
     * Test that 'setAsDeferred' is idempotent.
     */
    function test_onlyOneBoomerang(self) {
        var d = self.setUp();
        return d.addCallback(
            function(ignored) {
                var data = self.scrollingWidget.model.getRowData(0);
                var dom = self.scrollingWidget.findCellElement(data);
                self.scrollingWidget.setAsDeferred(data);
                self.assertEqual(dom.childNodes.length, 3);
                self.scrollingWidget.setAsDeferred(data);
                self.assertEqual(dom.childNodes.length, 3);
            });
    });


/**
 * Fetch the message detail widget off the page.
 */
Quotient.Test._getMessageDetail = function _getMessageDetail(self) {
    return Quotient.Message.MessageDetail.get(
        self.controllerWidget.firstWithClass(
            self.controllerWidget.messageDetail,
            "message-detail-fragment"));
},

Quotient.Test._QuotientTestBase.subclass(Quotient.Test, 'ControllerTestCase').methods(
    /**
     * Utility method to extract data from display nodes and return it as an
     * array of objects mapping column names to values.
     */
    function collectRows(self) {
        var rows = self.controllerWidget.scrollWidget.nodesByAttribute(
            "class", "q-scroll-row");
        var divs, j, row;
        for (var i = 0; i < rows.length; i++) {
            divs = rows[i].getElementsByTagName("div");
            row = {};
            for (j = 0; j < divs.length; j++) {
                row[divs[j].className] = divs[j].firstChild.nodeValue;
            }
            rows[i] = row;
        }
        return rows;
    },

    /**
     * Retrieve a Controller Widget for an inbox from the server.
     */
    function setUp(self) {
        var result = self.callRemote('getControllerWidget');
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(function(widget) {
                self.controllerWidget = widget;
                self.node.appendChild(widget.node);
                /*
                 * Wait for the controller to be fully initialized.  This
                 * includes its ScrollingWidget.
                 */
                return self.controllerWidget.initializationDeferred;
            });
        return result;
    },


    /**
     * Test that L{Quotient.Mailbox.Controller.selectFilterChoiceNode}
     * properly selects the choice it is asked to
     */
    function test_selectFilterChoiceNode(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                var node = document.createElement('div');
                node.className = 'foo-chooser';

                function makeOption(name) {
                    var opt = document.createElement('div');
                    opt.className = 'list-option';
                    var optName = document.createElement('div');
                    optName.className = 'opt-name';
                    optName.appendChild(document.createTextNode(name));
                    opt.appendChild(optName);
                    return opt;
                }

                var optOne = makeOption('option 1');
                node.appendChild(optOne);
                var optTwo = makeOption('option 2');
                node.appendChild(optTwo);

                self.controllerWidget.node.appendChild(node);

                self.controllerWidget.selectFilterChoiceNode(
                    'foo', 'option 1');

                self.assertEqual(optOne.className, 'selected-list-option');
                self.assertEqual(optTwo.className, 'list-option');
            });
        return result;
    },

    /**
     * Test viewing message source and getting back to the message body
     */
    function test_messageSource(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.messageAction_messageSource();
            });
        result.addCallback(
            function(ignored) {
                /* should be a Quotient.Message.Source inside the mailbox */
                var source = Nevow.Athena.Widget.get(
                    self.controllerWidget.firstNodeByAttribute(
                        "athena:class",
                        "Quotient.Message.Source"));

                source.cancel();

                /* no more Quotient.Message.Source */
                self.assertEqual(source.node.parentNode, null);
            });
        return result;
    },

    /**
     * Test that the right-padding of the mailbox widget is equal to the
     * width of the mantissa search box
     */
    function test_searchBox(self) {
        var searchBox = document.createElement("div");
        searchBox.style.width = "200px";
        var searchButton = document.createElement("div");
        searchButton.id = "search-button";
        searchBox.appendChild(searchButton);
        document.body.appendChild(searchBox);

        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                var ctc = self.controllerWidget.firstNodeByAttribute(
                    "class", "content-table-container");
                self.assertEqual(ctc.style.paddingRight, "200px");
            });
        result.addBoth(
            function(passthrough) {
                document.body.removeChild(searchBox);
                return passthrough;
            });
        return result;
    },

    /**
     * Test that there is no right-padding on the mailbox widget if there is
     * no search box
     */
    function test_noSearchBox(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                var ctc = self.controllerWidget.firstNodeByAttribute(
                    "class", "content-table-container");
                self.assertEqual(ctc.style.paddingRight, "");
            });
        return result;
    },

    /**
     * Test that the L{getPeople} method returns an Array of objects describing
     * the people names visible.
     */
    function test_getPeople(self) {
        var result = self.setUp();
        result.addCallback(function(ignored) {
                var people = self.controllerWidget.getPeople();
                people.sort(function(a, b) {
                        if (a.name < b.name) {
                            return -1;
                        } else if (a.name == b.name) {
                            return 0;
                        } else {
                            return 1;
                        }
                    });
                self.assertEqual(people.length, 2);

                self.assertEqual(people[0].name, 'Alice');
                self.assertEqual(people[1].name, 'Bob');

                /*
                 * Check that the keys are actually associated with these
                 * people.
                 */
                var result = self.callRemote('personNamesByKeys',
                                             people[0].key, people[1].key);
                result.addCallback(function(names) {
                        self.assertArraysEqual(names, ['Alice', 'Bob']);
                    });
                return result;

            });
        return result;
    },

    /**
     * Test that the unread counts associated with various views are correct.
     * The specific values used here are based on the initialization the server
     * does.
     */
    function test_unreadCounts(self) {
        return self.setUp().addCallback(function(ignored) {
                self.assertEqual(
                    self.controllerWidget.getUnreadCountForView("inbox"), 1);

                self.assertEqual(
                    self.controllerWidget.getUnreadCountForView("spam"), 1);

                self.assertEqual(
                    self.controllerWidget.getUnreadCountForView("all"), 2);

                self.assertEqual(
                    self.controllerWidget.getUnreadCountForView("sent"), 0);
            });
    },

    /**
     * Test the mutation function for unread counts by view.
     */
    function test_setUnreadCounts(self) {
        return self.setUp().addCallback(function(ignored) {
                self.controllerWidget.setUnreadCountForView("inbox", 7);
                self.assertEquals(self.controllerWidget.getUnreadCountForView("inbox"), 7);
            });
    },

    /**
     * Test that the correct subjects show up in the view.
     */
    function test_subjects(self) {
        var result = self.setUp();
        result.addCallback(function(ignored) {
                var rows = self.collectRows();

                self.assertEqual(
                    rows.length, 2,
                    "Should have been 2 rows in the initial inbox view.");

                self.assertEquals(rows[0]["subject"], "2nd message");
                self.assertEquals(rows[1]["subject"], "1st message");
            });
        return result;
    },

    /**
     * Test that the correct dates show up in the view.
     */
    function test_dates(self) {
        var result = self.setUp();
        result.addCallback(function(ignored) {
                var rows = self.collectRows();

                self.assertEqual(
                    rows.length, 2,
                    "Should have been 2 rows in the initial inbox view.");

                /*
                 * Account for timezone differences.
                 */
                var date = new Date(
                    new Date(1999, 12, 13, 0, 0).valueOf() -
                    new Date().getTimezoneOffset() * 100000).getDate();

                self.assertEquals(rows[0]["date"], "1999-12-" + date);
                self.assertEquals(rows[1]["date"], "4:05 PM");
            });
        return result;
    },

    /**
     * Test that the correct list of people shows up in the chooser.
     */
    function test_people(self) {
        var result = self.setUp();
        result.addCallback(function(ignored) {
                var nodesByClass = function nodesByClass(root, value) {
                    return Divmod.Runtime.theRuntime.nodesByAttribute(
                        root, 'class', value);
                };
                /*
                 * Find the node which lets users select to view messages from
                 * a particular person.
                 */
                var viewSelectionNode = self.controllerWidget.contentTableGrid[0][0];
                var personChooser = nodesByClass(
                    viewSelectionNode, "person-chooser")[0];

                /*
                 * Get the nodes with the names of the people in the chooser.
                 */
                var personChoices = nodesByClass(personChooser, "list-option");

                /*
                 * Get the names out of those nodes.
                 */
                var personNames = [];
                var personNode = null;
                for (var i = 0; i < personChoices.length; ++i) {
                    personNode = nodesByClass(personChoices[i], "opt-name")[0];
                    personNames.push(personNode.firstChild.nodeValue);
                }

                personNames.sort();
                self.assertArraysEqual(personNames, ["Alice", "Bob"]);
            });
        return result;
    },


    /**
     * Test that we have all of the expected views in no particular order.
     */
    function test_viewNodes(self) {
        var nodes = Divmod.dir(self.controllerWidget.mailViewNodes);
        nodes.sort();
        var expected = ["all", "inbox", "archive", "draft", "spam", "deferred",
                        "bounce", "outbox", "sent", "trash", "focus"];
        expected.sort();
        self.assertArraysEqual(nodes, expected);
    },


    /**
     * Test that the expected views are selectable and that they are in the
     * right order.
     */
    function test_mailViewSelect(self) {
        var node = self.controllerWidget.viewShortcutSelect;
        var options = MochiKit.Base.map(
            function(x) { return x.value; },
            node.getElementsByTagName('option'));
        self.assertArraysEqual(options,
                               ['inbox', 'all', 'focus', 'archive', 'deferred',
                                'draft', 'outbox', 'bounce', 'sent', 'spam',
                                'trash']);
    },


    /**
     * Test switching to the archive view.
     */
    function test_archiveView(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.chooseMailView('archive');
            });
        result.addCallback(
            function(ignored) {
                var rows = self.collectRows();

                self.assertEqual(
                    rows.length, 2,
                    "Should have been 2 rows in the archive view.");

                self.assertEqual(rows[0]["subject"], "3rd message");
                self.assertEqual(rows[1]["subject"], "4th message");
            });
        return result;
    },


    /**
     * Test switching to the 'outbox' view.
     */
    function test_outboxView(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.chooseMailView('outbox');
            });
        result.addCallback(
            function(ignored) {
                var rows = self.collectRows();
                self.assertEqual(rows.length, 0);
            });
        return result;
    },


    /**
     * Test switching to the 'bounce' view.
     */
    function test_bounceView(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.chooseMailView('bounce');
            });
        result.addCallback(
            function(ignored) {
                var rows = self.collectRows();
                self.assertEqual(rows.length, 0);
            });
        return result;
    },


    /**
     * Test switching to the 'draft' view.
     */
    function test_draftView(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.chooseMailView('draft');
            });
        result.addCallback(
            function(ignored) {
                var rows = self.collectRows();
                self.assertEqual(rows.length, 0);
            });
        return result;
    },

    /**
     * Test switching to the 'all messages' view.
     */
    function test_allView(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.chooseMailView('all');
            });
        result.addCallback(
            function(ignored) {
                var rows = self.collectRows();

                self.assertEqual(
                    rows.length, 4,
                    "Should have been 4 rows in the 'all messages' view.");

                self.assertEqual(rows[0]["subject"], "1st message");
                self.assertEqual(rows[1]["subject"], "2nd message");
                self.assertEqual(rows[2]["subject"], "3rd message");
                self.assertEqual(rows[3]["subject"], "4th message");
            });
        return result;
    },


    /**
     * Test switching to the spam view.
     */
    function test_spamView(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.chooseMailView('spam');
            });
        result.addCallback(
            function(ignored) {
                var rows = self.collectRows();

                self.assertEqual(
                    rows.length, 1,
                    "Should have been 1 row in the spam view.");

                self.assertEqual(rows[0]["subject"], "5th message");
            });
        return result;
    },

    /**
     * Test switching to the sent view.
     */
    function test_sentView(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.chooseMailView('sent');
            });
        result.addCallback(
            function(ignored) {
                var rows = self.collectRows();

                self.assertEqual(
                    rows.length, 1,
                    "Should have been 1 row in the sent view.");

                self.assertEqual(rows[0]["subject"], "6th message");
            });
        return result;
    },

    /**
     * Check that there is a checkbox in the 'sent' scrolltable rows
     */
    function test_sentViewCheckbox(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.chooseMailView('sent');
            });
        result.addCallback(
            function(ignored) {
                var rows = self.controllerWidget.scrollWidget.nodesByAttribute(
                    "class", "q-scroll-row");
                for(var i = 0; i < rows.length; i++) {
                    self.assertEqual(
                        Nevow.Athena.NodesByAttribute(
                            rows[i], "class", "checkbox-image").length,
                        1);
                }
        });
        return result;
    },

    /**
     * Test that the sent view has a "to" column instead of a "from" column.
     */
    function test_sentViewToColumn(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                /* Sanity check - sender should be displayed in this view.
                 */
                self.failIf(
                    self.controllerWidget.scrollWidget.skipColumn(
                        "senderDisplay"));
                self.failUnless(
                    self.controllerWidget.scrollWidget.skipColumn(
                        "recipient"));

                return self.controllerWidget.chooseMailView("sent");
            });
        result.addCallback(
            function(ignored) {
                var scrollWidget = self.controllerWidget.scrollWidget;

                self.failUnless(
                    self.controllerWidget.scrollWidget.skipColumn(
                        "senderDisplay"));
                self.failIf(
                    self.controllerWidget.scrollWidget.skipColumn(
                        "recipient"));

                /* Make sure the values are correct.
                 */
                var node = scrollWidget.model.getRowData(0).__node__;
                self.assertNotEqual(
                    node.innerHTML.indexOf('alice@example.com'),
                    -1);
            });
        return result;
    },

    /**
     * Check that we are in the "Messages from Alice" view, based on the
     * subjects of the messages we can see
     */
    function _checkInAliceView(self) {
        var rows = self.collectRows();

        self.assertEquals(
            rows.length, 4, "Should have been 4 rows in Alice view.");

        /* not a touch once view, so messages should be newest to oldest */
        self.assertEquals(rows[0]["subject"], "1st message");
        self.assertEquals(rows[1]["subject"], "2nd message");
        self.assertEquals(rows[2]["subject"], "3rd message");
        self.assertEquals(rows[3]["subject"], "4th message");
    },

    /**
     * Test switching to a view of messages from a particular person.
     */
    function test_personView(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                var people = self.controllerWidget.getPeople();

                /*
                 * I know the first one is Alice, but I'll make sure.
                 */
                self.assertEqual(people[0].name, 'Alice');

                /*
                 * Change to the all view, so that we see all messages instead
                 * of just inbox messages.
                 */
                var result = self.controllerWidget.chooseMailView('all');
                result.addCallback(function(ignored) {
                        /*
                         * Next view only messages from Alice.
                         */
                        return self.controllerWidget.choosePerson(people[0].key);
                    });

                /*
                 * Once that is done, assert that only Alice's messages show
                 * up.
                 */
                result.addCallback(function(ignored) {
                        self._checkInAliceView();
                    });
                return result;
            });
        return result;
    },

    /**
     * Test that L{Quotient.Mailbox.Controller.choosePerson} switches into the
     * "All People" view when passed "all" as the person key
     */
    function test_personViewAll(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.chooseMailView("trash");
            });
        result.addCallback(
            function(ignored) {
                self.assertEqual(
                    self.controllerWidget.scrollWidget.model.totalRowCount(), 3);

                var people = self.controllerWidget.getPeople();
                self.assertEqual(people[1].name, "Bob");

                return self.controllerWidget.choosePerson(people[1].key);
            });
        result.addCallback(
            function(ignored) {
                self.assertEqual(
                    self.controllerWidget.scrollWidget.model.totalRowCount(), 2);
                    return self.controllerWidget.choosePerson("all");
                });
        result.addCallback(
            function(ignored) {
                self.assertEqual(
                    self.controllerWidget.scrollWidget.model.totalRowCount(), 3);
            });
        return result;
    },

    /**
     * Test switching to a view of messages from a particular person (Alice),
     * using the DOM-based view changing method
     */
    function test_personViewByNode(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.chooseMailView('all');
            });
        result.addCallback(
            function(ignored) {
                var personChooser = self.controllerWidget.firstNodeByAttribute(
                                        "class", "person-chooser");
                var aliceNode = Nevow.Athena.FirstNodeByAttribute(
                                    personChooser, "class", "list-option");

                return self.controllerWidget.choosePersonByNode(aliceNode).addCallback(
                    function(ignored) {
                        return aliceNode;
                    });
            });
        result.addCallback(
            function(aliceNode) {
                self.assertEqual(aliceNode.className, "selected-list-option");
                self._checkInAliceView();
            });
        return result;
    },

    /**
     * Test switching to a view of messages with a particular tag.
     */
    function test_tagView(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                /*
                 * Change to the view of messages with the foo tag.
                 */
                return self.controllerWidget.chooseTag('foo');
            });
        /*
         * Once the view is updated, test that only the message tagged "foo" is
         * visible.
         */
        result.addCallback(
            function(ignored) {
                var rows = self.collectRows();

                self.assertEquals(
                    rows.length, 1, "Should have been 1 row in the 'foo' tag view.");

                self.assertEquals(rows[0]["subject"], "1st message");
            });
        return result;
    },

    /**
     * Test that sending a view request starts the throbber throbbing and that
     * when the request has been completed the throbber stops throbbing.
     */
    function test_throbberStates(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                /*
                 * Hook the throbber.
                 */
                self.throbber = Quotient.Test.TestThrobber();
                self.controllerWidget.scrollWidget.throbber = self.throbber;

                var result = self.controllerWidget.chooseMailView('all');

                /*
                 * Throbber should have been started by the view change.
                 */
                self.failUnless(
                    self.throbber.throbbing,
                    "Throbber should have been throbbing after view request.");

                return result;
            });
        result.addCallback(
            function(ignored) {
                /*
                 * View has been changed, the throbber should have been stopped.
                 */
                self.failIf(
                    self.throbber.throbbing,
                    "Throbber should have been stopped after view change.");
            });
        return result;
    },

    /**
     * Test that the first row of the initial view is selected after the widget
     * loads.
     */
    function test_initialSelection(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                self.assertEqual(
                    self.controllerWidget.scrollWidget.getActiveRow().__id__,
                    self.controllerWidget.scrollWidget.model.getRowData(0).__id__,
                    "Expected first row to be selected.");
            });
        return result;
    },

    /**
     * Test that the first row after a view change completes is selected.
     */
    function test_viewChangeSelection(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.chooseMailView('all');
            });
        result.addCallback(
            function(ignored) {
                self.assertEqual(
                    self.controllerWidget.scrollWidget.getActiveRow().__id__,
                    self.controllerWidget.scrollWidget.model.getRowData(0).__id__,
                    "Expected first row to be selected after view change.");
            });
        return result;
    },

    /**
     * Test that the currently selected message can be archived.
     */
    function test_archiveCurrentMessage(self) {
        var model;
        var rowIdentifiers;
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                model = self.controllerWidget.scrollWidget.model;

                rowIdentifiers = [
                    model.getRowData(0).__id__,
                    model.getRowData(1).__id__];

                return self.controllerWidget.messageAction_archive();
            });
        result.addCallback(
            function(ignored) {
                return self.callRemote(
                    "archivedFlagsByWebIDs",
                    rowIdentifiers[0],
                    rowIdentifiers[1]);
            });
        result.addCallback(
            function(flags) {
                self.assertArraysEqual(
                    flags,
                    [true, false]);

                self.assertEqual(
                    model.getRowData(0).__id__, rowIdentifiers[1]);
            });
        return result;
    },


    /**
     * Test that the checkbox for a row changes to the checked state when that
     * row is added to the group selection.
     */
    function test_groupSelectRowCheckbox(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                var scroller = self.controllerWidget.scrollWidget;
                var row = scroller.model.getRowData(0);
                var webID = row.__id__;
                scroller.groupSelectRow(webID);
                /*
                 * The checkbox should be checked now.
                 */
                var checkboxImage = scroller._getCheckbox(row.__node__);
                self.assertNotEqual(
                    checkboxImage.src.indexOf("checkbox-on.gif"), -1,
                    "Checkbox image was not the on image.");
            });
        return result;
    },

    /**
     * Test that the checkbox for a row changes to the unchecked state when
     * that row is removed from the group selection.
     */
    function test_groupUnselectRowCheckbox(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                var scroller = self.controllerWidget.scrollWidget;
                var row = scroller.model.getRowData(0);
                var webID = row.__id__;
                /*
                 * Select it first, so the next call will unselect it.
                 */
                scroller.model.selectRow(webID);

                scroller.groupSelectRow(webID);
                /*
                 * The checkbox should be checked now.
                 */

                var checkboxImage = scroller._getCheckbox(row.__node__);
                self.assertNotEqual(
                    checkboxImage.src.indexOf("checkbox-off.gif"), -1,
                    "Checkbox image was not the on image.");
            });
        return result;
    },

    /**
     * Test changing the batch selection to all messages.
     */
    function test_changeBatchSelectionAll(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                self.controllerWidget.changeBatchSelection("all");

                var rows = [];
                var model = self.controllerWidget.scrollWidget.model;
                function accumulate(row) {
                    rows.push(row);
                }
                model.visitSelectedRows(accumulate);

                self.assertEqual(rows.length, 2);
                self.assertEqual(rows[0].__id__, model.getRowData(0).__id__);
                self.assertEqual(rows[1].__id__, model.getRowData(1).__id__);
            });
        return result;
    },

    /**
     * Test changing the batch selection to read messages.
     */
    function test_changeBatchSelectionRead(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                self.controllerWidget.changeBatchSelection("read");

                var rows = [];
                var model = self.controllerWidget.scrollWidget.model;
                function accumulate(row) {
                    rows.push(row);
                }
                model.visitSelectedRows(accumulate);

                self.assertEqual(rows.length, 1);
                self.assertEqual(rows[0].__id__, model.getRowData(0).__id__);
            });
        return result;
    },

    /**
     * Test changing the batch selection to unread messages.
     */
    function test_changeBatchSelectionUnread(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                self.controllerWidget.changeBatchSelection("unread");

                var rows = [];
                var model = self.controllerWidget.scrollWidget.model;
                function accumulate(row) {
                    rows.push(row);
                }
                model.visitSelectedRows(accumulate);

                self.assertEqual(rows.length, 1);
                self.assertEqual(rows[0].__id__, model.getRowData(1).__id__);
            });
        return result;
    },

    function _actionTest(self, viewName, individualActionNames, batchActionNames) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.chooseMailView(viewName);
            });
        result.addCallback(
            function(ignored) {
                /*
                 * Make sure that each individual action's button is displayed,
                 * and any action not explicitly mentioned is hidden.
                 */
                var actionsController = self.controllerWidget.messageActions,
                    enabledActions = actionsController.model.getEnabledActions(),
                    allActionNames = actionsController.model.actions,
                    excludedActionNames = Quotient.Common.Util.difference(
                        allActionNames, individualActionNames);

                for (var i = 0; i < individualActionNames.length; ++i) {
                    self.failUnless(
                        actionsController.view.isButtonVisible(
                            individualActionNames[i]));
                }

                /*
                 * All the other actions should be hidden.
                 */
                for (var i = 0; i < excludedActionNames.length; ++i) {
                    self.failIf(
                        actionsController.view.isButtonVisible(
                            excludedActionNames[i]));
                }
            });
        return result;
    },

    /**
     * Test that the correct actions (and batch actions) are available in the inbox view.
     */
    function test_actionsForInbox(self) {
        return self._actionTest(
            "inbox",
            ["archive", "defer", "delete", "forward", "reply", "trainSpam"],
            ["archive", "delete", "trainSpam"]);
    },

    /**
     * Like L{test_actionsForInbox}, but for the archive view.
     */
    function test_actionsForArchive(self) {
        return self._actionTest(
            'archive',
            ['unarchive', 'delete', 'forward', 'reply', 'trainSpam'],
            ['unarchive', 'delete', 'trainSpam']);
    },

    /**
     * Like L{test_actionsForInbox}, but for the all view.
     */
    function test_actionsForAll(self) {
        return self._actionTest(
            "all",
            ["unarchive", "defer", "delete", "forward", "reply", "trainSpam"],
            ["unarchive", "delete", "trainSpam"]);
    },

    /**
     * Like L{test_actionsForInbox}, but for the trash view.
     */
    function test_actionsForTrash(self) {
        return self._actionTest(
            "trash",
            ["undelete", "forward", "reply"],
            ["undelete"]);
    },

    /**
     * Like L{test_actionsForInbox}, but for the spam view.
     */
    function test_actionsForSpam(self) {
        return self._actionTest(
            "spam",
            ["delete", "trainHam"],
            ["delete", "trainHam"]);
    },

    /**
     * Like L{test_actionsForInbox}, but for the deferred view.
     */
    function test_actionsForDeferred(self) {
        return self._actionTest(
            "deferred",
            ["forward", "reply"],
            []);
    },

    /**
     * Like L{test_actionsForInbox}, but for the outbox view.
     */
    function test_actionsForOutbox(self) {
        return self._actionTest('outbox', [], []);
    },

    /**
     * Like L{test_actionsForInbox}, but for the bounce view.
     */
    function test_actionsForBounce(self) {
        return self._actionTest('bounce', ['delete', 'forward'],
                                ['delete']);
    },

    /**
     * Like L{test_actionsForInbox}, but for the sent view.
     */
    function test_actionsForSent(self) {
        return self._actionTest(
            "sent",
            ["delete", "forward", "reply"],
            ["delete"]);
    },

    /**
     * Test deleting the currently selected message batch.
     */
    function test_deleteBatch(self) {
        var rowIdentifiers;
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                var model = self.controllerWidget.scrollWidget.model;

                rowIdentifiers = [
                    model.getRowData(0).__id__,
                    model.getRowData(1).__id__];

                self.controllerWidget.changeBatchSelection("unread");
                return self.controllerWidget.messageAction_delete();
            });
        result.addCallback(
            function(ignored) {
                return self.callRemote(
                    'deletedFlagsByWebIDs',
                    rowIdentifiers[0],
                    rowIdentifiers[1]);
            });
        result.addCallback(
            function(deletedFlags) {
                self.assertArraysEqual(
                    deletedFlags,
                    [false, true]);
            });
        return result;
    },

    /**
     * Test the batch deletion of all messages in the current view.
     */
    function test_deleteAllBatch(self) {
        var model;
        var scroller;
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                scroller = self.controllerWidget.scrollWidget;
                model = scroller.model;

                rowIdentifiers = [
                    model.getRowData(0).__id__,
                    model.getRowData(1).__id__];

                self.controllerWidget.changeBatchSelection("all");
                return self.controllerWidget.messageAction_delete();
            });
        result.addCallback(
            function(ignored) {
                /*
                 * Model and view should be completely empty at this point.
                 */
                self.assertEqual(model.rowCount(), 0);
                self.assertEqual(scroller._scrollViewport.childNodes.length, 1);
                self.assertEqual(scroller._scrollViewport.childNodes[0].style.height, "0px");

                return self.callRemote(
                    'deletedFlagsByWebIDs',
                    rowIdentifiers[0],
                    rowIdentifiers[1]);
            });
        result.addCallback(
            function(deletedFlags) {
                self.assertArraysEqual(
                    deletedFlags,
                    [true, true]);
            });
        return result;
    },

    /**
     * Test archiving the currently selected message batch.
     */
    function test_archiveBatch(self) {
        var rowIdentifiers;
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                var model = self.controllerWidget.scrollWidget.model;

                rowIdentifiers = [
                    model.getRowData(0).__id__,
                    model.getRowData(1).__id__];

                self.controllerWidget.changeBatchSelection("unread");
                return self.controllerWidget.messageAction_archive();
            });
        result.addCallback(
            function(ignored) {
                return self.callRemote(
                    'archivedFlagsByWebIDs',
                    rowIdentifiers[0],
                    rowIdentifiers[1]);
            });
        result.addCallback(
            function(deletedFlags) {
                self.assertArraysEqual(
                    deletedFlags,
                    [false, true]);
            });
        return result;
    },

    /**
     * Test archiving a batch which includes the currently selected message.
     * This should change the message selection to the next message in the
     * mailbox.
     */
    function test_archiveBatchIncludingSelection(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                self.controllerWidget.changeBatchSelection("read");
                return self.controllerWidget.messageAction_archive(null);
            });
        result.addCallback(
            function(ignored) {
                var model = self.controllerWidget.scrollWidget.model;
                self.assertEqual(
                    model.getRowData(0).__id__,
                    self.controllerWidget.scrollWidget.getActiveRow().__id__);
            });
        return result;
    },

    /**
     * Test selecting every message in the view and then archiving them.
     */
    function test_archiveAllBySelection(self) {
        var rowNodes;
        var scroller;
        var model;
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                scroller = self.controllerWidget.scrollWidget;
                model = scroller.model;

                var rowIdentifiers = [
                    model.getRowData(0).__id__,
                    model.getRowData(1).__id__];

                rowNodes = [
                    model.getRowData(0).__node__,
                    model.getRowData(1).__node__];

                scroller.groupSelectRow(rowIdentifiers[0]);
                scroller.groupSelectRow(rowIdentifiers[1]);

                return self.controllerWidget.messageAction_archive();
            });
        result.addCallback(
            function(ignored) {
                /*
                 * Everything has been archived, make sure there are no rows
                 * left.
                 */
                self.assertEqual(model.rowCount(), 0);

                /*
                 * And none of those rows that don't exist in the model should
                 * be displayed, either.
                 */
                self.assertEqual(rowNodes[0].parentNode, null);
                self.assertEqual(rowNodes[1].parentNode, null);
            });
        return result;
    },

    /**
     * Test archiving the selected group of messages.
     */
    function test_archiveGroupSelection(self) {
        var rowIdentifiers;
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                var model = self.controllerWidget.scrollWidget.model;

                rowIdentifiers = [
                    model.getRowData(0).__id__,
                    model.getRowData(1).__id__];

                self.controllerWidget.scrollWidget.groupSelectRow(rowIdentifiers[1]);
                return self.controllerWidget.messageAction_archive();
            });
        result.addCallback(
            function(ignored) {
                return self.callRemote(
                    'archivedFlagsByWebIDs',
                    rowIdentifiers[0],
                    rowIdentifiers[1]);
            });
        result.addCallback(
            function(deletedFlags) {
                self.assertArraysEqual(
                    deletedFlags,
                    [false, true]);
            });
        return result;
    },

    /**
     * Check the interaction between archiving a number of checked messages
     * (a 'batch') and then archiving a single message (the 'selected'
     * message).
     *
     * In particular, we do the equivalent of selecting the "foo" tag, hitting
     * "select all", hitting "archive", selecting the "all" special tag, and
     * then hitting "archive". We then check that there are no messages left
     * in the inbox display. This means that the selected message was archived.
     *
     * Derived from ticket #1780
     */
    function test_archiveBatchThenArchiveSelected(self) {
        var d = self.setUp();
        var model;
        // select the 'foo' tag.
        d.addCallback(
            function(ignored) {
                model = self.controllerWidget.scrollWidget.model;
                return self.controllerWidget.chooseTag('foo');
            });
        // select all messages in the 'foo' tag (there should be just one).
        d.addCallback(
            function(ignored) {
                self.assertEqual(model.totalRowCount(), 1);
                self.controllerWidget.changeBatchSelection("all");
                return self.controllerWidget.messageAction_archive();
            });
        // display all messages regardless of tag.
        d.addCallback(
            function(ignored) {
                return self.controllerWidget.chooseTag('all');
            });
        // there should be one message displayed. archive it.
        d.addCallback(
            function(ignored) {
                self.assertEqual(model.totalRowCount(), 1);
                return self.controllerWidget.messageAction_archive();
            });
        // there should be no more messages in this view.
        d.addCallback(
            function(ignored) {
                // totalRowCount is *cached*, so we need to fetch the *real*
                // value from the *widget*. guh. -- jml
                var d = self.controllerWidget.scrollWidget.getSize();
                d.addCallback(function(size) { self.assertEqual(size, 0); });
                return d
            });
        return d;
    },


    /**
     * Test archiving the selected group of messages, including the currently
     * selected message.
     */
    function test_archiveGroupSelectionIncludingSelection(self) {
        var model;
        var rowIdentifiers;
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                model = self.controllerWidget.scrollWidget.model;

                rowIdentifiers = [
                    model.getRowData(0).__id__,
                    model.getRowData(1).__id__];

                self.controllerWidget.scrollWidget.groupSelectRow(rowIdentifiers[0]);
                return self.controllerWidget.messageAction_archive();
            });
        result.addCallback(
            function(ignored) {
                self.assertEqual(
                    model.getRowData(0).__id__,
                    self.controllerWidget.scrollWidget.getActiveRow().__id__);
                self.assertEqual(
                    model.getRowData(0).__id__,
                    rowIdentifiers[1]);
            });
        return result;
    },

    /**
     * Test the spam filter can be trained on a particular message.
     */
    function test_trainSpam(self) {
        var model;
        var rowIdentifiers;

        var result = self.setUp();
        result.addCallback(
            function(ignored) {

                model = self.controllerWidget.scrollWidget.model;
                // Let's sanity check before we assert in the next method...
                self.assertEqual(model.rowCount(), 2);

                rowIdentifiers = [
                    model.getRowData(0).__id__,
                    model.getRowData(1).__id__
                    ];

                return self.controllerWidget.messageAction_trainSpam();
            });
        result.addCallback(
            function(ignored) {
                /*
                 * Should have removed message from the current view, since it
                 * is not the spam view.
                 */
                self.assertEqual(model.rowCount(), 1);
                self.assertEqual(model.getRowData(0).__id__, rowIdentifiers[1]);

                /*
                 * Make sure the server thinks the message was trained as spam.
                 */
                return self.callRemote(
                    "trainedStateByWebIDs",
                    rowIdentifiers[0], rowIdentifiers[1]);
            });
        result.addCallback(
            function(trainedStates) {
                /*
                 * This one was trained as spam.
                 */
                self.assertEqual(trainedStates[0].trained, true);
                self.assertEqual(trainedStates[0].spam, true);

                /*
                 * This one was not.
                 */
                self.assertEqual(trainedStates[1].trained, false);
            });
        return result;
    },


    /**
     * Like L{test_trainSpam}, only for training a message as ham rather than
     * spam.
     */
    function test_trainHam(self) {
        var model;
        var rowIdentifiers;

        var result = self.setUp();
        result.addCallback(
            function(ignored) {

                /*
                 * Change to the spam view so training as ham will remove the
                 * message from the view.
                 */

                return self.controllerWidget.chooseMailView("spam");
            });
        result.addCallback(
            function(ignored) {
                model = self.controllerWidget.scrollWidget.model;

                rowIdentifiers = [model.getRowData(0).__id__];

                return self.controllerWidget.messageAction_trainHam();
            });
        result.addCallback(
            function(ignored) {
                /*
                 * Should have removed message from the current view.
                 */
                self.assertEqual(model.rowCount(), 0);

                /*
                 * Make sure the server thinks the message was trained as spam.
                 */
                return self.callRemote(
                    "trainedStateByWebIDs", rowIdentifiers[0]);
            });
        result.addCallback(
            function(trainedStates) {
                /*
                 * It was trained as ham.
                 */
                self.assertEqual(trainedStates[0].trained, true);
                self.assertEqual(trainedStates[0].spam, false);
            });
        return result;
    },

    /**
     * Test the message deferral functionality.
     */
    function test_defer(self) {
        var model;
        var rowIdentifiers;

        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                model = self.controllerWidget.scrollWidget.model;

                rowIdentifiers = [
                    model.getRowData(0).__id__,
                    model.getRowData(1).__id__];

                return self.controllerWidget.messageAction_defer({
                    days: 0, hours: 1, minutes: 0});
            });
        result.addCallback(
            function(ignored) {
                self.assertEqual(model.rowCount(), 1);

                self.assertEqual(model.getRowData(0).__id__, rowIdentifiers[1]);

                return self.callRemote(
                    "deferredStateByWebIDs",
                    rowIdentifiers[0], rowIdentifiers[1]);
            });
        result.addCallback(
            function(deferredStates) {
                /*
                 * First message should have an undeferral time that is at
                 * least 30 minutes after the current time, since the minimum
                 * deferral time is 1 hour. (XXX This is garbage - we need to
                 * be able to test exact values here).
                 */
                self.assertNotEqual(deferredStates[0], null);
                self.failUnless(
                    deferredStates[0] - (30 * 60) > new Date().getTime() / 1000);
                /*
                 * Second message wasn't deferred
                 */
                self.assertEqual(deferredStates[1], null);
            });
        return result;
    },


    /**
     * Test that a boomerang appears on a message that is deferred from the
     * 'all' view.
     */
    function test_deferDisplay(self) {
        var model, widget;
        var d = self.setUp();
        d.addCallback(
            function(ignored) {
                widget = self.controllerWidget.scrollWidget;
                model = widget.model;
                return self.controllerWidget.chooseMailView('all');
            });
        d.addCallback(
            function(ignored) {
                return self.controllerWidget.messageAction_defer({
                    days: 0, hours: 1, minutes: 0});
            });
        d.addCallback(
            function(ignored) {
                var node = widget.findCellElement(model.getRowData(0));
                self.assertEqual(node.childNodes[2].getAttribute('src'),
                                 self.staticURL('/images/boomerang.gif'));
            });
        return d;
    },

    /**
     * Test that a boomerang never appears on any messages in the inbox view
     * when a message is deferred
     */
    function test_noInboxBoomerang(self) {
        var d = self.setUp();
        d.addCallback(
            function(ignored) {
                return self.controllerWidget.messageAction_defer({
                    days: 0, hours: 1, minutes: 0});
            });
        d.addCallback(
            function(ignored) {
                function boomerangCount(node) {
                    return Nevow.Athena.NodesByAttribute(
                        node, 'src', self.staticURL('/images/boomerang.gif')
                        ).length;
                }
                self.assertEqual(
                    Nevow.Athena.NodesByAttribute(
                        self.controllerWidget.scrollWidget.node,
                        'src',
                        self.staticURL('/images/boomerang.gif')).length,
                    0);
            });
        return d;

    },

    /**
     * Same as test_deferDisplay, except for a whole group.
     */
    function test_deferDisplayGroup(self) {
        var model, widget;
        var d = self.setUp();
        d.addCallback(
            function(ignored) {
                widget = self.controllerWidget.scrollWidget;
                model = widget.model;
                return self.controllerWidget.chooseMailView('all');
            });
        d.addCallback(
            function(ignored) {
                var ids = [model.getRowData(0).__id__,
                           model.getRowData(1).__id__];
                self.controllerWidget.scrollWidget.groupSelectRow(ids[0]);
                self.controllerWidget.scrollWidget.groupSelectRow(ids[1]);
                return self.controllerWidget.messageAction_defer({
                    days: 0, hours: 1, minutes: 0});
            });
        d.addCallback(
            function(ignored) {
                function boomerangCount(node) {
                    return Nevow.Athena.NodesByAttribute(
                        node, 'src', self.staticURL('/images/boomerang.gif')
                        ).length;
                }
                var node = widget.findCellElement(model.getRowData(0));
                self.assertEqual(boomerangCount(node), 1);
                node = widget.findCellElement(model.getRowData(1));
                self.assertEqual(boomerangCount(node), 1);
                node = widget.findCellElement(model.getRowData(2));
                self.assertEqual(boomerangCount(node), 0);
            });
        return d;
    },


    /**
     * Same as test_deferDisplay, except for a batch selection.
     */
    function test_deferDisplayBatch(self) {
        var model, widget;
        var d = self.setUp();
        d.addCallback(
            function(ignored) {
                widget = self.controllerWidget.scrollWidget;
                model = widget.model;
                return self.controllerWidget.chooseMailView('all');
            });
        d.addCallback(
            function(ignored) {
                self.controllerWidget.changeBatchSelection('all');
                return self.controllerWidget.messageAction_defer({
                    days: 0, hours: 1, minutes: 0});
            });
        d.addCallback(
            function(ignored) {
                var node, index, indices = model.getRowIndices();
                for (var i=0; i<indices.length; ++i) {
                    index = indices[i];
                    node = widget.findCellElement(model.getRowData(index));
                    self.assertEqual(node.childNodes[2].getAttribute('src'),
                                     self.staticURL('/images/boomerang.gif'));
                }
            });
        return d;
    },

    /**
     * Test that selecting the reply-to action for a message brings up a
     * compose widget.
     */
    function test_replyTo(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.messageAction_reply(false);
            });
        result.addCallback(self._makeComposeTester());
        return result;
    },

    /**
     * Test that selecting the forward action for a message brings up a
     * compose widget.
     */
    function test_forward(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.messageAction_forward(false);
            });
        result.addCallback(self._makeComposeTester());
        return result;
    },

    /**
     * Test that selecting the "reply all" action for a message brings up a
     * compose widget.
     */
    function test_replyToAll(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.messageAction_replyAll(false);
            });
        result.addCallback(self._makeComposeTester());
        return result;
    },

    /**
     * Test that selecting the redirect action for a message brings up a
     * compose widget
     */
    function test_redirect(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.messageAction_redirect(false);
            });
        result.addCallback(
            function(ignored) {
                var msgDetailNodes = self.controllerWidget.nodesByAttribute(
                    "class", "message-detail-fragment"),
                    /* redirect contains a msg detail, inserted before the
                     * original msg detail */
                    msgDetail = Quotient.Message.MessageDetail.get(
                        msgDetailNodes[1]),
                    children = msgDetail.childWidgets,
                    lastChild = children[children.length - 1];
                self.failUnless(lastChild instanceof Quotient.Compose.RedirectingController);

                var parentNode = lastChild.node;
                while(parentNode != null && parentNode != self.node) {
                    parentNode = parentNode.parentNode;
                }
                self.assertEqual(parentNode, self.node);
            });
        return result;
    },
    /**
     * Test that the send button on the compose widget returns the view to its
     * previous state.
     */
    function test_send(self) {
        var composer;
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.messageAction_reply(false);
            });
        result.addCallback(
            function(ignored) {

                var children = self._getMessageDetail().childWidgets;
                composer = children[children.length - 1];
                /*
                 * Sanity check.
                 */
                self.failUnless(composer instanceof Quotient.Compose.Controller);

                composer.stopSavingDrafts();

                return composer.submit();
            });
        result.addCallback(
            function(ignored) {
                /*
                 * Composer should no longer be displayed.
                 */
                self.assertEqual(composer.node.parentNode, null);

                return composer.callRemote('getInvokeArguments');
            });
        result.addCallback(
            function(invokeArguments) {
                /*
                 * Should have been called once.
                 */
                self.assertEqual(invokeArguments.length, 1);

                self.assertArraysEqual(invokeArguments[0].toAddresses, ['alice@example.com']);
                self.assertArraysEqual(invokeArguments[0].cc, ['bob@example.com']);
                self.assertArraysEqual(invokeArguments[0].bcc, ['jane@example.com']);
                self.assertArraysEqual(invokeArguments[0].subject, ['Test Message']);
                self.assertArraysEqual(invokeArguments[0].draft, [false]);
                self.assertArraysEqual(invokeArguments[0].messageBody, ['message body text']);
            });
        return result;
    },

    /**
     * Helper for draft saving tests.
     *
     * @param expectedCallCount: The number of DelayedCalls which are expected
     * to be pending after the compose widget is obscured by the supplied
     * function.
     *
     * @param occult: A function which should get rid of the compose widget
     * somehow.
     */
    function _stopSavingDraftsTest(self, expectedCallCount, occult) {
        var DelayedCall = Divmod.Runtime.DelayedCall;
        var calls = [];
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                /*
                 * Steal the delayed call system.
                 */
                Divmod.Runtime.DelayedCall = function(delay, callable) {
                    calls.push({
                          delay: delay,
                          callable: callable});
                    function cancel() {
                        for (var i = 0; i < calls.length; ++i) {
                            if (calls[i].delay === delay &&
                                calls[i].callable === callable) {
                                calls.splice(i, 1);
                                return;
                            }
                        }
                        throw new Error("Cancelled already-cancelled event.");
                    };
                    return {cancel: cancel};
                };
                return self.controllerWidget.messageAction_reply(false);
            });
        result.addCallback(occult);
        result.addCallback(
            function(ignored) {
                /*
                 * There should be only one delayed call now.
                 */
                self.assertEqual(calls.length, expectedCallCount);
            });
        result.addBoth(
            function(passthrough) {
                /*
                 * Put the real DelayedCall back.
                 */
                Divmod.Runtime.DelayedCall = DelayedCall;
                return passthrough;
            });
        return result;
    },

    /**
     * Verify that if a second compose widget is dumped on top of a first, the
     * first stops scheduling drafts to be saved.
     */
    function test_doubleCompose(self) {
        return self._stopSavingDraftsTest(
            1,
            function(ignored) {
                /*
                 * Dump another compose widget on top of the existing one.
                 */
                return self.controllerWidget.messageAction_reply(false);
            });
    },

    /**
     * Verify that if a message detail is requested while a compose widget is
     * up, the compose widget stops scheduling draft saving calls.
     */
    function test_messageDetailOverCompose(self) {
        return self._stopSavingDraftsTest(
            0,
            function(ignored) {
                /*
                 * Request that the detail for a message be displayed.
                 */
                var scrollWidget = self.controllerWidget.scrollWidget;
                var scrollModel = scrollWidget.model;
                var row = scrollModel.getRowData(0);
                var webID = row.__id__;
                return self.controllerWidget.fastForward(webID);
            });
    },


    /**
     * Test that a message in the trash can be undeleted.
     */
    function test_undelete(self) {
        var model;
        var rowIdentifier;

        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                model = self.controllerWidget.scrollWidget.model;
                return self.controllerWidget.chooseMailView("trash");
            });
        result.addCallback(
            function(ignored) {
                rowIdentifier = model.getRowData(0).__id__;
                return self.controllerWidget.messageAction_undelete();
            });
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.chooseMailView("all");
            });
        result.addCallback(
            function(ignored) {
                /*
                 * Undeleted message should be here _somewhere_.
                 */
                var row = model.findRowData(rowIdentifier);
            });
        return result;
    },

    /**
     * Test that a message in the archive can be unarchived.
     */
    function test_unarchive(self) {
        var model;
        var rowIdentifier;

        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                model = self.controllerWidget.scrollWidget.model;
                return self.controllerWidget.chooseMailView("all");
            });
        result.addCallback(
            function(ignored) {
                rowIdentifier = model.getRowData(0).__id__;
                return self.controllerWidget.messageAction_unarchive();
            });
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.chooseMailView("inbox");
            });
        result.addCallback(
            function(ignored) {
                /*
                 * Undeleted message should be here _somewhere_.
                 */
                var row = model.findRowData(rowIdentifier);
            });
        return result;
    },


    /**
     * Test that a message disappears when it is unarchived from the archive
     * view.
     */
    function test_unarchiveRemovesFromArchive(self) {
        var d = self.setUp();
        var model, rowIdentifier;
        d.addCallback(
            function(ignored) {
                model = self.controllerWidget.scrollWidget.model;
                return self.controllerWidget.chooseMailView('archive');
            });
        d.addCallback(
            function(ignored) {
                rowIdentifier = model.getRowData(0).__id__;
                return self.controllerWidget.messageAction_unarchive();
            });
        d.addCallback(
            function(ignored) {
                self.assertThrows(Mantissa.ScrollTable.NoSuchWebID,
                                  function () {
                                      model.findIndex(rowIdentifier);
                                  });
            });
        return d;
    },


    /**
     * Test that a message in "All" view remains in "All" when it is
     * unarchived.
     */
    function test_unarchiveKeepsInAll(self) {
        var d = self.setUp();
        var model, rowIdentifier;
        d.addCallback(
            function(ignored) {
                model = self.controllerWidget.scrollWidget.model;
                return self.controllerWidget.chooseMailView('all');
            });
        d.addCallback(
            function(ignored) {
                rowIdentifier = model.getRowData(0).__id__;
                return self.controllerWidget.messageAction_unarchive();
            });
        d.addCallback(
            function(ignored) {
                self.assertEqual(rowIdentifier, model.getRowData(0).__id__);
            });
        return d;
    },


    /**
     * Test that archiving a message from the Archive view does not change
     * the display.
     */
    function test_archiveFromArchiveIdempotent(self) {
        var d = self.setUp();
        var model, rowIdentifier;
        d.addCallback(
            function(ignored) {
                model = self.controllerWidget.scrollWidget.model;
                return self.controllerWidget.chooseMailView('archive');
            });
        d.addCallback(
            function(ignored) {
                rowIdentifier = model.getRowData(0).__id__;
                return self.controllerWidget.messageAction_archive();
            });
        d.addCallback(
            function(ignored) {
                // check that the "archived" row is unchanged.
                self.assertEqual(rowIdentifier,
                                 model.getRowData(0).__id__);
            });
        return d;
    },


    /**
     * Test that the (undisplayed) Message.sender column is passed to the
     * scrolltable model
     */
    function test_senderColumn(self) {
        var model = self.controllerWidget.scrollWidget.model;
        self.failUnless(model.getRowData(0).sender);
    },

    /**
     * Test that the private helper method _findPreviewRow returns the correct
     * row data.
     */
    function test_findPreviewRow(self) {
        var controller;
        var model;
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                controller = self.controllerWidget;
                model = controller.scrollWidget.model;
                self.assertEqual(
                    controller._findPreviewRow(model.getRowData(0).__id__).__id__,
                    model.getRowData(1).__id__);
                self.assertEqual(
                    controller._findPreviewRow(model.getRowData(1).__id__).__id__,
                    model.getRowData(0).__id__);

                /*
                 * Switch to a view with only one message to test that case.
                 */
                return controller.chooseMailView('spam');
            });
        result.addCallback(
            function(ignored) {
                self.assertEqual(
                    controller._findPreviewRow(model.getRowData(0).__id__),
                    null);
            });
        return result;
    },


    /**
     * Test that all of the correct information for a preview is extracted from
     * a data row by the private helper method _getPreviewData.
     */
    function test_getPreviewData(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                var rowData = self.controllerWidget.scrollWidget.model.getRowData(0);
                var preview = self.controllerWidget._getPreviewData(rowData);
                self.assertArraysEqual(Divmod.dir(preview), ["subject"]);
                self.assertEqual(preview.subject, "2nd message");
            });
        return result;
    },

    /**
     * Test that values passed to setMessageContent show up in the display.
     */
    function test_setMessageContent(self) {
        var webID;
        var controller;
        var model;
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                controller = self.controllerWidget;
                model = controller.scrollWidget.model;
                webID = model.getRowData(0).__id__;
                return self.callRemote('getMessageDetail', webID);
            });
        result.addCallback(
            function(messageDetailInfo) {
                var subject = model.getRowData(1).subject;
                controller.setMessageContent(webID, messageDetailInfo);
                self.assertNotEqual(controller.node.innerHTML.indexOf(subject), -1);

            });
        return result;
    },

    /**
     * Test that the subject of the message preview passed to setMessageContent
     * is properly escaped if necessary.
     */
    function test_setPreviewQuoting(self) {
        var webID;
        var controller;
        var model;
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                controller = self.controllerWidget;
                model = controller.scrollWidget.model;
                webID = model.getRowData(0).__id__;
                return self.callRemote('getMessageDetail', webID);
            });
        result.addCallback(
            function(messageDetailInfo) {
                var subject = 'test <subject> & string';
                var escaped = 'test &lt;subject&gt; &amp; string';

                /*
                 * Cheat a little bit.  Jam the subject we're testing into the
                 * model so it'll get used to populate the view.
                 */
                model.getRowData(1).subject = subject;

                controller.setMessageContent(webID, messageDetailInfo);
                self.assertNotEqual(controller.node.innerHTML.indexOf(escaped), -1);

            });
        return result;
    },


    /**
     * @return: a function which can be added as a callback to a deferred
     * which fires with an L{Quotient.Compose.Controller} instance.  Checks
     * the the compose instance is inside the message detail of our
     * L{Quotient.Mailbox.Controller}, and has the "inline" attribute set
     */
    function _makeComposeTester(self) {
        return function (composer) {
            var children = self._getMessageDetail().childWidgets;
            var lastChild = children[children.length - 1];
            self.failUnless(lastChild instanceof Quotient.Compose.Controller);

            /*
             * XXX Stop it from saving drafts, as this most likely won't
             * work and potentially corrupts page state in ways which will
             * break subsequent tests.
             */
            lastChild.stopSavingDrafts();

            /*
             * Make sure it's actually part of the page
             */
            var parentNode = lastChild.node;
            while (parentNode != null && parentNode != self.node) {
                parentNode = parentNode.parentNode;
            }
            self.assertEqual(parentNode, self.node);
            self.failUnless(lastChild.inline);
            return lastChild;
        }
    },
    Quotient.Test._getMessageDetail);



/**
 * Test controller behaviors in the presence of a more than a complete visible
 * page of messages.
 */
Quotient.Test.FullControllerTestCase = Nevow.Athena.Test.TestCase.subclass(
    'Quotient.Test.FullControllerTestCase');
Quotient.Test.FullControllerTestCase.methods(
    /* Retrieve a fully controller widget from the server, add it to the
     * document and return its initialization deferred
     *
     * @type: L{Divmod.Defer.Deferred}
     */
    function setUp(self) {
        var result = self.callRemote('getFullControllerWidget');
        result.addCallback(function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                self.controller = widget;
                self.node.appendChild(widget.node);
                return widget.initializationDeferred;
            });
        return result;
    },


    /**
     * Check the interaction between archiving a number of checked messages
     * (a 'batch') and then archiving a single message (the 'selected'
     * message).
     *
     * This test functions much like
     * L{ControllerTestCase.test_archiveBatchThenArchiveSelected}, except it
     * ensures that the messages that are off-screen are *not* archived. This
     * is the negative behaviour outlined in ticket #1780.
     */
    function test_archiveAllTaggedThenArchiveSelected(self) {
        var d = self.setUp();
        d.addCallback(
            function(ignored) {
                return self.controller.chooseTag('foo');
            });
        d.addCallback(
            function(ignored) {
                self.controller.changeBatchSelection('all');
                return self.controller.messageAction_archive();
            });
        d.addCallback(
            function(ignored) {
                return self.controller.chooseTag('all');
            });
        d.addCallback(
            function(ignored) {
                return self.controller.messageAction_archive();
            });
        d.addCallback(
            function(ignored) {
                var d = self.controller.scrollWidget.getSize();
                // 20 messages originally, 2 archived -- 1 tagged 'foo', and 1
                // selected.
                d.addCallback(function(size) { self.assertEqual(size, 18); });
                return d;
            });
        return d;
    },


    /**
     * Test deletion of all messages using batch selection.
     */
    function test_deleteAllBatch(self) {
        var result = self.setUp();

        result.addCallback(
            function(ignored) {
                /*
                 * Sanity check - make sure there are fewer rows in the model
                 * than the server knows about.
                 */
                self.failIf(self.controller.scrollWidget.model.rowCount() >= 20);

                /*
                 * Batch select everything and delete it.
                 */
                self.controller.changeBatchSelection("all");
                return self.controller.messageAction_delete();
            });
        result.addCallback(
            function(ignored) {
                var scroller = self.controller.scrollWidget;
                self.assertEqual(
                    scroller.model.rowCount(),
                    0,
                    "Too many rows in model.");
                self.assertEqual(
                    scroller.placeholderModel.getPlaceholderCount(),
                    1,
                    "Too many placeholders in model.");

                /*
                 * The existence of this placeholder is not strictly necessary.
                 * However, it exists with the current implementation, and I
                 * really want to assert something about placeholders, so I am
                 * going to assert that it covers an empty range.  If the
                 * placeholder implementation changes at some future point,
                 * then perhaps these asserts should be changed as well.
                 */
                var placeholder = scroller.placeholderModel.getPlaceholderWithIndex(0);
                self.assertEqual(placeholder.start, 0);
                self.assertEqual(placeholder.stop, 0);

                /*
                 * Fucked up.  Asserting against a string to determine the
                 * height of something?  Garbage.  Asserting against a style to
                 * make sure that there's nothing visible?  Equally fucked up.
                 */
                self.assertEqual(
                    scroller._scrollViewport.childNodes.length,
                    1,
                    "Too many rows in view.");
                self.assertEqual(
                    scroller._scrollViewport.childNodes[0].style.height,
                    "0px",
                    "View too tall.");
            });
        return result;
    },

    /**
     * Test group actions when the rows have been fetched out of order
     */
    function test_groupActionsOutOfOrderRows(self) {
        var result = self.setUp();

        result.addCallback(
            function(ignored) {
                /* get a row near the end */
                return self.controller.scrollWidget.requestRowRange(18, 19);
            });

        result.addCallback(
            function(ignored) {
                /* get some row before it */
                return self.controller.scrollWidget.requestRowRange(15, 16);
            });

        result.addCallback(
            function(ignored) {
                /* add the last row to the group selection */
                var webID = self.controller.scrollWidget.model.getRowData(18).__id__;
                self.controller.scrollWidget.groupSelectRow(webID);
                /* and archive it */
                result = self.controller.messageAction_archive();
                return result.addCallback(
                    function(ignored) {
                        return webID;
                    });
            });

        result.addCallback(
            function(webID) {
                /* if we got here, we're good, but lets test some junk anyway */
                self.failIf(self.controller.scrollWidget.selectedGroup);
                self.assertThrows(
                    Mantissa.ScrollTable.NoSuchWebID,
                    function() {
                        self.controller.scrollWidget.model.findIndex(webID);
                    });
            });
        return result;
    });


Quotient.Test.EmptyInitialViewControllerTestCase = Nevow.Athena.Test.TestCase.subclass(
    'Quotient.Test.EmptyInitialViewControllerTestCase');
Quotient.Test.EmptyInitialViewControllerTestCase.methods(
    /**
     * Retrieve a Controller Widget for an inbox from the server.
     */
    function setUp(self) {
        var result = self.callRemote('getControllerWidget');
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(function(widget) {
                self.controllerWidget = widget;
                self.node.appendChild(widget.node);
                /**
                 * Wait for the controller widget to be fully initialized.
                 * This includes its ScrollingWidget.
                 */
                return self.controllerWidget.initializationDeferred;
            });
        result.addCallback(function(widget) {
                return self.controllerWidget.chooseMailView('all');
            });
        return result;
    },
    /**
     * Test that the forward action works in this configuration.
     */
    function test_forward(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.messageAction_forward(false);
            });
        result.addCallback(
            function(ignored) {
                var children = self._getMessageDetail().childWidgets;
                var lastChild = children[children.length - 1];
                self.failUnless(lastChild instanceof Quotient.Compose.Controller);

                /*
                 * XXX Stop it from saving drafts, as this most likely won't
                 * work and potentially corrupts page state in ways which will
                 * break subsequent tests.
                 */
                lastChild.stopSavingDrafts();

                /*
                 * Make sure it's actually part of the page
                 */
                var parentNode = lastChild.node;
                while (parentNode != null && parentNode != self.node) {
                    parentNode = parentNode.parentNode;
                }
                self.assertEqual(parentNode, self.node);
            });
        return result;
    },
    Quotient.Test._getMessageDetail);



Quotient.Test.EmptyControllerTestCase = Nevow.Athena.Test.TestCase.subclass('Quotient.Test.EmptyControllerTestCase');
Quotient.Test.EmptyControllerTestCase.methods(
    /**
     * Get an empty Controller widget and add it as a child to this test case's
     * node.
     */
    function setUp(self) {
        var result = self.callRemote('getEmptyControllerWidget');
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(function(widget) {
                self.controllerWidget = widget;
                self.node.appendChild(widget.node);
                return widget.initializationDeferred;
            });
        return result;
    },

    /**
     * Test that loading an empty mailbox doesn't result in any errors, that no
     * message is initially selected, etc.
     */
    function test_emptyLoad(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                self.assertEqual(
                    self.controllerWidget.scrollWidget.getActiveRow(),
                    null,
                    "No rows exist, so none should have been selected.");
            });
        return result;
    },

    /**
     * Test that switching to an empty view doesn't result in any errors, that
     * no message is initially selected, etc.
     */
    function test_emptySwitch(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.chooseMailView('all');
            });
        result.addCallback(
            function(ignored) {
                self.assertEqual(
                    self.controllerWidget.scrollWidget.getActiveRow(),
                    null,
                    "No rows exist, so none should have been selected.");
            });
        return result;
    },

    /**
     * Test that loading an empty mailbox displays 'No more messages' in
     * the next message preview bar. Check the same after switching to
     * an empty view.
     */
    function test_messagePreview(self) {
        var d = self.setUp();
        d.addCallback(
            function(ignored) {
                var node = self.controllerWidget.nextMessagePreview;
                self.assertEqual(MochiKit.DOM.scrapeText(node),
                                 'No more messages.');
            });
        return d;
    },


    /**
     * After the composer is dismissed, if there are no messages in the
     * selected view, the message detail area remains blank.
     */
    function test_emptyMessageViewAfterDismissingComposer(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                return self.controllerWidget.compose(false);
            });
        result.addCallback(
            function(composer) {
                var finished = self.controllerWidget.reloadMessageAfterComposeCompleted(composer);
                composer.cancel();
                return finished;
            });
        result.addCallback(
            function(ignored) {
                self.assertEqual(self.controllerWidget.messageDetail.firstChild, null);
            });
        return result;
    });


/**
 * Tests for UI interactions with the focused state of the workflow.
 */
Quotient.Test.FocusControllerTestCase = Nevow.Athena.Test.TestCase.subclass('Quotient.Test.FocusControllerTestCase');
Quotient.Test.FocusControllerTestCase.methods(
    /**
     * Get an empty Controller widget and add it as a child to this test case's
     * node.
     */
    function setUp(self) {
        var result = self.callRemote('getFocusControllerWidget');
        result.addCallback(
            function cbWidgetInfo(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function cbWidget(widget) {
                self.controllerWidget = widget;
                self.node.appendChild(widget.node);
                return widget.initializationDeferred;
            });
        return result;
    },

    /**
     * Test that in the inbox view, both the focused message and the unfocused
     * message show up.
     */
    function test_focusedShownByInbox(self) {
        var result = self.setUp();
        result.addCallback(
            function cbSetUp(ignored) {
                var model = self.controllerWidget.scrollWidget.model;
                self.assertEqual(model.rowCount(), 2);
                self.assertEqual(
                    model.getRowData(0).subject, 'focused message');
                self.assertEqual(
                    model.getRowData(1).subject, 'unfocused message');
            });
        return result;
    },

    /**
     * Test that only the focused message shows up in the focus view.
     */
    function test_focusedShownByFocus(self) {
        var result = self.setUp();
        result.addCallback(
            function cbSetUp(ignored) {
                return self.controllerWidget.chooseMailView('focus');
            });
        result.addCallback(
            function cbViewChange(ignored) {
                var model = self.controllerWidget.scrollWidget.model;
                self.assertEqual(model.rowCount(), 1);
                self.assertEqual(
                    model.getRowData(0).subject, 'focused message');
            });
        return result;
    },

    /**
     * Test that a focused message can be archived from the inbox view and it
     * will disappear from both the inbox and focus views.
     */
    function test_archiveFocusedFromInbox(self) {
        var result = self.setUp();
        result.addCallback(
            function cbSetUp(ignored) {
                return self.controllerWidget.messageAction_archive();
            });
        result.addCallback(
            function cbArchived(ignored) {
                var model = self.controllerWidget.scrollWidget.model;
                self.assertEqual(model.rowCount(), 1);
                self.assertEqual(
                    model.getRowData(0).subject, 'unfocused message');
            });
        return result;
    },

    /**
     * Like L{test_archiveFocusedFromInbox}, but invoke the archive action from
     * the focus view instead.
     */
    function test_archiveFocusedFromFocus(self) {
        var result = self.setUp();
        result.addCallback(
            function cbSetUp(ignored) {
                return self.controllerWidget.chooseMailView('focus');
            });
        result.addCallback(
            function cbViewChanged(ignored) {
                return self.controllerWidget.messageAction_archive();
            });
        result.addCallback(
            function cbArchived(ignored) {
                var model = self.controllerWidget.scrollWidget.model;
                self.assertEqual(model.rowCount(), 0);
            });
        return result;
    },

    /**
     * Test that archiving and then unarchiving the focused message results in
     * it returning to the focus view.
     */
    function test_unarchiveFocused(self) {
        var model;
        var result = self.setUp();
        result.addCallback(
            function cbSetUp(ignored) {
                model = self.controllerWidget.scrollWidget.model;
                return self.controllerWidget.messageAction_archive();
            });
        result.addCallback(
            function cbArchived(ignored) {
                self.assertEqual(model.rowCount(), 1);
                return self.controllerWidget.chooseMailView('archive');
            });
        result.addCallback(
            function cbArchiveView(ignored) {
                return self.controllerWidget.messageAction_unarchive();
            });
        result.addCallback(
            function cbUnarchived(ignored) {
                self.assertEqual(model.rowCount(), 0);
                return self.controllerWidget.chooseMailView('focus');
            });
        result.addCallback(
            function cbFocusView(ignored) {
                self.assertEqual(model.rowCount(), 1);
                self.assertEqual(
                    model.getRowData(0).subject, 'focused message');
            });
        return result;
    },

    /**
     * Test that a focused message can be moved to the trash from the inbox.
     */
    function test_trashFocusFromInbox(self) {
        var model;
        var result = self.setUp();
        result.addCallback(
            function cbSetUp(ignored) {
                model = self.controllerWidget.scrollWidget.model;
                return self.controllerWidget.messageAction_delete();
            });
        result.addCallback(
            function cbTrashed(ignored) {
                self.assertEqual(model.rowCount(), 1);
                self.assertEqual(
                    model.getRowData(0).subject, 'unfocused message');
                return self.controllerWidget.chooseMailView('trash');
            });
        result.addCallback(
            function cbTrashView(ignored) {
                self.assertEqual(model.rowCount(), 1);
                self.assertEqual(
                    model.getRowData(0).subject, 'focused message');
                return self.controllerWidget.messageAction_undelete();
            });
        result.addCallback(
            function cbUntrashed(ignored) {
                self.assertEqual(model.rowCount(), 0);
                return self.controllerWidget.chooseMailView('focus');
            });
        result.addCallback(
            function cbFocusView(ignored) {
                self.assertEqual(model.rowCount(), 1);
                self.assertEqual(
                    model.getRowData(0).subject, 'focused message');
            });
        return result;
    },

    /**
     * Like L{test_trashFocusFromInbox}, but invoke the trash action from the
     * focus view instead.
     */
    function test_trashFocusFromFocus(self) {
        var model;
        var result = self.setUp();
        result.addCallback(
            function cbSetUp(ignored) {
                model = self.controllerWidget.scrollWidget.model;
                return self.controllerWidget.chooseMailView('focus');
            });
        result.addCallback(
            function cbFocusView(ignored) {
                return self.controllerWidget.messageAction_delete();
            });
        result.addCallback(
            function cbTrashed(ignored) {
                self.assertEqual(model.rowCount(), 0);
                return self.controllerWidget.chooseMailView('trash');
            });
        result.addCallback(
            function cbTrashView(ignored) {
                self.assertEqual(model.rowCount(), 1);
                self.assertEqual(
                    model.getRowData(0).subject, 'focused message');
                return self.controllerWidget.messageAction_undelete();
            });
        result.addCallback(
            function cbUntrashed(ignored) {
                self.assertEqual(model.rowCount(), 0);
                return self.controllerWidget.chooseMailView('focus');
            });
        result.addCallback(
            function cbFocusViewAgain(ignored) {
                self.assertEqual(model.rowCount(), 1);
                self.assertEqual(
                    model.getRowData(0).subject, 'focused message');
            });
        return result;
    },

    /**
     * Test classifying a focused message as spam from the inbox.
     */
    function test_spamFocusFromInbox(self) {
        var model;
        var result = self.setUp();
        result.addCallback(
            function cbSetUp(ignored) {
                model = self.controllerWidget.scrollWidget.model;
                return self.controllerWidget.messageAction_trainSpam();
            });
        result.addCallback(
            function cbTrained(ignored) {
                self.assertEqual(model.rowCount(), 1);
                self.assertEqual(
                    model.getRowData(0).subject, 'unfocused message');
                return self.controllerWidget.chooseMailView('spam');
            });
        result.addCallback(
            function cbSpamView(ignored) {
                self.assertEqual(model.rowCount(), 1);
                self.assertEqual(
                    model.getRowData(0).subject, 'focused message');
                return self.controllerWidget.messageAction_trainHam();
            });
        result.addCallback(
            function cbTrained(ignored) {
                self.assertEqual(model.rowCount(), 0);
                return self.controllerWidget.chooseMailView('focus');
            });
        result.addCallback(
            function cbFocusView(ignored) {
                self.assertEqual(model.rowCount(), 1);
                self.assertEqual(
                    model.getRowData(0).subject, 'focused message');
            });
        return result;
    },

    /**
     * Like L{test_spamFocusFromInbox}, but invoke the spam action from the
     * focus view.
     */
    function test_spamFocusFromFocus(self) {
        var model;
        var result = self.setUp();
        result.addCallback(
            function cbSetUp(ignored) {
                model = self.controllerWidget.scrollWidget.model;
                return self.controllerWidget.chooseMailView('focus');
            });
        result.addCallback(
            function cbFocusView(ignored) {
                return self.controllerWidget.messageAction_trainSpam();
            });
        result.addCallback(
            function cbSpammed(ignored) {
                self.assertEqual(model.rowCount(), 0);
                return self.controllerWidget.chooseMailView('spam');
            });
        result.addCallback(
            function cbSpamView(ignored) {
                self.assertEqual(model.rowCount(), 1);
                self.assertEqual(
                    model.getRowData(0).subject, 'focused message');
                return self.controllerWidget.messageAction_trainHam();
            });
        result.addCallback(
            function cbHammed(ignored) {
                self.assertEqual(model.rowCount(), 0);
                return self.controllerWidget.chooseMailView('focus');
            });
        result.addCallback(
            function cbFocusViewAgain(ignored) {
                self.assertEqual(model.rowCount(), 1);
                self.assertEqual(
                    model.getRowData(0).subject, 'focused message');
            });
        return result;
    });

/**
 * Tests for Quotient.Compose.FromAddressScrollTable
 */
Quotient.Test.FromAddressScrollTableTestCase = Nevow.Athena.Test.TestCase.subclass('Quotient.Test.FromAddressScrollTableTestCase');
Quotient.Test.FromAddressScrollTableTestCase.methods(
    /**
     * Retreive a L{Quotient.Compose.FromAddressScrollTable} from the server
     */
    function setUp(self)  {
        var result = self.callRemote("getFromAddressScrollTable");
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                self.scrollTable = widget;
                self.node.appendChild(widget.node);
                return widget.initializationDeferred;
            });
        return result;
    },

    /**
     * @return: the scrolltable action with name C{name}
     * @rtype: L{Mantissa.ScrollTable.Action}
     */
    function getAction(self, name) {
        for(var i = 0; i < self.scrollTable.actions.length; i++){
            if(self.scrollTable.actions[i].name == name) {
                return self.scrollTable.actions[i];
            }
        }
        throw new Error("no action with name " + name);
    },

    /**
     * Test that the model contains the right stuff for the two FromAddress
     * items in the database
     */
    function test_model(self) {
        return self.setUp().addCallback(
            function() {
                self.assertEqual(self.scrollTable.model.rowCount(), 2);

                var first = self.scrollTable.model.getRowData(0);
                var second = self.scrollTable.model.getRowData(1);

                self.failUnless(first._default);
                self.failIf(second._default);
        });
    },

    /**
     * Test that the custom columnAliases and actions definitions are both
     * respected.
     */
    function test_userInterfaceCustomization(self) {
        return self.setUp().addCallback(
            function(ignored) {
                /*
                 * This is pretty whitebox.
                 */
                self.assertNotEqual(
                    self.scrollTable._headerRow.innerHTML.indexOf('SMTP Host'),
                    -1);

                var i;
                for (i = 0; i < self.scrollTable.columnNames.length; ++i) {
                    if (self.scrollTable.columnNames[i] == "actions") {
                        break;
                    }
                }
                if (i == self.scrollTable.columnNames.length) {
                    self.fail("Did not find actions in columnNames.");
                }
            });
    },

    /**
     * Test that the setDefaultAddress action works
     */
    function test_setDefaultAddress(self) {
        return self.setUp().addCallback(
            function() {
                var second = self.scrollTable.model.getRowData(1);
                var action = self.getAction("setDefaultAddress");
                return action.enact(self.scrollTable, second).addCallback(
                    function() {
                        second = self.scrollTable.model.getRowData(1)
                        var first = self.scrollTable.model.getRowData(0);

                        self.failUnless(second._default);
                        self.failIf(first._default);
                    })
            });
    },

    /**
     * Test that the delete & set default actions are disabled for the system
     * address, which is also the default
     */
    function test_actionsDisabled(self) {
        return self.setUp().addCallback(
            function() {
                var systemAddr = self.scrollTable.model.getRowData(0);
                self.failUnless(systemAddr._default);
                self.assertEqual(systemAddr.__id__, self.scrollTable.systemAddrWebID);

                var actions = self.scrollTable.getActionsForRow(systemAddr);
                self.assertEqual(actions.length, 0);

                var otherAddr = self.scrollTable.model.getRowData(1);
                actions = self.scrollTable.getActionsForRow(otherAddr);
                self.assertEqual(actions.length, 2);
            });
    },

    /**
     * Test the delete action
     */
    function test_deleteAction(self) {
        return self.setUp().addCallback(
            function() {
                var row = self.scrollTable.model.getRowData(1);
                var action = self.getAction("delete");
                return action.enact(self.scrollTable, row).addCallback(
                    function() {
                        self.assertEqual(self.scrollTable.model.rowCount(), 1);
                    });
            });
    });

Quotient.Test.ComposeController = Quotient.Compose.Controller.subclass('ComposeController');
Quotient.Test.ComposeController.methods(
    function saveDraft(self, userInitiated) {
        return Divmod.Defer.succeed(null);
    },

    function startSavingDrafts(self) {
        return;
    },

    function submitSuccess(self, passthrough) {
        return passthrough;
    });

Quotient.Test.ComposeTestCase = Nevow.Athena.Test.TestCase.subclass('ComposeTestCase');
Quotient.Test.ComposeTestCase.methods(
    /**
     * Get a L{Quotient.Test.ComposeController} instance
     */
    function getController(self) {
        return Quotient.Test.ComposeController.get(
                    Nevow.Athena.NodeByAttribute(
                        self.node.parentNode,
                        "athena:class",
                        "Quotient.Test.ComposeController"));
    },

    /**
     * Test the name completion method
     * L{Quotient.Compose.EmailAddressAutoCompleteModel.complete} generates
     * the correct address lists for various inputs
     *
     * @param model: the L{Quotient.Compose.EmailAddressAutoCompleteModel}
     */
    function _doAddressCompletionTest(self, model) {
        /* these are the pairs of [displayName, emailAddress] that we expect
         * the controller to have received from getPeople() */

        var moe     = ["Moe Aboulkheir", "maboulkheir@divmod.com"];
        var tobias  = ["Tobias Knight", "localpart@domain"];
        var madonna = ["Madonna", "madonna@divmod.com"];
        var kilroy  = ["", "kilroy@foo"];

        /**
         * For an emailAddress C{addr} (or part of one), assert that the list
         * of possible completions returned by complete() matches exactly the
         * list of lists C{completions}, where each element is a pair
         * containing [displayName, emailAddress]
         */
        var assertCompletionsAre = function(addr, completions) {
            var _completions = model.complete(addr);
            self.assertArraysEqual(_completions, completions,
                                   function(a, b) {
                                        self.assertArraysEqual(a, b);
                                    });
        }

        /* map email address prefixes to lists of expected completions */
        var completionResults = {
            "m": [moe, madonna],
            "a": [moe],
            "ma": [moe, madonna],
            "maboulkheir@divmod.com": [moe],
            "Moe Aboulkheir": [moe],
            "AB": [moe],
            "k": [tobias, kilroy],
            "KnigHT": [tobias],
            "T": [tobias],
            "l": [tobias],
            "localpart@": [tobias]
        };

        /* check they match up */
        for(var k in completionResults) {
            assertCompletionsAre(k, completionResults[k]);
        }
    },

    /**
     * Test that the 'to' autocompleter of our L{Quotient.Compose.Controller}
     * correctly completes email addresses
     */
    function test_toAddressCompletion(self) {
        var controller = self.getController();
        self._doAddressCompletionTest(
            controller.toAutoCompleteController.model);
    },

    /**
     * Test that the 'cc' autocompleter of our L{Quotient.Compose.Controller}
     * correctly completes email addresses
     */
    function test_ccAddressCompletion(self) {
        var controller = self.getController();
        self._doAddressCompletionTest(
            controller.ccAutoCompleteController.model);
    },

    /**
     * Test that
     * L{Quotient.Compose.EmailAddressAutoCompleteView._reconstituteAddress}
     * correctly turns name & email address pairs into formatted email
     * addresses
     *
     * @param view: L{Quotient.Compose.EmailAddressAutoCompleteView}
     */
    function _doAddressReconstitutionTest(self, view) {
        /* map each [displayName, emailAddress] pair to the result we expect
         * from ComposeController.reconstituteAddress(), when passed the pair */
        var reconstitutedAddresses = [
            [["Moe Aboulkheir", "maboulkheir@divmod.com"],
             '"Moe Aboulkheir" <maboulkheir@divmod.com>'],
            [["Tobias Knight", "localpart@domain"],
             '"Tobias Knight" <localpart@domain>'],
            [["Madonna", "madonna@divmod.com"],
             '"Madonna" <madonna@divmod.com>'],
            [["", "kilroy@foo"], '<kilroy@foo>']
        ];

        /* check they match up */
        for(var i = 0; i < reconstitutedAddresses.length; i++) {
            self.assertEquals(
                view._reconstituteAddress(reconstitutedAddresses[i][0]),
                reconstitutedAddresses[i][1]);
        }
    },

    /**
     * Test that the 'to' autocompleter of our L{Quotient.Compose.Controller}
     * correctly reconstitutes email addresses
     */
    function test_toAddressReconstitution(self) {
        var controller = self.getController();
        self._doAddressReconstitutionTest(
            controller.toAutoCompleteController.view);
    },

    /**
     * Test that the 'cc' autocompleter of our L{Quotient.Compose.Controller}
     * correctly reconstitutes email addresses
     */
    function test_ccAddressReconstitution(self) {
        var controller = self.getController();
        self._doAddressReconstitutionTest(
            controller.ccAutoCompleteController.view);
    },

    /**
     * Test that L{Quotient.Compose.Controller.toggleMoreOptions} toggles the
     * visibility of the "more options" nodes
     */
    function test_toggleMoreOptions(self) {
        var controller = self.getController();
        var nodes = controller.nodesByAttribute("class", "more-options");
        self.failUnless(0 < nodes.length);

        for(var i = 0; i < nodes.length; i++) {
            self.assertEquals(nodes[i].style.display, "none");
        }
        controller.toggleMoreOptions();
        for(i = 0; i < nodes.length; i++) {
            self.assertEquals(nodes[i].style.display, "");
        }
    },

    /**
     * TestL{Quotient.Compose.Controller._toggleDisclosureLabels}
     */
    function test_toggleDisclosureLabels(self) {
        var controller = self.getController(),
            node = document.createElement("div"),
            l1 = document.createElement("div"),
            l2 = document.createElement("div");

        l1.className = "closed-label";
        l2.className = "open-label";

        l2.style.display = "none";
        node.appendChild(l1);
        node.appendChild(l2);

        controller._toggleDisclosureLabels(node);

        self.assertEquals(l1.style.display, "none");
        self.assertEquals(l2.style.display, "");

        controller._toggleDisclosureLabels(node);

        self.assertEquals(l1.style.display, "");
        self.assertEquals(l2.style.display, "none");
    });

/**
 * Tests for compose autocomplete
 */
Quotient.Test.ComposeAutoCompleteTestCase = Nevow.Athena.Test.TestCase.subclass('Quotient.Test.ComposeAutoCompleteTestCase');
Quotient.Test.ComposeAutoCompleteTestCase.methods(
    /**
     * Make a L{Mantissa.AutoComplete.Controller} with a
     * L{Quotient.Compose.EmailAddressAutoCompleteModel} and a
     * L{Quotient.Compose.EmailAddressAutoCompleteView}
     */
    function _setUp(self) {
        self.textbox = document.createElement("textarea");
        self.node.appendChild(self.textbox);
        self.completionsNode = document.createElement("div");
        self.node.appendChild(self.completionsNode);

        self.controller = Mantissa.AutoComplete.Controller(
                            Quotient.Compose.EmailAddressAutoCompleteModel(
                                [['Larry', 'larry@host'],
                                 ['Larry Joey', 'larryjoey@host'],
                                 ['Xavier A.', 'other@host']]),
                            Quotient.Compose.EmailAddressAutoCompleteView(
                                self.textbox, self.completionsNode),
                            function(f, when) {
                                f();
                            });
    },

    /**
     * Send a fake keypress event for key C{keyCode} to C{node}
     *
     * @param node: node with C{onkeypress} handler
     * @type keyCode: C{Number}
     */
    function _fakeAKeypressEvent(self, node, keyCode) {
        node.onkeypress({keyCode: keyCode});
    },

    /**
     * Check that the DOM inside C{self.completionsNode} looks like the right
     * DOM for the list of completions C{completions}
     *
     * @type completions: C{Array} of C{String}
     */
    function _checkDOMCompletions(self, completions) {
        self.assertEquals(completions.length,
                          self.completionsNode.childNodes.length);

        for(var i = 0; i < completions.length; i++) {
            self.assertEquals(
                completions[i],
                self.completionsNode.childNodes[i].firstChild.nodeValue);
        }
    },

    /**
     * Test L{Quotient.Compose.EmailAddressAutoCompleteModel.isCompletion}
     */
    function test_isCompletion(self) {
        self._setUp();

        var model = self.controller.model;
        var nameAddr = ['XXX Joe', 'xyz@host.tld'];

        self.failUnless(model.isCompletion('jo', nameAddr));
        self.failUnless(model.isCompletion('xy', nameAddr));
        self.failUnless(model.isCompletion('xx', nameAddr));
        self.failUnless(model.isCompletion('host', nameAddr));
        self.failUnless(model.isCompletion('host.tld', nameAddr));
    },

    /**
     * Negative tests for
     * L{Quotient.Compose.EmailAddressAutoCompleteModel.isCompletion}
     */
    function test_isNotCompletion(self) {
        self._setUp();

        var model = self.controller.model,
            nameAddr = ['XXX Joe', 'xyz@host.tld'];

        self.failIf(model.isCompletion(' ', nameAddr));
        self.failIf(model.isCompletion('', nameAddr));
        self.failIf(model.isCompletion('.t', nameAddr));
    },

    /**
     * Test that a list of completions is visible when appropriate
     */
    function test_visibleCompletions(self) {
        self._setUp();

        self.controller.view.setValue('Larry');
        /* 0 is the keycode for all alphanumeric keypresses with onkeypress */
        self._fakeAKeypressEvent(self.textbox, 0);

        self.assertEquals(self.completionsNode.style.display, "");
        self._checkDOMCompletions(['"Larry" <larry@host>',
                                   '"Larry Joey" <larryjoey@host>']);
    },

    /**
     * Test that the completions node isn't visible when there are no
     * completions
     */
     function test_invisibleCompletions(self) {
        self._setUp();

        self.controller.view.setValue('Z');
        self._fakeAKeypressEvent(self.textbox, 0);

        self.assertEquals(self.completionsNode.style.display, "none");
        self._checkDOMCompletions([]);
    });



/**
 * Tests for roundtripping of recipient addresses
 */
Quotient.Test.ComposeToAddressTestCase = Nevow.Athena.Test.TestCase.subclass('Quotient.Test.ComposeToAddressTestCase');
Quotient.Test.ComposeToAddressTestCase.methods(
    /**
     * Retrieve a compose widget from the server, add it as a child widget
     *
     * @param key: unique identifier for the test method
     * @param fromAddress: comma separated string of email addresses with
     * which to seed the ComposeFragment.
     */
    function setUp(self, key, fromAddress) {
        var result  = self.callRemote('getComposeWidget', key, fromAddress);
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                self.scrollingWidget = widget;
                self.node.appendChild(widget.node);
                return widget;
            });
        return result;
    },

    /**
     * Create a compose widget initialized with some from addresses, save a
     * draft, make sure that the server got the addresses which we specified
     */
    function test_roundtrip(self) {
        var addrs = ['foo@bar', 'bar@baz'];
        var result = self.setUp('roundtrip', addrs);
        result.addCallback(
            function(composer) {
                /* save a draft, but bypass all the dialog/looping stuff */
                composer.nodeByAttribute("name", "draft").checked = true;
                return composer.submit();
            });
        result.addCallback(
            function(result) {
                self.assertArraysEqual(result, addrs);
            });
        return result;
    });


Quotient.Test.MessageDetailTestHelper = Divmod.Class.subclass('Quotient.Test.MessageDetailTestHelper');
/**
 * A helper class which wraps a message detail and provides some utility
 * methods for checking various things about it
 */
Quotient.Test.MessageDetailTestHelper.methods(
    function __init__(self, widget) {
        self.widget = widget;
    },

    /**
     * Assert that the msg detail header fields that belong inside the "More
     * Detail" panel are visible or not
     *
     * @param failureFunction: function to call with a descriptive string if
     * we find something inconsistent
     * @type failureFunction: function
     *
     * @param visible: do we expect "More Detail" to be visible or not?
     * @type visible: boolean
     */
    function checkMoreDetailVisibility(self, failureFunction, visible) {
        var rows = self.widget.nodesByAttribute(
                    "class", "detailed-row");
        if(rows.length == 0) {
            failureFunction("expected at least one 'More Detail' row");
        }
        for(var i = 0; i < rows.length; i++) {
            if(visible != (rows[i].style.display != "none")) {
                failureFunction("one of the 'More Detail' rows has the wrong visibility");
            }
        }
    },

    /**
     * Collect the names/nodes of the headers being displayed by our
     * L{Quotient.Message.MessageDetail} widget, by looking at its DOM
     *
     * @return: mapping of header names to nodes
     * @type: C{Object}
     */
    function collectHeaders(self) {
        var hdrs = self.widget.firstNodeByAttribute("class", "msg-header-table"),
            fieldValues = {},
            cols, fieldName;

        function getElementsByTagNameShallow(parent, tagName) {
            var acc = [];
            for(var i = 0; i < parent.childNodes.length; i++) {
                if(parent.childNodes[i].tagName &&
                    parent.childNodes[i].tagName.toLowerCase() == tagName) {
                    acc.push(parent.childNodes[i]);
                }
            }
            return acc;
        }

        var rows = getElementsByTagNameShallow(hdrs, "tr");

        for(var i = 0; i < rows.length; i++) {
            cols = getElementsByTagNameShallow(rows[i], "td");
            if(cols.length < 2) {
                continue;
            }
            fieldName = cols[0].firstChild.nodeValue;
            fieldName = fieldName.toLowerCase().slice(0, -1);
            fieldValues[fieldName] = cols[1];
        }
        return fieldValues;
    },

    /**
     * Like L{collectHeaders}, but the values in the object returned are the
     * string values of each header, and headers without a simple string value
     * will not be included
     */
    function collectStringHeaders(self) {
        var headers = {}, _headers = self.collectHeaders();
        for(var k in _headers) {
            if(_headers[k].childNodes.length == 1
                && !_headers[k].firstChild.tagName) {
                headers[k] = _headers[k].firstChild.nodeValue;
            }
        }
        return headers;
    });


/**
 * Check that the message detail renders correctly
 */
Quotient.Test.MsgDetailTestCase = Nevow.Athena.Test.TestCase.subclass('Quotient.Test.MsgDetailTestCase');
Quotient.Test.MsgDetailTestCase.methods(
    function setUp(self) {
        var d = self.callRemote('setUp');
        d.addCallback(
            function (widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        d.addCallback(
            function (widget) {
                self.node.appendChild(widget.node);
                self.msgDetail = widget;
                self.testHelper = Quotient.Test.MessageDetailTestHelper(widget);
            });
        return d;
    },

    /**
     * Test that the text headers in the DOM reflect the headers of the
     * message that is being rendered
     */
    function test_headers(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                var fieldvalues = self.testHelper.collectStringHeaders();

                var assertFieldsEqual = function(answers) {
                    for(var k in answers) {
                        self.assertEquals(fieldvalues[k], answers[k]);
                    }
                }

                assertFieldsEqual(
                    {subject: "the subject",
                     sent: "Wed, 31 Dec 1969 19:00:00 -0500",
                     received: "Wed, 31 Dec 1969 19:00:01 -0500"});
            });
        return result;
    },

    /**
     * Tests for the "More Detail" feature of
     * L{Quotient.Message.MessageDetail}
     */
    function test_moreDetail(self) {
        var result = self.setUp(),
            failureFunc = function(m) {
                self.fail(m);
            },
            checkAndToggle = function(value) {
                return function(ignored) {
                    self.testHelper.checkMoreDetailVisibility(
                        failureFunc, value);
                    var result = self.msgDetail.callRemote("getMoreDetailSetting");
                    result.addCallback(
                        function(setting) {
                            self.assertEquals(setting, value);
                            return self.msgDetail.toggleMoreDetail();
                        });
                    return result;
                }
            };

        result.addCallback(checkAndToggle(false));
        result.addCallback(checkAndToggle(true));
        result.addCallback(checkAndToggle(false));
        return result;
    });

Quotient.Test.MsgDetailTagsTestCase = Nevow.Athena.Test.TestCase.subclass(
    'Quotient.TestCase.MsgDetailTagsTestCase');

/**
 * Tests for L{Quotient.Message.MessageDetail} and tags
 */
Quotient.Test.MsgDetailTagsTestCase.methods(
    /**
     * @param tags: tags to assign to the message
     * @type tags: C{Array} of C{String}
     */
    function setUp(self, tags) {
        var d = self.callRemote('setUp', tags);
        d.addCallback(
            function (widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        d.addCallback(
            function (widget) {
                self.node.appendChild(widget.node);
                self.msgDetail = widget;
            });
        return d;
    },

    /**
     * Test that the L{Quotient.Message.MessageDetail} is initialized with a
     * list of a tags that reflects what is in the database
     */
    function test_initialState(self) {
        var D = self.setUp(['tag1', 'tag2']);
        D.addCallback(
            function(ignored) {
                self.assertArraysEqual(self.msgDetail.tags, ['tag1', 'tag2']);
            });
        return D;
    },

    /**
     * Figure out the tags of the message by looking at its DOM
     *
     * @rtype: C{Array} of C{String}
     */
    function _collectTagsFromDOM(self) {
        var node = self.msgDetail.firstNodeByAttribute(
            'class', 'tags-display'),
            tags = [];
        for(var i = 0; i < node.childNodes.length; i++) {
            tags.push(node.childNodes[i].firstChild.nodeValue);
        }
        return tags;
    },

    /**
     * Same as L{test_initialState}, but look at the DOM
     */
    function test_initialDOMState(self) {
        var D = self.setUp(['tag1', 'tag2']);
        D.addCallback(
            function(ignored) {
                self.assertArraysEqual(
                    self._collectTagsFromDOM(),
                    ['tag1', 'tag2']);
            });
        return D;
    },

    /**
     * Test L{Quotient.Message.MessageDetail.saveTags} when a tag is being
     * removed and one is being added.
     */
    function test_saveTags(self) {
        var D = self.setUp(['tag1', 'tag2']);
        D.addCallback(
            function(ignored) {
                return self.msgDetail.saveTags(['tag1', 'tag3']);
            });
        D.addCallback(
            function(ignored) {
                self.assertArraysEqual(
                    self.msgDetail.tags,
                    ['tag1', 'tag3']);
            });
        return D;
    },

    /**
     * Same as L{test_saveTags}, but look at the DOM
     */
    function test_saveTagsDOM(self) {
        var D = self.setUp(['tag1', 'tag2']);
        D.addCallback(
            function(ignored) {
                return self.msgDetail.saveTags(['tag1', 'tag3']);
            });
        D.addCallback(
            function(ignored) {
                self.msgDetail._updateTagList();
                self.assertArraysEqual(
                    self._collectTagsFromDOM(),
                    ['tag1', 'tag3']);
            });
        return D;
    },

    /**
     * Test L{Quotient.Message.MessageDetail.editTags}
     */
    function test_editTags(self) {
        var D = self.setUp(['tag1', 'tag2', 'tag3']);
        D.addCallback(
            function(ignored) {
                self.msgDetail.editTags();
                var input = self.msgDetail.editTagsContainer.tags;
                self.assertEquals(input.style.display, "");
                self.assertEquals(input.value, 'tag1, tag2, tag3');
            });
        return D;
    },

    /**
     * Check that the state of the DOM accurately reflects our expectations
     * for the case where a message has no tags
     */
    function _checkNoTags(self) {
        var tagsDisplay = self.msgDetail.tagsDisplay;
        self.assertEquals(
            tagsDisplay.childNodes.length, 1);
        self.assertEquals(
            tagsDisplay.firstChild.nodeValue.toLowerCase(), 'no tags');
    },

    /**
     * Test L{Quotient.Message.MessageDetail._updateTagList} when there are no
     * tags.  A "No Tags" message should be shown
     */
    function test_updateNoTags(self) {
        var D = self.setUp([]);
        D.addCallback(
            function(ignored) {
                self.msgDetail._updateTagList();
                self._checkNoTags();
            });
        return D;
    },

    /**
     * Test L{Quotient.Message.MessageDetail} when no tags have been changed
     */
    function test_saveSameTags(self) {
        var D = self.setUp(['tag1', 'tag2']);
        D.addCallback(
            function(ignored) {
                return self.msgDetail.saveTags(['tag1', 'tag2']);
            });
        D.addCallback(
            function(ignored) {
                self.msgDetail._updateTagList();
                self.assertArraysEqual(
                    self._collectTagsFromDOM(),
                    ['tag1', 'tag2']);
            });
        return D;
    },

    /**
     * Test L{Quotient.Message.MessageDetail} when all tags have been removed
     */
    function test_saveRemovedTags(self) {
        var D = self.setUp(['tag1', 'tag2']);
        D.addCallback(
            function(ignored) {
                return self.msgDetail.saveTags([]);
            });
        D.addCallback(
            function(ignored) {
                self.msgDetail._updateTagList();
                self._checkNoTags();
            });
        return D;
    });



Quotient.Test.MsgDetailAddPersonTestCase = Nevow.Athena.Test.TestCase.subclass(
    'Quotient.Test.MsgDetailAddPersonTestCase');

/**
 * Test case for the interaction between L{Quotient.Common.SenderPerson} and
 * L{Quotient.Message.MessageDetail}
 */
Quotient.Test.MsgDetailAddPersonTestCase.methods(
    function setUp(self, key) {
        var d = self.callRemote('setUp', key);
        d.addCallback(
            function (widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        d.addCallback(
            function (widget) {
                self.node.appendChild(widget.node);
                self.msgDetail = widget;
            });
        return d;
    },

    /**
     * Test showing Add Person dialog, and adding a person
     */
    function test_addPerson(self) {
        var result = self.setUp('addPerson');
        result.addCallback(
            function() {
                var sp = Nevow.Athena.Widget.get(
                            self.msgDetail.firstNodeByAttribute(
                                "athena:class",
                                "Quotient.Common.SenderPerson"));
                sp.showAddPerson();

                self.assertEquals(sp.dialog.node.style.display, "");
                self.assertEquals(sp.dialog.node.style.position, "absolute");

                var dialogLiveForm = Nevow.Athena.Widget.get(
                                        sp.dialog.node.getElementsByTagName(
                                            "form")[0]);

                return dialogLiveForm.submit().addCallback(
                    function() {
                        return self.callRemote("verifyPerson", "addPerson");
                    });
            });
        return result;
    });

Quotient.Test.MsgDetailInitArgsTestCase = Nevow.Athena.Test.TestCase.subclass(
                                                'Quotient.Test.MsgDetailInitArgsTestCase');
/**
 * Tests for the initArgs for L{Quotient.Message.MessageDetail}
 */
Quotient.Test.MsgDetailInitArgsTestCase.methods(
    function setUp(self) {
        var d = self.callRemote('setUp');
        d.addCallback(
            function (widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        d.addCallback(
            function (widget) {
                self.node.appendChild(widget.node);
                self.msgDetail = widget;
                self.testHelper = Quotient.Test.MessageDetailTestHelper(widget);
            });
        return d;
    },

    /**
     * Our python class returns True for the initial visibility of the "More
     * Detail" panel.  Make sure that this is reflected client-side
     */
    function test_moreDetailInitArg(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                self.testHelper.checkMoreDetailVisibility(
                    function(m) {
                        self.fail(m);
                    }, true);
            });
        return result;
    });

Quotient.Test.MsgDetailHeadersTestCase = Nevow.Athena.Test.TestCase.subclass(
                                            'Quotient.Test.MsgDetailHeadersTestCase');
/**
 * Tests for rendering of messages with various combinations of headers
 */
Quotient.Test.MsgDetailHeadersTestCase.methods(
    function setUp(self, headers) {
        var d = self.callRemote('setUp', headers);
        d.addCallback(
            function (widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        d.addCallback(
            function (widget) {
                self.node.appendChild(widget.node);
                self.msgDetail = widget;
                self.testHelper = Quotient.Test.MessageDetailTestHelper(widget);
            });
        return d;
    },

    /**
     * Test rendering of a message with a Resent-From header but no Resent-To
     */
    function test_resentFromNoResentTo(self) {
        var result = self.setUp({'Resent-From': 'user@host'});
        result.addCallback(
            function(ignored) {
                var headers = self.testHelper.collectStringHeaders();
                self.assertEquals(headers['resent from'], 'user@host');
                self.assertEquals(headers['resent to'], undefined);
            });
        return result;
    });

Quotient.Test.MsgDetailCorrespondentPeopleTestCase = Nevow.Athena.Test.TestCase.subclass(
                                            'Quotient.Test.MsgDetailCorrespondentPeopleTestCase');
/**
 * Tests for rendering a message where various correspondents are or aren't
 * represented by L{xmantissa.people.Person} items in the store
 */
Quotient.Test.MsgDetailCorrespondentPeopleTestCase.methods(
    function setUp(self, peopleAddresses, sender, recipient, cc) {
        var d = self.callRemote(
            'setUp', peopleAddresses, sender, recipient, cc);
        d.addCallback(
            function (widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        d.addCallback(
            function (widget) {
                self.node.appendChild(widget.node);
                self.msgDetail = widget;
                self.testHelper = Quotient.Test.MessageDetailTestHelper(widget);
            });
        return d;
    },

    /**
     * Check that there are nodes for C{count} person widgets inside C{node},
     * and no other nodes.
     *
     * @param node: the node to look inside
     * @type node: node
     * @param count: the expected number of person widgets
     * @type count: C{Number}
     */
    function assertPeopleWidgets(self, node, count) {
        self.assertEquals(node.childNodes.length, count);
        self.assertEquals(
            Nevow.Athena.NodesByAttribute(
                node, "class", "person-widget").length,
            count);
    },

    /**
     * Checker that there are nodes for C{count} add person widgets inside
     * C{node} and no other nodes.
     *
     * @param node: the node to look inside
     * @type node: node
     * @param count: the expected number of person widgets
     * @type count: C{Number}
     */
    function assertAddPersonWidgets(self, node, count) {
        self.assertEquals(node.childNodes.length, count);
        self.assertEquals(
            Nevow.Athena.NodesByAttribute(
                node, 'athena:class', 'Quotient.Common.SenderPerson').length,
            count);
    },

    /**
     * Test rendering a message with no people in the store.  Check that the
     * sender header is rendered as an add person fragment
     */
    function test_senderNoPeople(self) {
        var result = self.setUp(
            [], 'sender@host', 'recipient@host', null);
        result.addCallback(
            function(ignored) {
                var headers = self.testHelper.collectHeaders();
                self.assertAddPersonWidgets(headers['from'], 1);
            });
        return result;
    },

    /**
     * Test rendering a message where the sender address corresponds to the
     * email address of a person in the store.
     *
     * The sender header should render as a person fragment
     */
    function test_senderAPerson(self) {
        var result = self.setUp(
            ['sender@host'], 'sender@host', 'recipient@host', null);
        result.addCallback(
            function(ignored) {
                var headers = self.testHelper.collectHeaders();
                self.assertPeopleWidgets(headers['from'], 1);
            });
        return result;
    },

    /**
     * Test rendering a message with CC set but no people in the store
     *
     * There should be nodes for two L{Quotient.Common.SenderPerson} instances
     * inside the CC header node.
     */
    function test_ccNoPeople(self) {
        var result = self.setUp(
            [], 'sender@host', 'recipient@host', '1@host, 2@host');
        result.addCallback(
            function(ignored) {
                var headers = self.testHelper.collectHeaders();
                self.assertAddPersonWidgets(headers['cc'], 2);
            });
        return result;
    },

    /**
     * Test rendering a message where CC is set to an email address that
     * belongs to a person in the store
     *
     * The CC header node should contain the node for one person widget
     */
    function test_ccAPerson(self) {
        var result = self.setUp(
            ['1@host'], 'sender@host', 'recipient@host', '1@host');
        result.addCallback(
            function(ignored) {
                var headers = self.testHelper.collectHeaders();
                self.assertPeopleWidgets(headers['cc'], 1);
            });
        return result;
    },

    /**
     * Test rendering a message with recipient set but no people in the store
     *
     * There should be a node for a L{Quotient.Common.SenderPerson} instance
     * inside the recipient header node.
     */
    function test_recipientNoPeople(self) {
        var result = self.setUp([], 'sender@host', 'recipient@host', null);
        result.addCallback(
            function(ignored) {
                var headers = self.testHelper.collectHeaders();
                self.assertAddPersonWidgets(headers['to'], 1);
            });
        return result;
    },

    /**
     * Test rendering a message with the recipient set to an email address
     * which also belongs to a person in the store
     *
     * There should be one person widget in the recipient header node
     */
    function test_recipientAPerson(self) {
        var result = self.setUp(
            ['recipient@host'], 'sender@host', 'recipient@host', null);
        result.addCallback(
            function(ignored) {
                var headers = self.testHelper.collectHeaders();
                self.assertPeopleWidgets(headers['to'], 1);
            });
        return result;
    });


Quotient.Test.PostiniConfigurationTestCase = Nevow.Athena.Test.TestCase.subclass(
    'Quotient.Test.PostiniConfigurationTestCase');
/**
 * Tests for the Postini configuration form on the the Settings page.
 * See L{Quotient.Spam}.
 */
Quotient.Test.PostiniConfigurationTestCase.methods(
    function setUp(self) {
        var d = self.callRemote('setUp');
        d.addCallback(
            function (widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        d.addCallback(
            function (widget) {
                self.postiniConfig = widget.childWidgets[0];
                self.usePostiniScore = self.postiniConfig.nodeByAttribute(
                    'name', 'usePostiniScore');
                self.postiniThreshhold = self.postiniConfig.nodeByAttribute(
                    'name', 'postiniThreshhold');
                self.node.appendChild(widget.node);
            });
        return d;
    },

    /**
     * Test that the postini configuration form is rendered with a checkbox
     * and a text field and that the checkbox defaults to unchecked and the
     * text field to "0.03".
     */
    function test_defaults(self) {
        var d = self.setUp();
        d.addCallback(
            function (ignored) {
                self.assertEquals(self.usePostiniScore.checked, false);
                self.assertEquals(self.postiniThreshhold.value, '0.03');
            });
        return d;
    },

    /**
     * Test that submitting the form with changed values changes the
     * configuration on the server
     */
    function test_submitChangesSettings(self) {
        var d = self.setUp();
        d.addCallback(
            function (ignored) {
                self.usePostiniScore.checked = true;
                self.postiniThreshhold.value = '5.0';
                return self.postiniConfig.submit();
            });
        d.addCallback(
            function() {
                return self.callRemote('checkConfiguration');
            });
        return d;
    },

    /**
     * Test that submitting the form preserves the new values on the form.
     */
    function test_submitPreservesFormValues(self) {
        var d = self.setUp();
        d.addCallback(
            function (ignored) {
                self.usePostiniScore.checked = true;
                self.postiniThreshhold.value = '5.0';
                return self.postiniConfig.submit();
            });
        d.addCallback(
            function() {
                self.assertEquals(self.usePostiniScore.checked, true);
                self.assertEquals(self.postiniThreshhold.value, '5.0');
            });
        return d;
    });


Quotient.Test.AddGrabberTestCase = Nevow.Athena.Test.TestCase.subclass(
                                        'Quotient.Test.AddGrabberTestCase');

Quotient.Test.AddGrabberTestCase.methods(
    function test_addGrabber(self) {
        var form = Nevow.Athena.Widget.get(
                        self.firstNodeByAttribute(
                            'athena:class',
                            'Quotient.Grabber.AddGrabberFormWidget'));
        var inputs = form.gatherInputs();

        inputs['domain'].value = 'foo.bar';
        inputs['username'].value = 'foo';
        inputs['password1'].value = 'foo';
        inputs['password2'].value = 'zoo';

        return form.submit().addErrback(
            function() {
                self.fail('AddGrabberFormWidget did not catch the submit error');
            });
    });

Quotient.Test.GrabberListTestCase = Nevow.Athena.Test.TestCase.subclass(
                                        'Quotient.Test.GrabberListTestCase');

Quotient.Test.GrabberListTestCase.methods(
    /**
     * Test that the grabber list is initially visible when
     * we have one grabber, and that it becomes invisible when
     * we delete the grabber
     */
    function test_visibility(self) {
        var scrollerNode = self.firstNodeByAttribute(
            "class", "scrolltable-widget-node");

        var scrollWidget = Nevow.Athena.Widget.get(scrollerNode)
        scrollWidget.initializationDeferred.addCallback(
            function(ignored) {
                /* there is one grabber.  make sure the table is visible */
                self.assertEquals(scrollerNode.style.display, "");

                var D = self.callRemote("deleteGrabber");
                D.addCallback(
                    function() {
                        /* grabber has been deleted.  reload scrolltable */
                        D = scrollWidget.emptyAndRefill();
                        D.addCallback(
                            function() {
                                /* make sure it isn't visible */
                                self.assertEquals(scrollerNode.style.display, "none");
                            });
                        return D;
                    });
                return D;
            });
        return scrollWidget.initializationDeferred;
    });

Quotient.Test.ButtonTogglerTestCase = Nevow.Athena.Test.TestCase.subclass(
    'Quotient.Test.ButtonTogglerTestCase');
/**
 * Tests for L{Quotient.Common.ButtonToggler}
 */
Quotient.Test.ButtonTogglerTestCase.methods(
    /**
     * Make an element which is structured like a Quotient UI button, and
     * return it
     *
     * @return: object with "button" and "link" members, where "button" is the
     * button node, and "link" is child <a> node
     * @rtype: C{Object}
     */
    function _makeButton(self) {
        var button = self.nodeByAttribute("class", "button"),
            button = button.cloneNode(true),
            link = button.getElementsByTagName("a")[0];

        button.style.opacity = 1;
        return {button: button, link: link};
    },

    /**
     * Return an object with "toggler", "disabledTest" and "enabledTest"
     * members, where "toggler" is a L{Quotient.Common.ButtonToggler} and the
     * other two members are thunks which verify that the current state of the
     * button is consistent with what we expect for the disabled and enabled
     * states, respectively
     *
     * @rtype: C{Object}
     */
    function _makeTogglerTester(self) {
        var button = self._makeButton(),
            onclick = button.link.onclick = function() {
                return true;
            },
            OPACITY = 0.32,
            toggler = Quotient.Common.ButtonToggler(button.button, OPACITY);

        return {toggler: toggler,
                disabledTest: function() {
                    self.assertEquals(
                        button.button.style.opacity, OPACITY.toString());
                    /* our onclick returns true, and we want to make sure that
                     * the handler in place returns false, so that clicks do
                     * nothing */
                    self.assertEquals(button.link.onclick(), false);
                },
                enabledTest: function() {
                   self.assertEquals(button.button.style.opacity, '1');
                   self.assertEquals(button.link.onclick, onclick);
                }};
    },

    /**
     * Test the C{enable}/C{disable} methods of
     * L{Quotient.Common.ButtonToggler}
     */
    function test_enableDisable(self) {
        var tester = self._makeTogglerTester();

        tester.enabledTest();
        tester.toggler.disable();
        tester.disabledTest();
        tester.toggler.enable();
        tester.enabledTest();
    },

    /**
     * Test L{Quotient.Common.ButtonToggler.disableUntilFires}
     */
    function test_disableUntilFires(self) {
        var tester = self._makeTogglerTester(),
            D = Divmod.Defer.Deferred(),
            DEFERRED_RESULT = 'hi';

        tester.enabledTest();
        tester.toggler.disableUntilFires(D);
        tester.disabledTest();
        D.addCallback(
            function(result) {
                self.assertEquals(result, DEFERRED_RESULT);
                tester.enabledTest();
            });
        D.callback(DEFERRED_RESULT);
        return D;
    },

    /**
     * Test opacity defaulting
     */
    function test_opacityDefaulting(self) {
        var button = self._makeButton(),
            toggler = Quotient.Common.ButtonToggler(button.button);

        button.link.onclick = function() {
            /* just set it to something so the toggler doesn't complain */
        }
        self.assertEquals(button.button.style.opacity, '1');
        toggler.disable();
        self.assertEquals(button.button.style.opacity, '0.4');
    });

Quotient.Test.ShowNodeAsDialogTestCase = Nevow.Athena.Test.TestCase.subclass(
                                            'Quotient.Test.ShowNodeAsDialogTestCase');

Quotient.Test.ShowNodeAsDialogTestCase.methods(
    /**
     * Make a node suitable for showing as a dialog, and insert it below our
     * node in the DOM
     *
     * @param testName: name of the test
     * @type testName: C{String}
     *
     * @return: the node
     */
    function setUp(self, testName) {
        var node = document.createElement("div");
        node.style.display = "none";
        node.className = "ShowNodeAsDialogTestCase-" + testName + "-dialog";
        self.node.appendChild(node);
        return node;
    },

    function test_showNodeAsDialog(self) {
        var node = self.setUp("showNodeAsDialog");
        /* show it as a dialog */
        var dialog = Quotient.Common.Util.showNodeAsDialog(node);

        var getElements = function() {
            return Nevow.Athena.NodesByAttribute(
                    document.body,
                    "class",
                    node.className);
        }

        /* get all elements with the same class name as our node */
        var nodes = getElements();

        /* should be two - the original and the cloned dialog */
        self.assertEquals(nodes.length, 2);
        var orignode = nodes[0], dlgnode = nodes[1];
        self.assertEquals(dlgnode, dialog.node);

        self.assertEquals(orignode.style.display, "none");
        self.assertEquals(dlgnode.style.display, "");
        self.assertEquals(dlgnode.style.position, "absolute");

        dialog.hide();

        nodes = getElements();

        /* should be one, now that the dialog has been hidden */
        self.assertEquals(nodes.length, 1);
        self.assertEquals(nodes[0], orignode);
    },

    /**
     * Test that L{Quotient.Common.Util.showNodeAsDialog} takes the left/top
     * scrollbar offsets into account when centering the dialog
     */
    function test_scrollAlignment(self) {
        var node = document.createElement("div");
        node.style.overflow = "scroll";
        node.style.height = "100px";

        var stretch = document.createElement("div");
        stretch.appendChild(document.createTextNode("hi"));
        stretch.style.height = "1000px";
        node.appendChild(stretch);

        document.body.appendChild(node);

        var V_SCROLL_OFFSET = 13;
        node.scrollTop = V_SCROLL_OFFSET;

        var dlgNode = self.setUp("scrollAlignment"),
            dlg = Quotient.Common.Util.showNodeAsDialog(dlgNode, node);

        var nodeSize = Divmod.Runtime.theRuntime.getElementSize(node),
            dlgSize = Divmod.Runtime.theRuntime.getElementSize(dlgNode),
            /* figure out the position at which the dialog should appear.  we
             * want it to start so that the middle of it will be in the middle
             * of the _visible_ portion of the parent node, so we calculate
             * half of the parent height minus half of the dialog height,
             * offset vertically by the offset of the first visible
             * (unclipped) pixel in the parent */
            top = Math.floor((nodeSize.h / 2) - (dlgSize.h / 2)) + V_SCROLL_OFFSET;

        self.assertEquals(parseInt(dlg.node.style.top), top);

        dlg.hide();
    });

Quotient.Test.ShowSimpleWarningDialogTestCase = Nevow.Athena.Test.TestCase.subclass(
                                                    'Quotient.Test.ShowSimpleWarningDialogTestCase');

/**
 * Tests for L{Quotient.Common.Util.showSimpleWarningDialog}
 */
Quotient.Test.ShowSimpleWarningDialogTestCase.methods(
    /**
     * Test that the text we pass gets put inside the dialog node
     */
    function test_dialogText(self) {
        var text = "HI SOME TEXT",
            dlg = Quotient.Common.Util.showSimpleWarningDialog(text),
            node = dlg.node;
        self.assertEquals(
            Nevow.Athena.NodeByAttribute(
                node, "class", "simple-warning-dialog-text").firstChild.nodeValue,
            text);
        dlg.hide();
    },

    /**
     * Test that the dialog is visible
     */
    function test_visibility(self) {
        var dlg = Quotient.Common.Util.showSimpleWarningDialog(""),
            node = dlg.node;
        self.assertEquals(node.parentNode, document.body);
        self.assertEquals(node.style.display, "");
        dlg.hide();
    });


Quotient.Test.DraftsTestCase = Nevow.Athena.Test.TestCase.subclass(
                                    'Quotient.Test.DraftsTestCase');

/**
 * Tests for xquotient.compose.DraftsScreen
 */
Quotient.Test.DraftsTestCase.methods(
    /**
     * Get a handle on the drafts scrolltable, and return
     * a deferred that'll fire when it's done initializing
     */
    function setUp(self) {
        if(!self.scroller) {
            self.scroller = Nevow.Athena.Widget.get(
                                self.firstNodeByAttribute(
                                    "athena:class",
                                    "Quotient.Compose.DraftListScrollingWidget"));
        }
        return self.scroller.initializationDeferred;
    },

    /**
     * Basic test, just make sure the scrolltable can initialize
     */
    function test_initialization(self) {
        return self.setUp();
    },

    /**
     * Assert that the rows in the drafts scrolltable have subjects
     * that match those of the items created by our python counterpart
     */
    function test_rows(self) {
        return self.setUp().addCallback(
            function() {
                for(var i = 4; i <= 0; i--) {
                    self.assertEquals(
                        parseInt(self.scroller.model.getRowData(i).subject), i);
                }
            });
    });

Quotient.Test.MsgBodyTestCase = Nevow.Athena.Test.TestCase.subclass(
    'Quotient.Test.MsgBodyTestCase');
/**
 * Tests for L{Quotient.Message.BodyController}
 */
Quotient.Test.MsgBodyTestCase.methods(
    function setUp(self, key) {
        var D = self.callRemote('setUp', key);
        D.addCallback(
            function (widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        D.addCallback(
            function (widget) {
                self.node.appendChild(widget.node);
                self.msgBody = widget;
            });
        return D;
    },

    /**
     * Get the text of the current message body, stripped of leading and
     * trailing whitespace
     *
     * @rtype: C{String}
     */
    function getBody(self) {
        var node = self.msgBody.firstNodeByAttribute(
            'class', 'message-body');
        return Quotient.Common.Util.stripLeadingTrailingWS(
            node.firstChild.nodeValue);
    },

    /**
     * Test that the initial message body text corresponds to the text of the
     * text/plain part in the message
     */
    function test_initialTextPlain(self) {
        var D = self.setUp('initialTextPlain');
        D.addCallback(
            function(ignored) {
                self.assertEquals(self.getBody(), 'this is the text/plain');
            });
        return D;
    },

    /**
     * Test changing the type of the rendered part
     */
    function test_changeType(self) {
        var D = self.setUp('changeType');
        D.addCallback(
            function(ignored) {
                return self.msgBody.chooseDisplayMIMEType('text/html');
            });
        D.addCallback(
            function(newWidget) {
                self.assertEquals(
                    newWidget.node.getElementsByTagName('iframe').length, 1);
                self.assertEquals(
                    self.msgBody.node.parentNode, null);
            });
        return D;
    });


Quotient.Test.ActionsTestCase = Nevow.Athena.Test.TestCase.subclass(
    'Quotient.Test.ActionsTestCase');
/**
 * Tests for the L{Quotient.Message} actions classes
 * (L{Quotient.Message.ActionsController}, L{Quotient.Message.ActionsView})
 */
Quotient.Test.ActionsTestCase.methods(
    function setUp(self) {
        var result = self.callRemote('setUp');
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                self.actions = widget
            });
        return result;
    },

    function test_getDeferralPeriod(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                var period;
                var form = self.actions.view.deferForm;
                var days = form.days;
                var hours = form.hours;
                var minutes = form.minutes;

                days.value = hours.value = minutes.value = 1;
                period = self.actions.view._getDeferralPeriod();
                self.assertEqual(period.days, 1);
                self.assertEqual(period.hours, 1);
                self.assertEqual(period.minutes, 1);

                days.value = 2;
                period = self.actions.view._getDeferralPeriod();
                self.assertEqual(period.days, 2);
                self.assertEqual(period.hours, 1);
                self.assertEqual(period.minutes, 1);

                hours.value = 3;
                period = self.actions.view._getDeferralPeriod();
                self.assertEqual(period.days, 2);
                self.assertEqual(period.hours, 3);
                self.assertEqual(period.minutes, 1);

                minutes.value = 4;
                period = self.actions.view._getDeferralPeriod();
                self.assertEqual(period.days, 2);
                self.assertEqual(period.hours, 3);
                self.assertEqual(period.minutes, 4);
            });
        return result;
    },

    /**
     * Like L{test_getDeferralPeriod}, but for the utility method
     * L{_deferralStringToPeriod} and L{_getDeferralSelection} (Sorry for
     * putting these together, I think this is a really icky test and I didn't
     * want to type out all this boilerplate twice -exarkun).
     */
    function test_deferralStringtoPeriod(self) {
        var result = self.setUp();
        result.addCallback(
            function(ignored) {
                var period;
                var node = self.actions.view.deferSelect;

                var deferralPeriods = {
                    "one-day": {
                        "days": 1,
                        "hours": 0,
                        "minutes": 0},
                    "one-hour": {
                        "days": 0,
                        "hours": 1,
                        "minutes": 0},
                    "twelve-hours": {
                        "days": 0,
                        "hours": 12,
                        "minutes": 0},
                    "one-week": {
                        "days": 7,
                        "hours": 0,
                        "minutes": 0}
                };

                var option;
                var allOptions = node.getElementsByTagName("option");
                for (var cls in deferralPeriods) {
                    option = Divmod.Runtime.theRuntime.firstNodeByAttribute(node, "class", cls);
                    period = self.actions.view._deferralStringToPeriod(option.value);
                    self.assertEqual(period.days, deferralPeriods[cls].days);
                    self.assertEqual(period.hours, deferralPeriods[cls].hours);
                    self.assertEqual(period.minutes, deferralPeriods[cls].minutes);

                    for (var i = 0; i < allOptions.length; ++i) {
                        if (allOptions[i] === option) {
                            node.selectedIndex = i;
                            break;
                        }
                    }
                    if (i == allOptions.length) {
                        self.fail("Could not find option node to update selection index.");
                    }
                    period = self.actions.view._getDeferralSelection();
                    self.assertEqual(period.days, deferralPeriods[cls].days);
                    self.assertEqual(period.hours, deferralPeriods[cls].hours);
                    self.assertEqual(period.minutes, deferralPeriods[cls].minutes);
                }
            });
        return result;
    },

    /**
     * Test L{Quotient.Message.ActionsView.disableAllUntilFires}
     */
    function test_disableActionButtonsUntilFires(self) {
        var result = self.setUp();
        result.addCallback(
            function(result) {
                var buttons = [],
                    actionNames = self.actions.model.actions;
                for(var i = 0; i < actionNames.length; i++) {
                    /* special-case defer because it isn't really a button */
                    if(actionNames[i] == 'defer') {
                        continue;
                    }
                    buttons.push(
                        Nevow.Athena.NodeByAttribute(
                            self.actions.view._buttonNodes[actionNames[i]],
                            'class',
                            'button'));

                    self.assertEqual(
                        buttons[buttons.length-1].style.opacity, '');
                }

                var d = Divmod.Defer.Deferred();
                self.actions.view.disableAllUntilFires(d);

                for(var i = 0; i < buttons.length; i++) {
                    self.assertNotEqual(buttons[i].style.opacity, '');
                    self.failUnless(parseFloat(buttons[i].style.opacity) < 1);
                }

                d.callback(buttons);
                return d;
            });
        result.addCallback(
            function(buttons) {
                for(var i = 0; i < buttons.length; i++) {
                    self.assertEqual(parseFloat(buttons[i].style.opacity), 1);
                }
            });
        return result;
    },

    /**
     * Tests for L{Quotient.Message.ActionsView.dispatchActionFromSelect}
     */
    function test_dispatchActionFromSelect(self) {
        var result = self.setUp();
        result.addCallback(
            function() {
                var called = 0,
                    handler = function() {
                        called++;
                        return 'HI!';
                    },
                    listener = {messageAction_foo: handler},
                    select = document.createElement('select'),
                    option = document.createElement('option');

                option.value = 'foo';
                select.appendChild(option);

                self.actions.model.setActionListener(listener);

                self.assertEqual(
                    self.actions.view.dispatchActionFromSelect(select),
                    'HI!');
                self.assertEqual(called, 1);

                option.removeAttribute('value');

                self.assertEqual(
                    self.actions.view.dispatchActionFromSelect(select),
                    null);
                self.assertEqual(called, 1);
            });
        return result;
    });
