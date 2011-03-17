// Copyright (c) 2007 Divmod.
// See LICENSE for details.

/**
 * Tests for L{Mantissa.ScrollTable.ScrollModel}
 */

// import Divmod.Defer
// import Divmod.UnitTest
// import Mantissa.People
// import Nevow.Test.WidgetUtil

Mantissa.Test.TestPeople.StubWidget = Divmod.Class.subclass(
    'Mantissa.Test.TestPeople.StubWidget');
/**
 * Stub implementation of L{Nevow.Athena.Widget} used by tests to verify that
 * the correct remote calls are made.
 *
 * @ivar node: The widget's node.
 *
 * @ivar results: An array with one object for each time callRemote has been
 *     invoked.  The objects have the following properties::
 *
 *    deferred: The L{Divmod.Defer.Deferred} which was returned by the
 *              corresponding callRemote call.
 *    method: The name of the remote method which was invoked.
 *    args: An array of the remaining arguments given to the callRemote call.
 *
 * @ivar wasDetached: A flag indicating whether C{detach} was called.
 */
Mantissa.Test.TestPeople.StubWidget.methods(
    function __init__(self) {
        self.node = document.createElement('span');
        self.results = [];
        self.removedRows = [];
        self.wasDetached = false;
    },

    /**
     * Record an attempt to call a method on the server.
     */
    function callRemote(self, method) {
        var result = {};
        result.deferred = Divmod.Defer.Deferred();
        result.method = method;
        result.args = [];
        for (var i = 2; i < arguments.length; ++i) {
            result.args.push(arguments[i]);
        }
        self.results.push(result);
        return result.deferred;
    },

    /**
     * Pretend to be a ScrollingWidget and remember which rows have been
     * removed.
     */
    function removeRow(self, index) {
        self.removedRows.push(index);
    },

    /**
     * Record an attempt to detach this widget.
     */
    function detach(self) {
        self.wasDetached = true;
    });


Mantissa.Test.TestPeople.StubPersonForm = Divmod.Class.subclass(
    'Mantissa.Test.TestPeople.StubPersonForm');
/**
 * Stub implementation of L{Mantissa.People.AddPersonForm} and
 * L{Mantissa.People.EditPersonForm}.
 *
 * @ivar submissionObservers: An array of the objects passed to
 * L{observeSubmission}
 */
Mantissa.Test.TestPeople.StubPersonForm.methods(
    function __init__(self) {
        self.submissionObservers = [];
    },

    /**
     * Ignore the widget hierarchy.
     */
    function setWidgetParent(self, parent) {
    },

    /**
     * Remember an observer in L{submissionObservers}.
     */
    function observeSubmission(self, observer) {
        self.submissionObservers.push(observer);
    });


Mantissa.Test.TestPeople.StubOrganizerView = Divmod.UnitTest.TestCase.subclass(
    'Mantisa.Test.TestPeople.StubOrganizerView');
/**
 * Stub L{Mantissa.People.OrganizerView}.
 *
 * @ivar detailNode: The current detail node.
 * @type detailNode: DOM Node or C{null}.
 *
 * @ivar editLinkVisible: Whether the "edit" link is currently visible.
 * Defaults to C{false}.
 * @type editLinkVisible: C{Boolean}
 *
 * @ivar deleteLinkVisible: Whether the "delete" link is currently visible.
 * Defaults to C{false}.
 * @type deleteLinkVisible: C{Boolean}
 *
 * @ivar cancelFormLinkVisible: Whether the "cancel form" link is currently
 * visible.  Defaults to C{false}.
 * @type cancelFormLinkVisible: C{Boolean}
 *
 * @ivar organizerPositionSet: Whether the I{organizer} node has been
 * positioned.  Defaults to C{false}.
 * @type organizerPositionSet: C{Boolean}
 *
 * @ivar selectedFilterNode: The currently selected tag node.  Defaults to
 * L{defaultTagNode}.
 * @type selectedFilterNode: DOM node.
 *
 * @ivar filterThrobberVisible: Whether the filter throbber node is visible.
 * Defaults to C{false}.
 * @type filterThrobberVisible: C{Boolean}
 *
 * @ivar unscrolledPersonCell: Whether L{unscrollPersonCell} has been called.
 * Defaults to C{false}.
 * @type unscrolledPersonCell: C{Boolean}
 *
 * @ivar personWidgetThrobberVisible: Whether the person widget throbber is
 * currently visible.  Defaults to C{false}
 * @type personWidgetThrobberVisible: C{Boolean}
 */
Mantissa.Test.TestPeople.StubOrganizerView.methods(
    function __init__(self) {
        self.detailNode = null;
        self.editLinkVisible = false;
        self.deleteLinkVisible = false;
        self.cancelFormLinkVisible = false;
        self.organizerPositionSet = false;
        self.defaultTagNode = document.createElement('a');
        self.defaultTagNode.setAttribute(
            'class', 'people-table-selected-tag');
        self.selectedFilterNode = self.defaultTagNode;
        self.filterThrobberVisible = false;
        self.unscrolledPersonCell = false;
        self.personWidgetThrobberVisible = false;
    },

    /**
     * Set L{organizerPositionSet} to C{true}.
     */
    function setOrganizerPosition(self) {
        self.organizerPositionSet = true;
    },

    /**
     * Set L{personWidgetThrobberVisible} to C{true}.
     */
    function showPersonWidgetThrobber(self) {
        self.personWidgetThrobberVisible = true;
    },

    /**
     * Set L{personWidgetThrobberVisible} to C{false}.
     */
    function hidePersonWidgetThrobber(self) {
        self.personWidgetThrobberVisible = false;
    },

    /**
     * Set L{filterThrobberVisible} to C{true}.
     */
    function showFilterThrobber(self) {
        self.filterThrobberVisible = true;
    },

    /**
     * Set L{filterThrobberVisible} to C{false}.
     */
    function hideFilterThrobber(self) {
        self.filterThrobberVisible = false;
    },

    /**
     * Set L{selectedFilterNode} to C{filterNode}.
     */
    function filterSelected(self, filterNode) {
        self.selectedFilterNode = filterNode;
    },

    /**
     * Set L{detailNode} to C{node}.
     */
    function setDetailNode(self, node) {
        self.detailNode = node;
    },

    /**
     * Set L{detailNode} to C{null}.
     */
    function clearDetailNodes(self) {
        self.detailNode = null;
    },

    /**
     * Set L{unscrolledPersonCell} to C{true}.
     */
    function unscrollPersonCell(self) {
        self.unscrolledPersonCell = true;
    },

    /**
     * Set L{deleteLinkVisible} to C{true}.
     */
    function showDeleteLink(self) {
        self.deleteLinkVisible = true;
    },

    /**
     * Set L{deleteLinkVisible} to C{false}.
     */
    function hideDeleteLink(self) {
        self.deleteLinkVisible = false;
    },

    /**
     * Set L{editLinkVisible} to C{true}.
     */
    function showEditLink(self) {
        self.editLinkVisible = true;
    },

    /**
     * Set L{editLinkVisible} to C{false}.
     */
    function hideEditLink(self) {
        self.editLinkVisible = false;
    },

    /**
     * Set L{cancelFormLinkVisible} to C{true}.
     */
    function showCancelFormLink(self) {
        self.cancelFormLinkVisible = true;
    },

    /**
     * Set L{cancelFormLinkVisible} to C{false}.
     */
    function hideCancelFormLink(self) {
        self.cancelFormLinkVisible = false;
    });


Mantissa.Test.TestPeople.OrganizerViewTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.OrganizerViewTests');
/**
 * Tests for L{Mantissa.People.OrganizerView}.
 */
Mantissa.Test.TestPeople.OrganizerViewTests.methods(
    /**
     * Construct a L{Mantissa.People.OrganizerView}.
     */
    function setUp(self) {
        var defaultFilterNode = document.createElement('a');
        defaultFilterNode.setAttribute(
            'class', 'people-table-selected-filter');
        var filterThrobberNode = document.createElement('img');
        filterThrobberNode.style.display = 'none';
        var personWidgetThrobberNode = document.createElement('img');
        personWidgetThrobberNode.style.display = 'none';
        self.nodes = {
            'detail': document.createElement('span'),
            'edit-link': document.createElement('a'),
            'delete-link': document.createElement('a'),
            'cancel-form-link': document.createElement('a'),
            'default-filter': defaultFilterNode,
            'filter-throbber': filterThrobberNode,
            'person-cell': document.createElement('td'),
            'person-widget-throbber': personWidgetThrobberNode};
        self.view = Mantissa.People.OrganizerView(
            function nodeById(id) {
                return self.nodes[id];
            });
    },

    /**
     * L{Mantissa.People.OrganizerView.setOrganizerPosition} should set the
     * I{top} style property of the I{organizer} node to the Y-position of its
     * parent node.
     */
    function test_setOrganizerPosition(self) {
        var containerNode = document.createElement('div');
        var organizerNode = document.createElement('div');
        containerNode.appendChild(organizerNode);
        self.nodes['organizer'] = organizerNode;
        var yPosition = 203;
        var queriedNodes = [];
        var originalFindPosY = Divmod.Runtime.theRuntime.findPosY;
        try {
            Divmod.Runtime.theRuntime.findPosY = function findPosY(node) {
                queriedNodes.push(node);
                return yPosition;
            }
            self.view.setOrganizerPosition();
        } finally {
            Divmod.Runtime.theRuntime.findPosY = originalFindPosY;
        }
        self.assertIdentical(queriedNodes.length, 1);
        self.assertIdentical(queriedNodes[0], containerNode);
        self.assertIdentical(organizerNode.style.top, yPosition + 'px');
    },

    /**
     * L{Mantissa.People.OrganizerView.showPersonWidgetThrobber} should show
     * the node with the id I{person-widget-throbber}.
     */
    function test_showPersonWidgetThrobber(self) {
        self.view.showPersonWidgetThrobber();
        self.assertIdentical(
            self.nodes['person-widget-throbber'].style.display, '');
    },

    /**
     * L{Mantissa.People.OrganizerView.hidePersonWidgetThrobber} should hide
     * the node with the id I{person-widget-throbber}.
     */
    function test_hidePersonWidgetThrobber(self) {
        self.view.showPersonWidgetThrobber();
        self.view.hidePersonWidgetThrobber();
        self.assertIdentical(
            self.nodes['person-widget-throbber'].style.display, 'none');
    },

    /**
     * L{Mantissa.People.OrganizerView.showFilterThrobber} should show the
     * node with the id I{filter-throbber}.
     */
    function test_showFilterThrobber(self) {
        self.view.showFilterThrobber();
        self.assertIdentical(
            self.nodes['filter-throbber'].style.display, '');
    },

    /**
     * L{Mantissa.People.OrganizerView.hideFilterThrobber} should hide the
     * node with the id I{filter-throbber}.
     */
    function test_hideFilterThrobber(self ){
        self.view.showFilterThrobber();
        self.view.hideFilterThrobber();
        self.assertIdentical(
            self.nodes['filter-throbber'].style.display, 'none');
    },

    /**
     * L{Mantissa.People.OrganizerView.filterSelected} should apply the
     * I{people-table-selected-filter} class to the given node.
     */
    function test_tagSelected(self) {
        var node = document.createElement('a');
        self.view.filterSelected(node);
        self.assertIdentical(
            node.getAttribute('class'), 'people-table-selected-filter');
        self.assertIdentical(
            self.nodes['default-filter'].getAttribute('class'),
            'people-table-filter');
    },

    /**
     * L{Mantissa.People.OrganizerView.unscrollPersonCell} should reset the
     * node's C{scrollTop} property.
     */
    function test_unscrollPersonCell(self) {
        self.nodes['person-cell'].scrollTop = 99;
        self.view.unscrollPersonCell();
        self.assertIdentical(
            self.nodes['person-cell'].scrollTop, 0);
    },

    /**
     * L{Mantissa.People.OrganizerView.setDetailNode} should clear any current
     * detail nodes and append the given node.
     */
    function test_setDetailNode(self) {
        self.nodes['detail'].appendChild(
            document.createElement('span'));
        var detailNode = document.createElement('img');
        self.view.setDetailNode(detailNode);
        self.assertIdentical(
            self.nodes['detail'].childNodes.length, 1);
        self.assertIdentical(
            self.nodes['detail'].childNodes[0], detailNode);
    },

    /**
     * L{Mantissa.People.OrganizerView.clearDetailNodes} should clear any
     * current detail nodes.
     */
    function test_clearDetailNodes(self) {
        self.nodes['detail'].appendChild(
            document.createElement('img'));
        self.nodes['detail'].appendChild(
            document.createElement('span'));
        self.view.clearDetailNodes();
        self.assertIdentical(self.nodes['detail'].childNodes.length, 0);
    },

    /**
     * L{Mantissa.People.OrganizerView.hideEditLink} should hide the edit
     * link.
     */
    function test_hideEditLink(self) {
        self.view.hideEditLink();
        self.assertIdentical(
            self.nodes['edit-link'].style.display, 'none');
    },

    /**
     * L{Mantissa.People.OrganizerView.hideDeleteLink} should hide the delete
     * link.
     */
    function test_hideDeleteLink(self) {
        self.view.hideDeleteLink();
        self.assertIdentical(
            self.nodes['delete-link'].style.display, 'none');
    },

    /**
     * L{Mantissa.People.OrganizerView.showEditLink} should show the edit
     * link.
     */
    function test_showEditLink(self) {
        self.view.hideEditLink();
        self.view.showEditLink();
        self.assertIdentical(
            self.nodes['edit-link'].style.display, '');
    },

    /**
     * L{Mantissa.People.OrganizerView.showDeleteLink} should show the delete
     * link.
     */
    function test_showDeleteLink(self) {
        self.view.hideDeleteLink();
        self.view.showDeleteLink();
        self.assertIdentical(
            self.nodes['delete-link'].style.display, '');
    },

    /**
     * L{Mantissa.People.OrganizerView.hideCancelFormLink} should hide the
     * cancel form link.
     */
    function test_hideCancelFormLink(self) {
        self.view.hideCancelFormLink();
        self.assertIdentical(
            self.nodes['cancel-form-link'].style.display, 'none');
    },

    /**
     * L{Mantissa.People.OrganizerView.showCancelFormLink} should show the
     * cancel form link.
     */
    function test_showCancelFormLink(self) {
        self.view.hideCancelFormLink();
        self.view.showCancelFormLink();
        self.assertIdentical(
            self.nodes['cancel-form-link'].style.display, '');
    });


Mantissa.Test.TestPeople.TestableOrganizer = Mantissa.People.Organizer.subclass(
    'Mantissa.Test.TestPeople.TestableOrganizer');
/**
 * Trivial L{Mantissa.People.Organizer} subclass which uses
 * L{Mantissa.Test.TestPeople.StubOrganizerView}.
 */
Mantissa.Test.TestPeople.TestableOrganizer.methods(
    /**
     * Override the base implementation to return a
     * L{Mantissa.Test.TestPeople.StubOrganizerView}.
     */
    function _makeView(self) {
        return Mantissa.Test.TestPeople.StubOrganizerView();
    });


Mantissa.Test.TestPeople.OrganizerTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.OrganizerTests');
/**
 * Tests for L{Mantissa.People.Organizer}.
 */
Mantissa.Test.TestPeople.OrganizerTests.methods(
    /**
     * Create an Organizer for use by test methods.
     */
    function setUp(self) {
        self.node = Nevow.Test.WidgetUtil.makeWidgetNode();
        self.organizer = Mantissa.Test.TestPeople.TestableOrganizer(self.node);
        self.view = self.organizer.view;

        self.calls = [];
        self.organizer.callRemote = function(name) {
            var args = [];
            for (var i = 1; i < arguments.length; ++i) {
                args.push(arguments[i]);
            }
            var result = Divmod.Defer.Deferred();
            self.calls.push({name: name, args: args, result: result});
            return result;
        };
    },

    function _assertCalled(self, name, args) {
        self.assertIdentical(self.calls.length, 1);
        var call = self.calls[0];
        self.assertIdentical(call.name, name);
        self.assertArraysEqual(call.args, args);
    },

    /**
     * L{Mantissa.People.Organizer.dom_filterByFilter} should call
     * C{filterByFilter} with the right filter.
     */
    function test_dom_filterByFilter(self) {
        var filter = 'this is a fantastic filter';
        var filters = [];
        self.organizer.filterByFilter = function(filter) {
            filters.push(filter);
        }
        var eventNode = document.createElement('a');
        eventNode.appendChild(document.createTextNode(filter));
        self.assertIdentical(
            self.organizer.dom_filterByFilter(eventNode),
            false);
        self.assertArraysEqual(filters, [filter]);
        self.assertIdentical(
            self.view.selectedFilterNode, eventNode);
    },

    /**
     * L{Mantissa.People.Organizer.dom_filterByFilter} shouldn't do anything
     * if it's passed the currently selected filter node.
     */
    function test_dom_filterByFilterTwice(self) {
        var filtered = false;
        self.organizer.filterByFilter = function filterByFilter() {
            filtered = true;
        }
        var filterNode = document.createElement('a');
        self.view.selectedFilterNode = filterNode;
        self.assertIdentical(
            self.organizer.dom_filterByFilter(filterNode), false);
        self.assertIdentical(filtered, false);
    },

    /**
     * L{Mantissa.People.Organizer.filterByFilter} should call
     * C{filterByFilter} on the person scroller and reset the view state when
     * the call completes.
     */
    function test_filterByFilter(self) {
        var filter = 'this is a good filter';
        var filters = [];
        var deferred = Divmod.Defer.succeed(null);
        var personScroller = {
            filterByFilter: function filterByFilter(filter) {
                filters.push(filter);
                return deferred;
            }
        }
        self.organizer.getPersonScroller = function() {
            return personScroller;
        }
        self.assertIdentical(
            self.organizer.filterByFilter(filter),
            deferred);
        self.assertArraysEqual(filters, [filter]);
        self.assertIdentical(self.view.detailNode, null);
        self.assertIdentical(self.view.editLinkVisible, false);
        self.assertIdentical(self.view.deleteLinkVisible, false);
    },

    /**
     * L{Mantissa.People.Organizer.personScrollerInitialized} should call
     * L{Mantissa.People.Organizer.selectInPersonList} with the name of the
     * initial person, if one is set.
     */
    function test_personScrollerInitialized(self) {
        var initialPersonName = 'Alice';
        self.organizer.initialPersonName = initialPersonName;
        var selectedInPersonList = [];
        self.organizer.selectInPersonList = function(personName) {
            selectedInPersonList.push(personName);
        }
        self.organizer.personScrollerInitialized();
        self.assertIdentical(selectedInPersonList.length, 1);
        self.assertIdentical(
            selectedInPersonList[0], initialPersonName);
    },

    /**
     * L{Mantissa.People.Organizer}'s constructor should call
     * C{setOrganizerPosition} on its view.
     */
    function test_constructorSetsPosition(self) {
        self.assertIdentical(self.view.organizerPositionSet, true);
    },

    /**
     * L{Mantissa.People.Organizer}'s constructor should call
     * L{Mantissa.People.Organizer.displayEditPerson} if the C{initialState}
     * is I{edit}.
     */
    function test_initialStateObserved(self) {
        var displayEditPersonCalls = 0;
        /* subclass because the method we want to mock is called by the
         * constructor */
        var MockEditPersonOrganizer = Mantissa.Test.TestPeople.TestableOrganizer.subclass(
            'MockEditPersonOrganizer');
        MockEditPersonOrganizer.methods(
            function displayEditPerson(self) {
                displayEditPersonCalls++;
            });
        var initialPersonName = 'Initial Person';
        organizer = MockEditPersonOrganizer(
            Nevow.Test.WidgetUtil.makeWidgetNode(),
            '', initialPersonName, 'edit');
        self.assertIdentical(displayEditPersonCalls, 1);
        self.assertIdentical(
            organizer.initialPersonName, initialPersonName);
        self.assertIdentical(
            organizer.currentlyViewingName, initialPersonName);
    },

    /**
     * L{Mantissa.People.Organizer.setDetailWidget} should remove the children
     * of the detail node and add the node for the L{Nevow.Athena.Widget} it is
     * passed as a child of it.
     */
    function test_setDetailWidget(self) {
        var widget = {};
        widget.node = document.createElement('table');
        self.organizer.setDetailWidget(widget);
        self.assertIdentical(self.view.detailNode, widget.node);
    },

    /**
     * L{Mantissa.People.Organizer.setDetailWidget} should destroy the previous
     * detail widget.
     */
    function test_oldDetailWidgetDiscarded(self) {
        var firstWidget = Mantissa.Test.TestPeople.StubWidget();
        var secondWidget = Mantissa.Test.TestPeople.StubWidget();
        self.organizer.setDetailWidget(firstWidget);
        self.organizer.setDetailWidget(secondWidget);
        self.assertIdentical(firstWidget.wasDetached, true);
        self.assertIdentical(secondWidget.wasDetached, false);
    },

    /**
     * L{Mantissa.People.Organizer.clearDetailWidget} should remove the detail
     * widget and its view.
     */
    function test_clearDetailWidget(self) {
        var widget = Mantissa.Test.TestPeople.StubWidget();
        self.organizer.existingDetailWidget = widget;
        self.view.detailNode = widget.node;

        self.organizer.clearDetailWidget();
        self.assertIdentical(self.view.detailNode, null);
        self.assertIdentical(self.organizer.existingDetailWidget, null);
        self.assertIdentical(widget.wasDetached, true);
        // It should be idempotent.
        self.organizer.clearDetailWidget();
    },

    /**
     * L{Mantissa.People.Organizer.deletePerson} should call the remote
     * I{deletePerson} method.
     */
    function test_deletePerson(self) {
        var personName = 'A Person Name';
        self.organizer.currentlyViewingName = personName;
        self.organizer.deletePerson().callback(null);
        self._assertCalled('deletePerson', [personName]);

        self.assertIdentical(self.view.detailNode, null);
        self.assertIdentical(self.view.editLinkVisible, false);
        self.assertIdentical(self.view.deleteLinkVisible, false);
    },

    /**
     * L{Mantissa.People.Organizer.dom_deletePerson} should call
     * L{Mantissa.People.Organizer.deletePerson}.
     */
    function test_domDeletePerson(self) {
        var calls = 0;
        self.organizer.deletePerson = function() {
            calls++;
        }
        self.assertIdentical(self.organizer.dom_deletePerson(), false);
        self.assertIdentical(calls, 1);
    },

    /**
     * L{Mantissa.People.Organizer.cancelForm} should load the last-viewed
     * person and hide the form.
     */
    function test_cancelForm(self) {
        var formNode = document.createElement('form');
        self.view.detailNode = formNode;
        var personName = 'Person Name';
        self.organizer.currentlyViewingName = personName;
        var displayedPerson;
        self.organizer.displayPersonInfo = function(name) {
            displayedPerson = name;
        }
        self.organizer.cancelForm();
        self.assertIdentical(self.view.detailNode, null);
        self.assertIdentical(displayedPerson, personName);
        self.assertIdentical(self.view.cancelFormLinkVisible, false);
    },

    /**
     * L{Mantissa.People.Organizer.dom_cancelForm} should call
     * L{Mantissa.People.Organizer.cancelForm}.
     */
    function test_domCancelForm(self) {
        var calls = 0;
        self.organizer.cancelForm = function() {
            calls++;
        }
        self.assertIdentical(self.organizer.dom_cancelForm(), false);
        self.assertIdentical(calls, 1);
    },

    /**
     * The given deferred should set the widget it is called with as the
     * display widget, and show the "cancel form" button.
     *
     * @return: the set widget
     */
    function _assertSetsDetailWidget(self, deferred) {
        self.assertIdentical(self.view.editLinkVisible, false);
        self.assertIdentical(self.view.deleteLinkVisible, false);
        self.assertIdentical(self.view.cancelFormLinkVisible, false);

        self.organizer.addChildWidgetFromWidgetInfo = function(widgetInfo) {
            return widgetInfo;
        };
        var detailWidget = null;
        self.organizer.setDetailWidget = function(widget) {
            detailWidget = widget;
        };
        var resultingWidget = Mantissa.Test.TestPeople.StubPersonForm();
        deferred.callback(resultingWidget);
        self.assertIdentical(resultingWidget, detailWidget);
        self.assertIdentical(self.view.editLinkVisible, false);
        self.assertIdentical(self.view.deleteLinkVisible, false);
        self.assertIdentical(self.view.cancelFormLinkVisible, true);
        return detailWidget;
    },

    /**
     * L{Mantissa.People.Organizer.displayAddPerson} should call
     * I{getAddPerson} on the server and set the resulting widget as the detail
     * widget.
     */
    function test_getAddPerson(self) {
        var result = self.organizer.displayAddPerson();
        self._assertCalled('getAddPerson', []);
        self._assertSetsDetailWidget(self.calls[0].result);
    },

    /**
     * Similar to L{test_getAddPerson}, but for
     * L{Mantissa.People.Organizer.displayImportPeople}.
     */
    function test_getImportPeople(self) {
        var result = self.organizer.displayImportPeople();
        self._assertCalled('getImportPeople', []);
        var widget = self._assertSetsDetailWidget(self.calls[0].result);
        self.assertIdentical(widget.organizer, self.organizer)
    },

    /**
     * Similar to L{test_getAddPerson}, but for
     * L{Mantissa.People.Organizer.displayEditPerson}.
     */
    function test_getEditPerson(self) {
        var name = "A Person's name";
        self.organizer.currentlyViewingName = name;
        var result = self.organizer.displayEditPerson();
        self._assertCalled('getEditPerson', [name]);
        self._assertSetsDetailWidget(self.calls[0].result);
    },

    /**
     * L{Mantissa.People.Organizer.dom_displayEditPerson} should call
     * L{Mantissa.People.Organizer.displayEditPerson}.
     */
    function test_domDisplayEditPerson(self) {
        var calls = 0;
        self.organizer.displayEditPerson = function() {
            calls++;
        }
        self.assertIdentical(self.organizer.dom_displayEditPerson(), false);
        self.assertIdentical(calls, 1);
    },

    /**
     * L{Mantissa.People.Organizer.getPersonScroller} should return the first
     * child widget.
     */
    function test_getPersonScroller(self) {
        var personScroller = {};
        self.organizer.childWidgets = [personScroller];
        self.assertIdentical(
            self.organizer.getPersonScroller(), personScroller);
    },

    /**
     * L{Mantissa.People.Organizer.refreshPersonList} should call
     * C{emptyAndRefill} on the child scrolltable.
     */
    function test_refreshPersonList(self) {
        var calls = 0;
        self.organizer.childWidgets = [
            {emptyAndRefill: function() {
                calls++;
            }}];
        self.organizer.refreshPersonList();
        self.assertIdentical(calls, 1);
    },

    /**
     * L{Mantissa.People.Organizer.selectInPersonList} should call
     * C{selectNamedPerson} on the child scrolltable.
     */
    function test_selectInPersonList(self) {
        var names = [];
        self.organizer.childWidgets = [
            {selectNamedPerson: function(name) {
                names.push(name);
            }}];
        var personName = 'A person name';
        self.organizer.selectInPersonList(personName);
        self.assertIdentical(names.length, 1);
        self.assertIdentical(names[0], personName);
    },

    /**
     * L{Organizer} should add an observer to L{AddPersonForm} which calls
     * L{Organizer.displayPersonInfo} with the nickname it is passed.
     */
    function test_personCreationObservation(self) {
        var displayDeferred = self.organizer.displayAddPerson();
        var nickname = 'test nick';
        self.organizer.addChildWidgetFromWidgetInfo = function(widgetInfo) {
            return widgetInfo;
        };
        var refreshed = false;
        self.organizer.refreshPersonList = function() {
            refreshed = true;
            return Divmod.Defer.succeed(undefined);
        }
        var form = Mantissa.Test.TestPeople.StubPersonForm();
        self.calls[0].result.callback(form);
        form.submissionObservers[0](nickname);
        self.assertIdentical(refreshed, true);
        self.assertIdentical(
            self.organizer.currentlyViewingName, nickname);
    },

    /**
     * Similar to L{test_personCreationObservation}, but for
     * L{Mantissa.People.Organizer.displayEditPerson} and person edit
     * notification.
     */
    function test_personEditObservation(self) {
        var displayDeferred = self.organizer.displayEditPerson();
        var nickname = 'test nick';
        self.organizer.addChildWidgetFromWidgetInfo = function(widgetInfo) {
            return widgetInfo;
        };
        var displaying;
        self.organizer.displayPersonInfo = function(nickname) {
            displaying = nickname;
        };
        var refreshed = false;
        self.organizer.refreshPersonList = function() {
            refreshed = true;
            return Divmod.Defer.succeed(undefined);
        }
        var form = Mantissa.Test.TestPeople.StubPersonForm();
        self.calls[0].result.callback(form);
        form.submissionObservers[0](nickname);
        self.assertIdentical(displaying, nickname);
        self.assertIdentical(refreshed, true);
    },

    /**
     * The person-edit observer set by
     * L{Mantissa.People.Organizer.displayEditPerson} should call
     * L{Mantissa.People.Organizer.storeOwnerPersonNameChanged} if the store
     * owner person was edited.
     */
    function test_personEditObservationStoreOwner(self) {
        var name = 'Store Owner!';
        self.organizer.currentlyViewingName = name;
        self.organizer.storeOwnerPersonName = name;
        self.organizer.addChildWidgetFromWidgetInfo = function(widgetInfo) {
            return widgetInfo;
        }
        self.organizer.displayEditPerson();
        var stubPerformForm = Mantissa.Test.TestPeople.StubPersonForm();
        self.calls[0].result.callback(stubPerformForm);
        var nameChanges = [];
        self.organizer.storeOwnerPersonNameChanged = function(name) {
            nameChanges.push(name);
        }
        self.organizer._cbPersonModified = function() {
        }
        var newName = 'Store Owner 2!';
        stubPerformForm.submissionObservers[0](newName);
        self.assertIdentical(nameChanges.length, 1);
        self.assertIdentical(nameChanges[0], newName);
    },

    /**
     * L{Mantissa.People.Organizer.storeOwnerPersonNameChanged} should call
     * the method with the same name on the child person scroller.
     */
    function test_storeOwnerPersonNameChanged(self) {
        var nameChanges = [];
        self.organizer.childWidgets = [
            {storeOwnerPersonNameChanged: function(newName) {
                nameChanges.push(newName);
            }}];
        var newName = 'Store Owner!';
        self.organizer.storeOwnerPersonNameChanged(newName);
        self.assertIdentical(nameChanges.length, 1);
        self.assertIdentical(nameChanges[0], newName);
    },

    /**
     * L{Mantissa.People.Organizer.displayPersonInfo} should call
     * I{getPersonPluginWidget} with the nickname it is passed and put the
     * resulting widget in the detail area.
     */
    function test_displayPersonInfo(self) {
        var nickname = 'testuser';
        var result = self.organizer.displayPersonInfo(nickname);

        self._assertCalled('getPersonPluginWidget', [nickname]);
        self.assertIdentical(
            self.view.personWidgetThrobberVisible, true);

        var resultingWidgetInfo = {};
        var widgetInfos = [];
        var returnedNode = document.createElement('span');
        self.organizer.addChildWidgetFromWidgetInfo = function(widgetInfo) {
            widgetInfos.push(widgetInfo);
            return {node: returnedNode};
        }
        self.calls[0].result.callback(resultingWidgetInfo);
        self.assertIdentical(
            self.view.personWidgetThrobberVisible, false);
        self.assertIdentical(self.view.detailNode, returnedNode);
        self.assertIdentical(self.view.unscrolledPersonCell, true);
        self.assertIdentical(widgetInfos.length, 1);
        self.assertIdentical(widgetInfos[0], resultingWidgetInfo);
    });


Mantissa.Test.TestPeople.EditPersonFormTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.EditPersonFormTests');
/**
 * Tests for L{Mantissa.People.EditPersonForm}.
 */
Mantissa.Test.TestPeople.EditPersonFormTests.methods(
    /**
     * L{Mantissa.People.EditPersonForm.reset} shouldn't reset the values of
     * the form.
     */
    function test_reset(self) {
        var identifier = 'athena:123';
        var node = document.createElement('form');
        var wasReset = false;
        node.reset = function reset() {
            wasReset = true;
        };
        node.id = identifier;
        var form = Mantissa.People.EditPersonForm(node, 'name');
        form.reset();
        self.assertIdentical(wasReset, false);
    });


Mantissa.Test.TestPeople.SubmitNotificationFormTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.SubmitNotificationFormTests');
/**
 * Tests for L{Mantissa.Peoople._SubmitNotificationForm}.
 */
Mantissa.Test.TestPeople.SubmitNotificationFormTests.methods(
    /**
     * After successful submission, the form widget should notify all
     * registered observers of the nickname of the person which was just
     * modified.
     */
    function test_observeSubmission(self) {
        var createdPeople = [];
        function personCreationObserver(nickname) {
            createdPeople.push(nickname);
        };
        var nickname = 'test nick';
        var node = document.createElement('form');
        node.id = 'athena:123';
        var input = document.createElement('input');
        input.name = 'nickname';
        input.value = nickname;
        input.type = 'text';
        node.appendChild(input);
        var form = Mantissa.People._SubmitNotificationForm(node, 'name');
        form.observeSubmission(personCreationObserver);
        form.submitSuccess(null);
        self.assertIdentical(createdPeople.length, 1);
        self.assertIdentical(createdPeople[0], nickname);
    });


Mantissa.Test.TestPeople.AddPersonTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.AddPersonTests');
/**
 * Tests for L{Mantissa.People.AddPerson}.
 */
Mantissa.Test.TestPeople.AddPersonTests.methods(
    /**
     * L{Mantissa.People.AddPerson.observeSubmission} should pass the observer
     * it is called with to the C{observeSubmission} method of the
     * L{AddPersonForm} instance it contains.
     */
    function test_observePersonCreation(self) {
        var node = document.createElement('span');
        node.id = 'athena:123';
        var addPerson = Mantissa.People.AddPerson(node);
        var addPersonForm = Mantissa.Test.TestPeople.StubPersonForm();
        addPerson.addChildWidget(addPersonForm);
        var observer = {};
        addPerson.observeSubmission(observer);
        self.assertIdentical(addPersonForm.submissionObservers.length, 1);
        self.assertIdentical(addPersonForm.submissionObservers[0], observer);
    },

    /**
     * L{Mantissa.People.AddPerson.loaded} should schedule a call to
     * L{Mantissa.People.AddPerson.focusNicknameInput}.
     */
    function test_loadedSchedulesFocus(self) {
        var widget = Mantissa.People.AddPerson(
            Nevow.Test.WidgetUtil.makeWidgetNode());
        var callLaters = [];
        widget.callLater = function(seconds, callable) {
            callLaters.push([callable, seconds]);
        }
        var focuses = 0;
        widget.focusNicknameInput = function() {
            focuses++;
        }
        widget.loaded();
        self.assertIdentical(callLaters.length, 1);
        self.assertIdentical(callLaters[0][1], 0);
        self.assertIdentical(focuses, 0);
        callLaters[0][0]();
        self.assertIdentical(focuses, 1);
    },

    /**
     * L{Mantissa.People.AddPerson.focusNicknameInput} should focus the node
     * with the name I{nickname}.
     */
    function test_focusNicknameInput(self) {
        var node = Nevow.Test.WidgetUtil.makeWidgetNode();
        var input = document.createElement('input');
        input.setAttribute('type', 'text');
        input.setAttribute('name', 'nickname');
        var focuses = 0;
        input.focus = function() {
            focuses++;
        }
        node.appendChild(input);
        var widget = Mantissa.People.AddPerson(node);
        self.assertIdentical(focuses, 0);
        widget.focusNicknameInput();
        self.assertIdentical(focuses, 1);
    });


Mantissa.Test.TestPeople.EditPersonTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.EditPersonTests');
/**
 * Tests for L{Mantissa.People.EditPerson}.
 */
Mantissa.Test.TestPeople.EditPersonTests.methods(
    /**
     * L{Mantissa.People.EditPerson.observeSubmission} should pass the
     * observer it is called with to the C{observeSubmission} method of the
     * L{Mantissa.People.EditPersonForm} instance it contains.
     */
    function test_observePersonEdits(self) {
        var editPerson = Mantissa.People.EditPerson(
            Nevow.Test.WidgetUtil.makeWidgetNode());
        var editPersonForm = Mantissa.Test.TestPeople.StubPersonForm();
        editPerson.addChildWidget(editPersonForm);
        var observer = {};
        editPerson.observeSubmission(observer);
        self.assertIdentical(editPersonForm.submissionObservers.length, 1);
        self.assertIdentical(editPersonForm.submissionObservers[0], observer);
    });


Mantissa.Test.TestPeople.ImportPeopleWidgetTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.ImportPeopleWidgetTests');
/**
 * Tests for L{Mantissa.People.ImportPeopleWidget} and
 * L{Mantissa.People.ImportPeopleForm}.
 */
Mantissa.Test.TestPeople.ImportPeopleWidgetTests.methods(

    /**
     * Set up an import widget and associated organizer.
     */
    function setUp(self) {
        var _node = Nevow.Test.WidgetUtil.makeWidgetNode;
        self.organizer = Mantissa.Test.TestPeople.TestableOrganizer(_node());
        self.importWidget = Mantissa.People.ImportPeopleWidget(_node());
        self.resultNode = document.createElement('div');
        self.resultNode.setAttribute('class', 'import-result');
        self.importWidget.node.appendChild(self.resultNode);
        self.importForm = Mantissa.People.ImportPeopleForm(_node());
        self.importWidget.addChildWidget(self.importForm);
        self.importWidget.organizer = self.organizer;
    },

    /**
     * L{Mantissa.People.ImportPeopleForm.submitSuccess} should call
     * L{Mantissa.People.ImportPeopleWidget.imported} with the submission
     * result.
     */
    function test_submitSuccess(self) {
        var names;
        self.importWidget.imported = function (_names) {
            names = _names;
        };
        self.importForm.submitSuccess([]);
        self.assertArraysEqual(names, []);
        self.importForm.submitSuccess(['alice']);
        self.assertArraysEqual(names, ['alice']);
    },

    /**
     * L{Mantissa.People.ImportPeopleWidget.imported} should display an
     * appropriate result message, and refresh the organizer if any people have
     * been added.
     */
    function test_imported(self) {
        var refreshed = 0;
        self.organizer.refreshPersonList = function () {
            refreshed += 1;
            return Divmod.Defer.succeed();
        };
        var resultMessage;
        self.importWidget.resultMessage = function (message) {
            resultMessage = message;
        }

        self.importWidget.imported([]);
        self.assertIdentical(refreshed, 0)
        self.assertIdentical(resultMessage, 'No people imported.')

        self.importWidget.imported(['alice']);
        self.assertIdentical(refreshed, 1)
        self.assertIdentical(resultMessage, '1 person imported: alice')

        self.importWidget.imported(['alice', 'bob']);
        self.assertIdentical(refreshed, 2)
        self.assertIdentical(resultMessage, '2 people imported: alice, bob')

        // The widget should also work without an organizer.
        delete self.importWidget.organizer;
        self.importWidget.imported(['carol']);
        self.assertIdentical(refreshed, 2)
        self.assertIdentical(resultMessage, '1 person imported: carol')
    },

    /**
     * L{Mantissa.People.ImportPeopleWidget.resultMessage} should display the
     * given message.
     */
    function test_resultMessage(self) {
        function test(text) {
            self.importWidget.resultMessage(text);
            self.assertIdentical(self.resultNode.childNodes.length, 1);
            self.assertIdentical(self.resultNode.childNodes[0].nodeValue, text);
        }
        test('foo');
        test('bar');
    });


Mantissa.Test.TestPeople.PersonScrollerTestCase = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.PersonScrollerTestCase');
/**
 * Tests for L{Mantissa.People.PersonScroller}.
 */
Mantissa.Test.TestPeople.PersonScrollerTestCase.methods(
    /**
     * Construct a L{Mantissa.People.PersonScroller}.
     */
    function setUp(self) {
        self.scroller = Mantissa.People.PersonScroller(
            Nevow.Test.WidgetUtil.makeWidgetNode(), null, []);
    },

    /**
     * L{Mantissa.People.PersonScroller.loaded} should call
     * C{personScrollerInitialized} on the widget parent after the deferred
     * returned from the base implementation fires.
     */
    function test_loaded(self) {
        var initialized = false;
        self.scroller.widgetParent = {
            personScrollerInitialized: function() {
                initialized = true;
            }
        };
        var deferred = Divmod.Defer.Deferred();
        self.scroller.callRemote = function() {
            return deferred;
        }
        self.scroller.loaded();
        self.assertIdentical(initialized, false);
        deferred.callback([]);
        self.assertIdentical(initialized, true);
    },

    /**
     * L{Mantissa.People.PersonScroller.filterByFilter} should call the remote
     * I{filterByFilter} method and C{emptyAndRefill}.
     */
    function test_filterByFilter(self) {
        var remoteCalls = [];
        self.scroller.callRemote = function() {
            remoteCalls.push(arguments);
            return Divmod.Defer.succeed(null);
        }
        var refilled = 0;
        self.scroller.emptyAndRefill = function() {
            refilled++;
        }
        var filter = 'this is a filter';
        self.scroller.filterByFilter(filter);
        self.assertIdentical(remoteCalls.length, 1);
        self.assertIdentical(remoteCalls[0][0], 'filterByFilter');
        self.assertIdentical(remoteCalls[0][1], filter);
        self.assertIdentical(refilled, 1);
    },

    /**
     * L{Mantissa.People.PersonScroller.dom_cellClicked} should call the
     * C{displayPersonInfo} method on the parent widget.
     */
    function test_domCellClicked(self) {
        var displayingPerson;
        self.scroller.widgetParent = {
            displayPersonInfo: function(name) {
                displayingPerson = name;
            }}
        var personName = 'A person name';
        var rowNode = document.createElement('div');
        rowNode.appendChild(document.createTextNode(personName));
        self.assertIdentical(self.scroller.dom_cellClicked(rowNode), false);
        self.assertIdentical(displayingPerson, personName);
    },

    /**
     * L{Mantissa.People.PersonScroller.dom_cellClicked} should make the row
     * appear selected.
     */
    function test_domCellClickedSelection(self) {
        self.scroller.widgetParent = {
            displayPersonInfo: function(name) {
        }};
        var rowNode = document.createElement('div');
        self.scroller.dom_cellClicked(rowNode);
        self.assertIdentical(
            rowNode.getAttribute('class'),
            'person-list-selected-person-row');
    },

    /**
     * L{Mantissa.People.PersonScroller.dom_cellClicked} should unselect the
     * previously-selected row.
     */
    function test_domCellClickedDeselection(self) {
        self.scroller.widgetParent = {
            displayPersonInfo: function(name) {
        }};
        var rowNode = document.createElement('div');
        self.scroller.dom_cellClicked(rowNode);
        var secondRowNode = document.createElement('div');
        self.scroller.dom_cellClicked(secondRowNode);
        self.assertIdentical(
            rowNode.getAttribute('class'),
            'person-list-person-row');
        self.assertIdentical(
            secondRowNode.getAttribute('class'),
            'person-list-selected-person-row');
    },

    /**
     * L{Mantissa.People.PersonScroller.selectNamedPerson} should make the
     * given person's row appear selected.
     */
    function test_selectNamedPerson(self) {
        var personName = 'A person name';
        var firstJunkRowNode = self.scroller.makeRowElement(
            0, {name: 'Some other person name'}, []);
        var rowNode = self.scroller.makeRowElement(
            1, {name: personName}, []);
        var secondJunkRowNode = self.scroller.makeRowElement(
            2, {name: 'A third person name'}, []);
        self.scroller.selectNamedPerson(personName);
        self.assertIdentical(
            rowNode.getAttribute('class'),
            'person-list-selected-person-row');
        self.assertIdentical(
            firstJunkRowNode.getAttribute('class'),
            'person-list-person-row');
        self.assertIdentical(
            secondJunkRowNode.getAttribute('class'),
            'person-list-person-row');
    },

    /**
     * L{Mantissa.People.PersonScroller.makeRowElement} should make a
     * link-like node.
     */
    function test_makeRowElement(self) {
        var cellElement = document.createElement('span');
        var rowData = {name: 'A person name'};
        var rowElement = self.scroller.makeRowElement(
            0, rowData, [cellElement]);
        self.assertIdentical(rowElement.tagName, 'DIV');
        self.assertIdentical(rowElement.childNodes.length, 1);
        self.assertIdentical(rowElement.childNodes[0], cellElement);
        if(rowElement.onclick === undefined) {
            self.fail('row element has no onclick handler');
        }
    },

    /**
     * Make a row dict out of the given values.
     *
     * @param vip: C{vip} value.  Defaults to C{false}.
     * @type vip: C{Boolean}
     *
     * @param mugshotURL: C{mugshotURL} value.  Defaults to C{''}.
     * @type mugshotURL: C{String}
     *
     * @param name: C{name} value.  Defaults to C{''}.
     * @type name: C{String}
     *
     * @rtype: C{Object}
     */
    function _makeRowData(self, vip/*=false*/, mugshotURL/*=''*/, name/*=''*/) {
        if(vip === undefined) {
            vip = false;
        }
        if(mugshotURL === undefined) {
            mugshotURL = '';
        }
        if(name === undefined) {
            name = '';
        }
        return {vip: vip, mugshotURL: mugshotURL, name: name};
    },

    /**
     * L{Mantissa.People.PersonScroller.makeCellElement} shouldn't return a
     * node for the C{vip} column.
     */
    function test_makeCellElementVIP(self) {
        var cellElement = self.scroller.makeCellElement(
            'vip', self._makeRowData(true));
        self.assertIdentical(cellElement, undefined);
        cellElement = self.scroller.makeCellElement(
            'vip', self._makeRowData(false));
        self.assertIdentical(cellElement, undefined);
    },

    /**
     * L{Mantissa.People.PersonScroller.makeCellElement} shouldn't return a
     * node for the C{mugshotURL} column.
     */
    function test_makeCellElementMugshotURL(self) {
        var cellElement = self.scroller.makeCellElement(
            'mugshotURL', self._makeRowData(
                true, '/test_makeCellElementMugshotURL'));
        self.assertIdentical(cellElement, undefined);
    },

    /**
     * Verify the structure of the given person name node.
    */
    function _verifyNameNode(self, nameContainerNode, name, images) {
        self.assertIdentical(nameContainerNode.tagName, 'SPAN');
        self.assertIdentical(
            nameContainerNode.childNodes.length, images.length + 1);
        var nameNode = nameContainerNode.childNodes[0];
        self.assertIdentical(nameNode.nodeValue, name);
        var imageNode;
        for(var i = 0; i < images.length; i++) {
            imageNode = nameContainerNode.childNodes[i+1];
            self.assertIdentical(imageNode.tagName, 'IMG');
            self.assertIdentical(imageNode.getAttribute('src'), images[i]);
        }
    },

    /**
     * Add an entry for C{name} in L{scroller}'s C{columns} mapping.
     */
    function _mockScrollerColumn(self) {
        self.scroller.columns = {name: {
            extractValue: function(rowData) {
                return rowData.name;
            },
            valueToDOM: function(value) {
                return document.createTextNode(value);
            }}};
    },

    /**
     * L{Mantissa.people.PersonScroller.makeCellElement} should include a
     * C{<img>} tag pointing at the given C{mugshotURL} in the name cell.
     */
    function test_makeCellElementNameMugshot(self) {
        var mugshotURL = '/test_makeCellElementNameMugshot';
        self._mockScrollerColumn();
        var cellElement = self.scroller.makeCellElement(
            'name', self._makeRowData(false, mugshotURL));
        self.assertIdentical(cellElement.childNodes.length, 3);
        var mugshotNode = cellElement.childNodes[0];
        self.assertIdentical(mugshotNode.tagName, 'DIV');
        self.assertIdentical(
            mugshotNode.getAttribute('class'), 'people-table-mugshot');
        self.assertIdentical(
            mugshotNode.style.backgroundImage, 'url(' + mugshotURL + ')');
    },

    /**
     * L{Mantissa.People.PersonScroller.makeCellElement} should include the
     * person's name in the name cell.
     */
    function test_makeCellElementName(self) {
        var name = 'test_makeCellElementName';
        self._mockScrollerColumn();
        var cellElement = self.scroller.makeCellElement(
            'name', self._makeRowData(false, '', name));
        self.assertIdentical(cellElement.childNodes.length, 3);
        var nameContainerNode = cellElement.childNodes[1];
        self._verifyNameNode(nameContainerNode, name, []);
    },

    /**
     * L{Mantissa.People.PersonScroller.makeCellElement} should include a vip
     * flag image in the name cell DOM for vip people.
     */
    function test_makeCellElementNameVIP(self) {
        var name = 'test_makeCellElementName';
        self._mockScrollerColumn();
        var cellElement = self.scroller.makeCellElement(
            'name', self._makeRowData(true, '', name));
        self.assertIdentical(cellElement.childNodes.length, 3);
        var nameContainerNode = cellElement.childNodes[1];
        self._verifyNameNode(nameContainerNode, name,
            ['/static/mantissa-base/images/vip-flag.png']);
    },

    /**
     * L{Mantissa.People.PersonScroller.makeCellElement} should include an
     * image in the store owner person's name cell.
     */
    function test_makeCellElementNameStoreOwner(self) {
        var storeOwnerPersonName = 'Store Owner!';
        self.scroller.storeOwnerPersonName = storeOwnerPersonName;
        self._mockScrollerColumn();
        var cellElement = self.scroller.makeCellElement(
            'name', self._makeRowData(false, '', storeOwnerPersonName));
        self.assertIdentical(cellElement.childNodes.length, 3);
        var nameContainerNode = cellElement.childNodes[1];
        self._verifyNameNode(
            nameContainerNode, storeOwnerPersonName,
            ['/static/mantissa-base/images/me-icon.png']);
    });


Mantissa.Test.TestPeople.PersonPluginViewTestCase = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.PersonPluginViewTestCase');
/**
 * Tests for L{Mantissa.People.PersonPluginView}.
 */
Mantissa.Test.TestPeople.PersonPluginViewTestCase.methods(
    /**
     * L{Mantissa.People.PersonPluginView.getPluginWidget} should request the
     * correct widget and add its node to the dom.
     */
    function test_getPluginWidget(self) {
        var view = Mantissa.People.PersonPluginView(
            Nevow.Test.WidgetUtil.makeWidgetNode());
        var returnedWidgetInfo = {};
        var returnedWidget = {};
        var pluginName = 'the plugin!';
        view.callRemote = function() {
            self.assertIdentical(arguments.length, 2);
            self.assertIdentical(arguments[0], 'getPluginWidget');
            self.assertIdentical(arguments[1], pluginName);
            return Divmod.Defer.succeed(returnedWidgetInfo);
        }
        view.addChildWidgetFromWidgetInfo = function(widgetInfo) {
            self.assertIdentical(widgetInfo, returnedWidgetInfo);
            return returnedWidget;
        }
        var widget;
        view.getPluginWidget(pluginName).addCallback(
            function(theWidget) {
                widget = theWidget;
            });
        self.assertIdentical(widget, returnedWidget);
    });


Mantissa.Test.TestPeople.PluginTabbedPaneTestCase = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.PluginTabbedPaneTestCase');
/**
 * Tests for L{Mantissa.People.PluginTabbedPane}.
 */
Mantissa.Test.TestPeople.PluginTabbedPaneTestCase.methods(
    /**
     * L{Mantissa.People.PluginTabbedPane.namedTabSelected} should call
     * C{getPluginWidget} on its parent.
     */
    function test_namedTabSelected(self) {
        var pane = Mantissa.People.PluginTabbedPane(
            Nevow.Test.WidgetUtil.makeWidgetNode());
        var pluginWidget = {node: {}};
        var tabName = 'test_namedTabSelected';
        var getPluginWidgetCalls = 0;
        pane.widgetParent = {
            getPluginWidget: function(theTabName) {
                getPluginWidgetCalls++;
                self.assertIdentical(tabName, theTabName);
                return Divmod.Defer.succeed(pluginWidget);
            }
        }
        var replaceNamedPaneContentCalls = 0;
        pane.view.replaceNamedPaneContent = function(theTabName, node) {
            replaceNamedPaneContentCalls++;
            self.assertIdentical(node, pluginWidget.node);
            self.assertIdentical(theTabName, tabName);
        }
        pane.namedTabSelected(tabName);
        self.assertIdentical(getPluginWidgetCalls, 1);
        self.assertIdentical(replaceNamedPaneContentCalls, 1);
    },

    /**
     * L{Mantissa.People.PluginTabbedPane.namedTabSelected} shouldn't do
     * anything if the tab has already been selected.
     */
    function test_namedTabSelectedReselect(self) {
        var pane = Mantissa.People.PluginTabbedPane(
            Nevow.Test.WidgetUtil.makeWidgetNode());
        var getPluginWidgetCalls = 0;
        pane.widgetParent = {
            getPluginWidget: function() {
                getPluginWidgetCalls++;
                return Divmod.Defer.succeed({node: {}});
            }
        }
        pane.view.replaceNamedPaneContent = function() {}
        pane.namedTabSelected('test_namedTabSelectedReselect');
        self.assertIdentical(getPluginWidgetCalls, 1);
        pane.namedTabSelected('test_namedTabSelectedReselect');
        self.assertIdentical(getPluginWidgetCalls, 1);
    });

