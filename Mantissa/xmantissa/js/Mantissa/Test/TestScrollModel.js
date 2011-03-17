// -*- test-case-name: xmantissa.test.test_javascript -*-
// Copyright (c) 2007 Divmod.
// See LICENSE for details.

/**
 * Tests for L{Mantissa.ScrollTable.ScrollModel}
 */

// import Divmod.UnitTest
// import Mantissa.ScrollTable

Mantissa.Test.TestScrollModel.StubObserver = Divmod.Class.subclass(
    'Mantissa.Test.TestScrollModel.StubObserver');
/**
 * Dummy observer which records all events broadcast to it.  This record is
 * later inspected by test methods to verify the correct thing has happend.
 */
Mantissa.Test.TestScrollModel.StubObserver.methods(
    function __init__(self) {
        self.events = [];
    },

    function rowSelected(self, row) {
        self.events.push({'type': 'selected', 'row': row});
    },

    function rowUnselected(self, row) {
        self.events.push({'type': 'unselected', 'row': row});
    },

    function rowActivated(self, row) {
        self.events.push({'type': 'activated', 'row': row});
    },

    function rowDeactivated(self, row) {
        self.events.push({'type': 'deactivated', 'row': row});
    });


Mantissa.Test.TestScrollModel.StubBackend = Divmod.Class.subclass(
    'Mantissa.Test.TestScrollModel.StubBackend');
/**
 * Extremely simple, test-friendly row backend implementation.
 */
Mantissa.Test.TestScrollModel.StubBackend.methods(
    function __init__(self) {
        self.requests = [];
    },

    function requestRowRange(self, offset, count) {
        self.requests.push(Divmod.Defer.Deferred());
        return self.requests[self.requests.length - 1];
    });


Mantissa.Test.TestScrollModel.ScrollModelTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestScrollModel.ScrollModelTests');
/**
 * Tests for the underlying model object, L{Mantissa.ScrollTable.ScrollModel}.
 */
Mantissa.Test.TestScrollModel.ScrollModelTests.methods(
    function setUp(self) {
        self.backend = Mantissa.Test.TestScrollModel.StubBackend();
        self.model = Mantissa.ScrollTable.ScrollModel(self.backend);
        self.model.setRowData(0, {'__id__': 'a'});
    },

    /**
     * Return an array of all rows which L{ScrollModel.visitSelectedRows} hits.
     */
    function _getSelectedRows(self) {
        var rows = [];
        function visitor(row) {
            rows.push(row);
        };
        self.model.visitSelectedRows(visitor);
        return rows;
    },

    /**
     * Verify that visitSelectedRows does not invoke its visitor at all if
     * there are no rows at all in the model.
     */
    function test_visitEmptyModel(self) {
        self.model.empty();
        var rows = self._getSelectedRows();
        self.assertIdentical(rows.length, 0);
    },

    /**
     * Verify that visitSelectedRows calls its visitor with the active row if
     * there is one and no rows are selected.
     */
    function test_activeRowWithoutSelection(self) {
        self.model.setRowData(1, {'__id__': 'b'});
        self.model.activateRow('b');
        var rows = self._getSelectedRows();
        self.assertIdentical(rows.length, 1);
        self.assertIdentical(rows[0].__id__, 'b');
    },

    /**
     * Verify that visitSelectedRows does not call its visitor with the active
     * row if there is a selected row.
     */
    function test_activeRowWithSelection(self) {
        self.model.selectRow('a');
        self.model.setRowData(1, {'__id__': 'b'});
        self.model.activateRow('b');
        var rows = self._getSelectedRows();
        self.assertIdentical(rows.length, 1);
        self.assertIdentical(rows[0].__id__, 'a');
    },

    /**
     * Verify that when no rows in the model are selected, L{visitSelectedRows}
     * does not call the visitor at all.
     */
    function test_emptySelection(self) {
        var rows = self._getSelectedRows();
        self.assertIdentical(rows.length, 0);
    },

    /**
     * Verify that a row can be added to the row selection with the selectRow
     * method.
     */
    function test_selectRow(self) {
        self.model.selectRow('a');
        var rows = self._getSelectedRows();
        self.assertIdentical(rows.length, 1);
        self.assertIdentical(rows[0].__id__, 'a');
    },

    /**
     * Verify that a selected row can be removed from the row selection with
     * the unselectRow method.
     */
    function test_unselectRow(self) {
        self.model.selectRow('a');
        self.model.unselectRow('a');
        var rows = self._getSelectedRows();
        self.assertIdentical(rows.length, 0);
    },

    /**
     * Verify that isSelected returns true for selected rows and false for
     * unselected rows and never selected rows.
     */
    function test_isSelected(self) {
        self.assert(!self.model.isSelected('a'));
        self.model.selectRow('a');
        self.assert(self.model.isSelected('a'));
        self.model.unselectRow('a');
        self.assert(!self.model.isSelected('a'));
    },

    /**
     * Verify that adding a selection observer has no side-effects.
     */
    function test_addObserver(self) {
        var observer = Mantissa.Test.TestScrollModel.StubObserver();
        self.model.addObserver(observer);
        self.assertIdentical(observer.events.length, 0);
    },

    /**
     * Verify that selection observers are notified when a row is selected.
     */
    function test_selectionCallback(self) {
        var observer = Mantissa.Test.TestScrollModel.StubObserver();
        self.model.addObserver(observer);
        self.model.selectRow('a');
        self.assertIdentical(observer.events.length, 1);
        self.assertIdentical(observer.events[0].type, 'selected');
        self.assertIdentical(observer.events[0].row.__id__, 'a');
    },

    /**
     * Verify that selection observers are notified when a row is unselected.
     */
    function test_unselectionCallback(self) {
        var observer = Mantissa.Test.TestScrollModel.StubObserver();
        self.model.addObserver(observer);
        self.model.unselectRow('a');
        self.assertIdentical(observer.events.length, 1);
        self.assertIdentical(observer.events[0].type, 'unselected');
        self.assertIdentical(observer.events[0].row.__id__, 'a');
    },

    /**
     * Verify that C{activeRow} returns C{null} before any row has been
     * activated.
     */
    function test_activeRowWithNoActiveRow(self) {
        self.assertIdentical(self.model.activeRow(), null);
    },

    /**
     * Verify that one row can be marked as active using the C{activateRow}
     * method.
     */
    function test_activateRow(self) {
        self.model.activateRow('a');
        self.assertIdentical(self.model.activeRow().__id__, 'a');
    },

    /**
     * Verify that activating a new row deactives the previously active row.
     */
    function test_activeNewRow(self) {
        self.model.setRowData(1, {'__id__': 'b'});
        self.model.activateRow('a');
        self.model.activateRow('b');
        self.assertIdentical(self.model.activeRow().__id__, 'b');
    },

    /**
     * Verify that the C{deactivateRow} method causes there to be no active
     * row.
     */
    function test_deactivateRow(self) {
        self.model.activateRow('a');
        self.model.deactivateRow();
        self.assertIdentical(self.model.activeRow(), null);
    },

    /**
     * Verify that C{deactivateRow} throws the right error if called when no
     * row is active.
     */
    function test_deactivateRowWithNoActiveRow(self) {
        self.assertThrows(
            Mantissa.ScrollTable.NoActiveRow,
            function() { self.model.deactivateRow(); });
    },

    /**
     * Verify that an observer registered with the model is notified when a row
     * becomes active.
     */
    function test_activationCallback(self) {
        var observer = Mantissa.Test.TestScrollModel.StubObserver();
        self.model.addObserver(observer);
        self.model.activateRow('a');
        self.assertIdentical(observer.events.length, 1);
        self.assertIdentical(observer.events[0].type, 'activated');
        self.assertIdentical(observer.events[0].row.__id__, 'a');
    },

    /**
     * Verify that an observer registered with the model is notified when an
     * active row is deactivated.
     */
    function test_deactivationCallback(self) {
        var observer = Mantissa.Test.TestScrollModel.StubObserver();
        self.model.activateRow('a');
        self.model.addObserver(observer);
        self.model.deactivateRow();
        self.assertIdentical(observer.events.length, 1);
        self.assertIdentical(observer.events[0].type, 'deactivated');
        self.assertIdentical(observer.events[0].row.__id__, 'a');
    },

    /**
     * Verify that an observer registered with the model is notified first of
     * the deactivation of an row and then activation of a new row if a new row
     * is activated while an existing row is active.
     */
    function test_activationChanged(self) {
        var observer = Mantissa.Test.TestScrollModel.StubObserver();
        self.model.setRowData(1, {'__id__': 'b'});
        self.model.activateRow('a');
        self.model.addObserver(observer);
        self.model.activateRow('b');
        self.assertIdentical(observer.events.length, 2);
        self.assertIdentical(observer.events[0].type, 'deactivated');
        self.assertIdentical(observer.events[0].row.__id__, 'a');
        self.assertIdentical(observer.events[1].type, 'activated');
        self.assertIdentical(observer.events[1].row.__id__, 'b');
    },

    /**
     * Verify that if the currently active row is removed from the model, it is
     * no longer reported as the active row and that a deactivation event is
     * broadcast to all observers.
     */
    function test_activeRowRemoved(self) {
        var observer = Mantissa.Test.TestScrollModel.StubObserver();
        self.model.activateRow('a');
        self.model.addObserver(observer);
        self.model.removeRow('a');
        self.assertIdentical(self.model.activeRow(), null);
        self.assertIdentical(observer.events.length, 1);
        self.assertIdentical(observer.events[0].type, 'deactivated');
        self.assertIdentical(observer.events[0].row.__id__, 'a');
    },

    /**
     * Verify that if the model is emptied completely with the C{empty} method,
     * the active row becomes no longer active and that a deactivation event is
     * broadast to all observers.
     */
    function test_activeRowEmptied(self) {
        var observer = Mantissa.Test.TestScrollModel.StubObserver();
        self.model.activateRow('a');
        self.model.addObserver(observer);
        self.model.empty();
        self.assertIdentical(self.model.activeRow(), null);
        self.assertIdentical(observer.events.length, 1);
        self.assertIdentical(observer.events[0].type, 'deactivated');
        self.assertIdentical(observer.events[0].row.__id__, 'a');
    });
