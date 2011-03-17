// -*- test-case-name: xmantissa.test.test_javascript -*-

// import Divmod.Runtime
// import Mantissa
// import MochiKit
// import MochiKit.Base
// import MochiKit.Iter
// import MochiKit.DOM



Mantissa.ScrollTable.NoSuchWebID = Divmod.Error.subclass(
    "Mantissa.ScrollTable.NoSuchWebID");
Mantissa.ScrollTable.NoSuchWebID.methods(
    function __init__(self, webID) {
        self.webID = webID;
    },

    function toString(self) {
        return "WebID " + self.webID + " not found";
    });


/**
 * Error class indicating that an operation which requires an active row was
 * attempted when there was no active row.
 */
Mantissa.ScrollTable.NoActiveRow = Divmod.Error.subclass(
    "Mantissa.ScrollTable.NoActiveRow");


Mantissa.ScrollTable.Action = Divmod.Class.subclass(
    'Mantissa.ScrollTable.Action');
/**
 * An action that can be performed on a scrolltable row.
 * (Currently on a single scrolltable row at a time).
 *
 * @ivar name: internal name for this action.  this will be used server-side
 *             to look up the action method.
 *
 * @ivar displayName: external name for this action.
 *
 * @ivar handler: optional.  function that will be called when the remote
 *                method successfully returns.  it will be passed the
 *                L{ScrollingWidget} the row was clicked in, the row that was
 *                clicked (a mapping of column names to values) and the result
 *                of the remote call that was made.  if not set, no action
 *                will be taken.  Alternatively, you can subclass and override
 *                L{handleSuccess}.
 *
 * @ivar icon: optional.  if set, then it will be used for the src attribute of
 *             an <IMG> element that will get placed inside the action link,
 *             instead of C{name}.
 */
Mantissa.ScrollTable.Action.methods(
    function __init__(self, name, displayName,
                      handler/*=undefined*/, icon/*=undefined*/) {
        self.name = name;
        self.displayName = displayName;
        self._successHandler = handler;
        self.icon = icon;
    },

    /**
     * Called by onclick handler created in L{toNode}.
     * Responsible for calling remote method, and dispatching the result to
     * C{self.handler}, if one is set.
     *
     * Arguments are the same as L{toNode}
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function enact(self, scrollingWidget, row) {
        var D = scrollingWidget.callRemote(
                    "performAction", self.name, row.__id__);
        return D.addCallbacks(
                function(result) {
                    return self.handleSuccess(scrollingWidget, row, result);
                },
                function(err) {
                    return self.handleFailure(scrollingWidget, row, err);
                });
    },

    /**
     * Called when the remote method successfully returns, with its result.
     * Calls the function supplied as C{handler} to L{__init__}, if defined.
     *
     * First two arguments are the same as L{toNode}
     */
    function handleSuccess(self, scrollingWidget, row, result) {
        if(self._successHandler) {
            return self._successHandler(scrollingWidget, row, result);
        }
    },

    /**
     * Called when the remote method, or one of its callbacks throws an error.
     * Displays an error dialog to the user.
     *
     * First two arguments are the same as L{toNode}
     */
    function handleFailure(self, scrollingWidget, row, err) {
        scrollingWidget.showErrorDialog("performAction", err);
    },

    /**
     * Called by L{Mantissa.ScrollTable.ScrollingWidget}.
     * Responsible for turning this action into a link node.
     *
     * @param scrollingWidget: L{Mantissa.ScrollTable.ScrollingWidget}
     * @param row: L{Object} mapping column names to column values of the row
     *             that this action will act on when clicked
     */
    function toNode(self, scrollingWidget, row) {
        var onclick = function() {
            self.enact(scrollingWidget, row);
            return false;
        };
        var linkBody;
        if(self.icon) {
            linkBody = MochiKit.DOM.IMG({border: 0, src: self.icon});
        } else {
            linkBody = self.displayName;
        }
        return MochiKit.DOM.A({onclick: onclick, href: "#"}, linkBody);
    },

    /**
     * Called by L{Mantissa.ScrollTable.ScrollingWidget}.
     *
     * @type row: C{object}
     * @return: boolean indicating whether this action should be enabled for
     * C{row}
     */
    function enableForRow(self, row) {
        return true;
    });


/**
 * Base class for shared ("legacy") methods between old (index-based)
 * ScrollModel and new (inequality-based) RegionModel.
 */

Mantissa.ScrollTable._ModelBase = Divmod.Class.subclass(
    "Mantissa.Scrolltable._ModelBase");
Mantissa.ScrollTable._ModelBase.methods(
    function __init__(self) {
        self._activeRow = null;
        self._selectionObservers = [];
    },

    /**
     * Mark the specified row as active.  Activation differs from selection in
     * that only a single row can be active at a time.
     *
     * @type identifier: String
     * @param identifier: The unique identifier for the row to activate.
     *
     * @throw NoSuchWebID: Thrown if the given identifier is not found.
     */
    function activateRow(self, identifier) {
        if (self._activeRow != null) {
            self.deactivateRow();
        }
        self._activeRow = self.findRowData(identifier);
        for (var i = 0; i < self._selectionObservers.length; ++i) {
            self._selectionObservers[i].rowActivated(self._activeRow);
        }
    },

    /**
     * Set up an object to receive notification of selection changes.
     */
    function addObserver(self, observer) {
        self._selectionObservers.push(observer);
    },

    /**
     * Check whether or not a particular row is selected.
     */
    function isSelected(self, identifier) {
        var row = self.findRowData(identifier);
        return (row.__selected__ === true);
    },

    /**
     * Call a function with each selected row or with the active row if there
     * is one and there are no selected rows.
     *
     * @param visitor: A one-argument function which will be invoked once for
     * each selected row, or once with the active row if there is one and there
     * are no selected rows.
     *
     * @return: undefined
     */
    function visitSelectedRows(self, visitor) {
        var row;
        var anySelected = false;
        var indices = self.getRowIndices();
        for (var i = 0; i < indices.length; ++i) {
            row = self._rows[indices[i]];
            if (row.__selected__) {
                visitor(row);
                anySelected = true;
            }
        }
        if (!anySelected) {
            row = self.activeRow();
            if (row !== null) {
                visitor(row);
            }
        }
    },

    /**
     * Add the specified row to the selection.  Any number of rows may be
     * selected at once.
     *
     * @type identifier: String
     * @param identifier: The unique identifier for the row to select.
     *
     * @throw Error: Thrown if the given identifier is not found.
     */
    function selectRow(self, identifier) {
        var row = self.findRowData(identifier);
        row.__selected__ = true;
        for (var i = 0; i < self._selectionObservers.length; ++i) {
            self._selectionObservers[i].rowSelected(row);
        }
    },

    /**
     * Remove the specified row from the selection.
     *
     * @type identifier: String
     * @param identifier: The unique identifier for the row to unselect.
     *
     * @throw Error: Thrown if the given identifier is not found.
     */
    function unselectRow(self, identifier) {
        var row = self.findRowData(identifier);
        row.__selected__ = false;
        for (var i = 0; i < self._selectionObservers.length; ++i) {
            self._selectionObservers[i].rowUnselected(row);
        }
    },

    /**
     * Make the currently active row non-active.
     *
     * @throw NoActiveRow: Thrown if there is no active row.
     */
    function deactivateRow(self) {
        if (self._activeRow == null) {
            throw Mantissa.ScrollTable.NoActiveRow();
        }
        for (var i = 0; i < self._selectionObservers.length; ++i) {
            self._selectionObservers[i].rowDeactivated(self._activeRow);
        }
        self._activeRow = null;
    },

    /**
     * @return: The currently active row object, or C{null} if no row is
     * active.
     */
    function activeRow(self) {
        return self._activeRow;
    },

    /**
     * Find the row data for the row with web id C{webID}.
     *
     * @type webID: string
     *
     * @rtype: object
     * @return: The structured data associated with the given webID.
     *
     * @throw Error: Thrown if the given webID is not found.
     */
    function findRowData(self, webID) {
        return self.getRowData(self.findIndex(webID));
    }
);

/**
 * Structured representation of the rows in a scrolltable.
 *
 * @ivar _rows: A sparse array of row data for this table.
 *
 * @ivar _activeRow: null or a reference to the row data which is currently
 * considered "active".  At most one row can be active at a time.  The active
 * row can be manipulated with L{activateRow} and L{deactivateRow}.  Changes to
 * the active row are broadcast to all listeners registered with
 * L{addObserver}.
 *
 * @ivar _totalRowCount: An integer giving the total number of rows in the
 * model, ignoring whether row data is available for all of them or not.
 *
 * @ivar _selectionObservers: An array of objects which have been added as
 * selection observers using the addObserver method.  These will be notified of
 * changes to the active row and the row selection group.
 */
Mantissa.ScrollTable.ScrollModel = Mantissa.ScrollTable._ModelBase.subclass(
    'Mantissa.ScrollTable.ScrollModel');
Mantissa.ScrollTable.ScrollModel.methods(
    function __init__(self) {
        Mantissa.ScrollTable.ScrollModel.upcall(self, "__init__");
        self._rows = [];
        self._totalRowCount = 0;
    },

    /**
     * @rtype: integer
     * @return: The number of rows in the model which we have already fetched.
     */
    function rowCount(self) {
        return self._rows.length;
    },

    /**
     * @rtype: integer
     * @return: The total number of rows in the model, i.e. the maximum number
     * of rows we could fetch
     */
    function totalRowCount(self) {
        return self._totalRowCount;
    },

    /**
     * Change the total number of rows in the model.
     * @type count: integer
     */
    function setTotalRowCount(self, count) {
        self._totalRowCount = count;
    },

    /**
     * Retrieve the index for the row data associated with the given webID.
     *
     * @type webID: string
     *
     * @rtype: integer
     *
     * @throw NoSuchWebID: Thrown if the given webID corresponds to no row in
     * the model.
     */
    function findIndex(self, webID) {
        for (var i = 0; i < self._rows.length; i++) {
            if (self._rows[i] != undefined && self._rows[i].__id__ == webID) {
                return i;
            }
        }
        throw Mantissa.ScrollTable.NoSuchWebID(webID);
    },

    /**
     * Set the data associated with a particular row.
     *
     * @type index: integer
     * @param index: The index of the row for which to set the data.
     *
     * @type data: The data to associate with the row.
     *
     * @throw Divmod.IndexError: Thrown if the row's index is less than zero.
     * @throw Error: Thrown if the row data's __id__ property is not a string.
     */
    function setRowData(self, index, data) {
        if (index < 0) {
            throw Divmod.IndexError("Specified index (" + index + ") out of bounds in setRowData.");
        }
        /*
         * XXX I hate `typeof'.  It is an abomination.  Why the hell is
         *
         *  typeof '' == 'string'
         *
         * but not
         *
         *  '' instanceof String?"
         *
         */
        if (typeof data.__id__ != 'string') {
            throw new Error("Specified row data has invalid __id__ property.");
        }

        /*
         * XXX No one should be setting row data for rows which already have
         * data, but we don't explicitly forbid it, so it may happen.  We do
         * _not_ preserve selection here, nor do we broadcast a deselection
         * event to observers (or a selection event if the new row data is
         * marked with __selected__).  Row activation is also totally bogus,
         * since if the clobbered row was active, it will still be referenced
         * by _activeRow.  If replacing existing rows is actually important,
         * this needs to be fixed.
         */
        self._rows[index] = data;
    },

    /**
     * Retrieve the row data for the row at the given index.
     *
     * @type index: integer
     *
     * @rtype: object
     * @return: The structured data associated with the row at the given index.
     *
     * @throw Divmod.IndexError: Thrown if the given index is out of bounds.
     */
    function getRowData(self, index) {
        if (index < 0 || index >= self._rows.length) {
            throw Divmod.IndexError("Specified index (" + index + ") out of bounds in getRowData.");
        }
        if (self._rows[index] === undefined) {
            return undefined;
        }
        return self._rows[index];
    },

    /**
     * Retrieve an array of indices for which local data is available.
     */
    function getRowIndices(self) {
        var indices = Divmod.dir(self._rows);
        for (var i = 0; i < indices.length; ++i) {
            indices[i] = parseInt(indices[i]);
        }
        return indices.sort(
            function(a, b) {
                if (a < b) {
                    return -1;
                }
                if (a > b) {
                    return 1;
                }
                return 0;
            });
    },

    /**
     * Find the first row which appears after C{row} in the scrolltable and
     * satisfies C{predicate}
     *
     * @type webID: string
     * @param webID: The web ID of the node at which to begin.
     *
     * @type predicate: function(rowIndex, rowData, rowNode) -> boolean
     * @param predicate: A optional callable which, if supplied, will be called
     * with each row to determine if it suitable to be returned.
     *
     * @rtype: string
     * @return: The web ID for the first set of arguments that satisfies
     * C{predicate}.  C{null} is returned if no rows are found after the given
     * web ID.
     */
    function findNextRow(self, webID, predicate) {
        var row;
        for (var i = self.findIndex(webID) + 1; i < self.rowCount(); ++i) {
            row = self.getRowData(i);
            if (row != undefined) {
                if (!predicate || predicate.call(null, i, row, row.__node__)) {
                    return row.__id__;
                }
            }
        }
        return null;
    },

    /**
     * Same as L{findNextRow}, except returns the first row which appears before C{row}
     */
    function findPrevRow(self, webID, predicate) {
        var row;
        for (var i = self.findIndex(webID) - 1; i > -1; --i) {
            row = self.getRowData(i);
            if (row != undefined) {
                if (!predicate || predicate.call(null, i, row, row.__node__)) {
                    return row.__id__;
                }
            }
        }
        return null;
    },

    /**
     * Remove a particular row from the scrolltable.
     *
     * @type webID: integer
     * @param webID: The index of the row to remove.
     *
     * @return: The row data which was removed.
     */
    function removeRow(self, index) {
        var row = self._rows.splice(index, 1)[0];
        if (row == self._activeRow) {
            self.deactivateRow();
        }
        return row;
    },

    /**
     * Remove all rows from the scrolltable.
     */
    function empty(self) {
        self._rows = [];
        if (self._activeRow != null) {
            self.deactivateRow();
        }
    });

Mantissa.ScrollTable.PlaceholderModel = Divmod.Class.subclass('Mantissa.ScrollTable.PlaceholderModel');
Mantissa.ScrollTable.PlaceholderModel.methods(
    function __init__(self) {
        self._placeholderRanges = [];
    },

    /**
     * Find the index of the placeholder which spans the area that the row at
     * C{rowIndex} will appear at
     *
     * @param rowIndex: integer
     *
     * @rtype: integer
     */
    function findPlaceholderIndexForRowIndex(self, rowIndex) {
        var pranges = self._placeholderRanges,
            len = pranges.length,
            lo = 0, hi = len, mid, midnew;

        while(true) {
            midnew = Math.floor((lo + hi) / 2);
            if(len-1 < midnew || midnew < 0 || mid == midnew) {
                return null;
            }
            mid = midnew;
            if(pranges[mid].stop <= rowIndex) {
                lo = mid + 1;
            } else if(rowIndex < pranges[mid].start) {
                hi = mid - 1;
            } else {
                return mid;
            }
       }
    },

    /**
     * Find the index of the first placeholder that starts after the row at
     * index C{rowIndex}.
     *
     * @param rowIndex: index of the reference row
     * @type rowIndex: integer
     *
     * @rtype: placeholder or null
     */
    function findFirstPlaceholderIndexAfterRowIndex(self, rowIndex) {
        var pranges = self._placeholderRanges,
            len = pranges.length,
            lo = 0, hi = len, mid;

        while(true) {
            mid = Math.floor((lo + hi) / 2);
            if(len-1 < mid || mid < 0) {
                return null;
            }
            /* this is difficult to think about.  what we're trying to say is
             * that we're done when we find the placeholder such that:
             *       * the placeholder starts after the index of the row we want
             *       * the placeholder before it stops before the index of the row we want
             *    OR
             *       * the placeholder starts after the index of the row we want
             *       * there is no placeholder before it
             *
             *  example:
             *
             *  | start: 0, stop: 1 |
             *  | start: 1, stop: 2 |
             *  | start: 3, stop: 4 |
             *  | start: 5, stop: 6 |
             *
             *  for a row index of 2, we want the 3 - 4 placeholder because:
             *       * 1 - 2 stops before the index of the row we want
             *       * 3 - 4 starts after the index of the row we want
             */
            if(pranges[mid].start <= rowIndex) {
                lo = mid + 1;
            } else if(0 < mid && rowIndex < pranges[mid-1].stop-1) {
                hi = mid - 1;
            } else {
                return mid;
            }
        }
    },

    /**
     * Called after a row has been removed.  Adjusts the placeholder state to
     * take this into account.
     *
     * @param rowIndex: index of the row that was removed
     * @type rowIndex: integer
     */
    function removedRow(self, rowIndex) {
        var i = self.findFirstPlaceholderIndexAfterRowIndex(rowIndex),
            pranges = self._placeholderRanges;
        if(i == null) {
            return;
        }
        for(; i < pranges.length; i++) {
            pranges[i].start--;
            pranges[i].stop--;
        }
    },

    /**
     * Find the placeholder object stored at index C{index}
     *
     * @type index: integer
     * @rtype: placeholder
     */
    function getPlaceholderWithIndex(self, index) {
        return self._placeholderRanges[index];
    },

    /**
     * Get the number of placeholders
     *
     * @rtype: integer
     */
    function getPlaceholderCount(self) {
        return self._placeholderRanges.length;
    },

    /**
     * Create and register a placeholder which extends from the zeroth row to
     * the end of the last row, overwriting any other placeholders.
     *
     * @param totalRowCount: total number of rows
     * @param node: same as L{createPlaceholder}'s C{node} argument
     */
    function registerInitialPlaceholder(self, totalRowCount, node) {
        self._placeholderRanges = [self.createPlaceholder(0, totalRowCount, node)];
    },

    /**
     * Replace placeholder with index C{index} with C{replacement}
     *
     * @type index: integer
     * @type replacement: placeholder
     */
    function replacePlaceholder(self, index, replacement) {
        self._placeholderRanges[index] = replacement;
    },

    /**
     * Divide the placeholder with index C{index} into two placeholders,
     * C{above} and C{below}.
     *
     * @type index: integer
     * @type above: placeholder
     * @type below: placeholder
     */
    function dividePlaceholder(self, index, above, below) {
        self._placeholderRanges.splice.apply(
            self._placeholderRanges, [index, 1].concat([above, below]));
    },

    /**
     * Remove the placeholder at C{index}
     *
     * @type index: integer
     */
    function removePlaceholder(self, index) {
        self._placeholderRanges.splice(index, 1);
    },

    /**
     * Remove all placeholders
     */
    function empty(self) {
        self._placeholderRanges = [];
    },

    /**
     * Create a placeholder which starts at C{start}, stops at C{stop}, and
     * is represented by the DOM node C{node}
     *
     * @param start: the index of the row that the placeholder starts at
     * @param stop: the index of the row that the placeholder stops at
     *
     * @return: object with "start" and "stop" members, corresponding to the
     * arguments of this method
     *
     * For a scrolltable like this:
     * | 0: REAL ROW    |
     * | 1: REAL ROW    |
     * | 2: PLACEHOLDER |
     * | 3: REAL ROW    |
     * the placeholder at index #2 would have start=2 and stop=3
     */
    function createPlaceholder(self, start, stop, node) {
        return {start: start, stop: stop, node: node};
    });


/**
 * This class defines DOM behaviors which are held in common between the
 * index-based ScrollingWidget and the value-based ScrollTable.
 *
 * Currently, subclasses must set all of these instance variables during
 * initialization.
 *
 * @ivar columnNames: an ordered list of the names of the columns provided.
 *
 * @ivar _rowHeight: an integer, the number of pixels that represents one row height.
 *
 * @ivar columnTypes: an object, with attributes named by the strings in
 * columnNames, and values that identify the types of the columns.
 */

Mantissa.ScrollTable._ScrollingBase = Nevow.Athena.Widget.subclass(
    'Mantissa.ScrollTable._ScrollingBase');

Mantissa.ScrollTable._ScrollingBase.methods(
    /**
     * @param name: column name
     * @return: boolean, indicating whether this column should not be rendered
     */
    function skipColumn(self, name) {
        if (name == 'toString') {
            /* YOU ARE NOT INVITED TO MY PIZZA PARTY JAVASCRIPT */
            return true;
        }
        return false;
    },

    /**
     * @type rowData: object
     *
     * @return: actions that are enabled for row C{rowData}
     * @rtype: array of L{Mantissa.ScrollTable.Action} instances
     */
    function getActionsForRow(self, rowData) {
        var enabled = [];
        for(var i = 0; i < self.actions.length; i++) {
            if(self.actions[i].enableForRow(rowData)) {
                enabled.push(self.actions[i]);
            }
        }
        return enabled;
    },

    /**
     * Make a node with some event handlers to perform actions on the row
     * specified by C{rowData}.
     *
     * @param rowData: Some data received from the server.
     *
     * @return: A DOM node.
     */
    function _makeActionsCells(self, rowData) {
        var actions = self.getActionsForRow(rowData);
        var actionNodes = [];
        for(var i = 0; i < actions.length; i++) {
            actionNodes.push(actions[i].toNode(self, rowData));
            actionNodes.push(document.createTextNode(" "));
        }
        if (actionNodes.length) {
            actionNodes.pop();
        }
        var attrs = {"class": "scroll-cell"};
        if(self.columnWidths && "actions" in self.columnWidths) {
            attrs["style"] = "width:" + self.columnWidths["actions"];
        }
        return MochiKit.DOM.TD(attrs, actionNodes);
    },

    /**
     * Make a DOM node for the given row.
     *
     * @param rowOffset: The (possibly approximate) index in the scroll model
     * of the row data being rendered.  This parameter will be removed in the
     * future, as it is sometimes impossible to predict an exact offset, which
     * is needed to do what this is attempting to (color the rows with
     * alternating colors).
     *
     * @param rowData: The row data for which to make an element.
     *
     * @return: A DOM node.
     */
    function _createRow(self, rowOffset, rowData) {
        var cells = [];

        for (var colName in rowData) {
            if(!(colName in self._columnOffsets) || self.skipColumn(colName)) {
                continue;
            }
            cells.push([colName, self.makeCellElement(colName, rowData)]);
        }
        if(self.actions && 0 < self.actions.length) {
            cells.push(["actions", self._makeActionsCells(rowData)]);
        }

        cells = cells.sort(
            function(data1, data2) {
                var a = self._columnOffsets[data1[0]];
                var b = self._columnOffsets[data2[0]];

                if (a<b) {
                    return -1;
                }
                if (a>b) {
                    return 1;
                }
                return 0;
            });

        var nodes = [];
        for (var i = 0; i < cells.length; ++i) {
            nodes.push(cells[i][1]);
        }
        return self.makeRowElement(rowOffset, rowData, nodes);
    },

    /**
     * Create a element to represent the given row data in the scrolling
     * widget.
     *
     * @param rowOffset: The index in the scroll model of the row data being
     * rendered.
     *
     * @param rowData: The row data for which to make an element.
     *
     * @param cells: Array of elements (DOM nodes) which represent the column
     * data for this row.
     *
     * @return: An element
     */
    function makeRowElement(self, rowOffset, rowData, cells) {
        var style = "height: " + self._rowHeight + "px";
        if (self._rowHeight === 0) {
            style = "";
        }
        if(rowOffset % 2) {
            style += "; background-color: #F0F0F0";
        }
        return MochiKit.DOM.TR(
            {"class": "scroll-row",
             "style": style,
             "valign": "center"},
            cells);
    },

    /**
     * Return an object the properties of which are named like columns and
     * refer to those columns' display indices.
     */
    function _getColumnOffsets(self, columnNames) {
        var columnOffsets = {};
        for( var i = 0; i < columnNames.length; i++ ) {
            if(self.skipColumn(columnNames[i])) {
                continue;
            }
            columnOffsets[columnNames[i]] = i;
        }
        return columnOffsets;
    },

    /**
     * This method is deprecated; it is not necessary in the new
     * L{ScrollTable} widget.  See L{TimestampColumn.valueToDOM}.
     *
     * Convert a Date instance to a human-readable string.
     *
     * @type when: C{Date}
     * @param when: The time to format as a string.
     *
     * @type now: C{Date}
     * @param now: If specified, the date which will be used to determine how
     * much context to provide in the returned string.
     *
     * @rtype: C{String}
     * @return: A string describing the date C{when} with as much information
     * included as is required by context.
     */
    function formatDate(self, date, /* optional */ now) {
        return date.toUTCString();
    },

    /**
     * This method is deprecated; it is not necessary in the new
     * L{ScrollTable} widget.  See L{Column.valueToDOM}.
     *
     * @param columnName: The name of the column for which this is a value.
     *
     * @param columnType: A string which might indicate the data type of the
     * values in this column (if you have the secret decoder ring).
     *
     * @param columnValue: An object received from the server.
     *
     * @return: The object to put into the DOM for this value.
     */
    function massageColumnValue(self, columnName, columnType, columnValue) {
        if(columnType == 'timestamp') {
            return self.formatDate(new Date(columnValue * 1000));
        }
	if(columnValue ==  null) {
            return '';
	}
        return columnValue;
    },

    /**
     * Update internal state associated with displaying column data, including:
     *
     * - _columnOffsets
     * - _rowHeight
     * - the _headerRow node.
     *
     * Call this whenever the return value of skipColumn might have changed.
     */
    function resetColumns(self) {
        /* set _columnOffsets before calling _getRowHeight() so that
         * _getRowGuineaPig() can call _createRow() */
        self._columnOffsets = self._getColumnOffsets(self.columnNames);
        self._rowHeight = self._getRowHeight();

        while (self._headerRow.firstChild) {
            self._headerRow.removeChild(self._headerRow.firstChild);
        }

        self._headerNodes = self._createRowHeaders(self.columnNames);
        for (var i = 0; i < self._headerNodes.length; ++i) {
            self._headerRow.appendChild(self._headerNodes[i]);
        }
    },

    /**
     * Return an Array of nodes to be used as column headers.
     *
     * @param columnNames: An Array of strings naming the columns in this
     * table.
     */
    function _createRowHeaders(self, columnNames) {
        var capitalize = function(s) {
            var words = s.split(/ /);
            var capped = "";
            for(var i = 0; i < words.length; i++) {
                capped += words[i].substr(0, 1).toUpperCase();
                capped += words[i].substr(1, words[i].length) + " ";
            };
            return capped;
        };

        var headerNodes = [];
        var sortable, attrs;

        for (var i = 0; i < columnNames.length; i++ ) {
            if(self.skipColumn(columnNames[i])) {
                continue;
            }

            var columnName = columnNames[i];
            var displayName;

            if(self.columnAliases && columnName in self.columnAliases) {
                displayName = self.columnAliases[columnName];
            } else {
                displayName = capitalize(columnName);
            }

            attrs = {"class": "scroll-column-header"};

            if(self.columnWidths && columnName in self.columnWidths) {
                attrs["style"] = "width:" + self.columnWidths[columnName];
            }

            if(columnName == "actions") {
                attrs["class"] = "actions-column-header";
            } else {
                sortable = self.columnTypes[columnName][1];

                if(sortable) {
                    attrs["class"] = "sortable-" + attrs["class"];
                    /*
                    * Bind the current value of columnName instead of just closing
                    * over it, since we're mutating the local variable in a loop.
                    */
                    attrs["onclick"] = (function(whichColumn) {
                            return function() {
                                /* XXX real-time feedback, ugh */
                                self.resort(whichColumn);
                            }
                        })(columnName);
                }
            }

            var headerNode = MochiKit.DOM.TD(attrs, displayName);
            headerNodes.push(headerNode);

        }
        return headerNodes;
    },

    /**
     * Make an element which will be displayed for the value of one column in
     * one row.
     *
     * @param colName: The name of the column for which to make an element.
     *
     * @param rowData: An object received from the server.
     *
     * @return: A DOM node.
     */
    function makeCellElement(self, colName, rowData) {
        var attrs = {"class": "scroll-cell"};
        if(self.columnWidths && colName in self.columnWidths) {
            attrs["style"] = "width:" + self.columnWidths[colName];
        }
        var node = MochiKit.DOM.TD(
            attrs,
            /* unfortunately we have to put a link inside each cell - IE
             * doesn't seem to display rows if they are anchors with
             * display: table-row
             */
            MochiKit.DOM.A({"style": "display: block",
                            "href": rowData.__id__},
                self.massageColumnValue(
                    colName,
                    self.columnTypes[colName][0],
                    rowData[colName])));

        if (self.columnTypes[colName][0] == "fragment") {
            Divmod.Runtime.theRuntime.setNodeContent(
                node.firstChild,
                '<div xmlns="http://www.w3.org/1999/xhtml">' + rowData[colName]
                + '</div>');
        }
        return node;
    });


/**
 * @ivar actions: An array of L{Mantissa.ScrollTable.Action} instances which
 * define ways which a user can interact with rows in this scrolltable.  May
 * be undefined to indicate there are no possible actions.
 *
 * @ivar columnAliases: An object mapping column names to text which will be
 * used in the construction of column headers.  If a column name is present
 * as a property on this object, the value will be placed in the column
 * heading, instead of the column name.  Any column name may be absent, in
 * which case the case-normalized column name will be used to construct the
 * header.  If this property is undefined, it will be treated the same as if
 * it were an object with no properties.
 *
 * @ivar lastScrollPos: Height in pixels of the top of the viewport in the
 * scrolling region after the most recent scroll event.  C{0} initially and
 * after being emptied.
 */
Mantissa.ScrollTable.ScrollingWidget = Mantissa.ScrollTable._ScrollingBase.subclass(
    'Mantissa.ScrollTable.ScrollingWidget');

Mantissa.ScrollTable.ScrollingWidget.methods(
    function __init__(self, node, metadata) {
        Mantissa.ScrollTable.ScrollingWidget.upcall(self, '__init__', node);

        self._rowTimeout = null;
        self._requestWaiting = false;
        self._moreAfterRequest = false;

        self.scrollingDown = true;
        self.lastScrollPos = 0;

        self._scrollViewport = self.nodeByAttribute('class', 'scroll-viewport');
        self._headerRow = self.nodeByAttribute('class', 'scroll-header-row');

        /*
         * A list of Deferreds which have been returned from the L{scrolled}
         * method and have yet to be fired.
         */
        self._scrollDeferreds = [];

        self.placeholderModel = Mantissa.ScrollTable.PlaceholderModel();
        self.model = Mantissa.ScrollTable.ScrollModel();

        self.setTableMetadata.apply(self, metadata);
        self.initializationDeferred = self._getSomeRows(true);
    },

    /**
     * Retrieve the structural definition of this table.
     *
     * @return: A Deferred which fires with an array with five elements.  They
     * are::
     *
     *    An array of strings naming the columns in this table.
     *
     *    An array of two-arrays giving the type and sortability of the columns
     *    in this table.
     *
     *    An integer giving the number of rows in this table.
     *
     *    A string giving the name of the column by which the table is
     *    currently ordered.
     *
     *    A boolean indicating whether the ordering is currently ascending
     *    (true) or descending (false).
     */
    function getTableMetadata(self) {
        return self.callRemote("getTableMetadata");
    },

    /**
     * Set up the tabular structure of this ScrollTable.
     *
     * @type columnNames: C{Array} of C{String}
     * @param columnNames: Names of the columns visible in this ScrollTable.
     *
     * @type columnTypes: C{Array} of C{String}
     * @param columnTypes: Names of the types of the columns visible in this
     * ScrollTable.
     *
     * @type rowCount: C{Integer}
     * @param rowCount: The total number of rows in the model.
     *
     * @type currentSort: C{String}
     * @param currentSort: The name of the column by which the model is
     * ordered.
     *
     * @type isAscendingNow: C{Boolean}
     * @param isAscendingNow: Whether the sort is ascending.
     *
     * @return: C{undefined}
     */
    function setTableMetadata(self, columnNames, columnTypes, rowCount,
                              currentSort, isAscendingNow) {
        self.columnNames = columnNames;
        self.columnTypes = columnTypes;

        if(self.actions && 0 < self.actions.length) {
            self.columnNames.push("actions");
        }

        self.resetColumns();
        self._setSortHeader(currentSort, isAscendingNow);
        self.model.setTotalRowCount(rowCount);
        self.padViewportWithPlaceholderRow(rowCount);
    },

    /**
     * Retrieve a range of row data from the server.
     *
     * @type firstRow: integer
     * @param firstRow: zero-based index of the first message to retrieve.
     *
     * @type lastRow: integer
     * @param lastRow: zero-based index of the message after the last message
     * to retrieve.
     */
    function getRows(self, firstRow, lastRow) {
        return self.callRemote("requestRowRange", firstRow, lastRow);
    },

    /**
     * Retrieve a range of row data from the server and store it locally.
     *
     * @type firstRow: integer
     * @param firstRow: zero-based index of the first message to retrieve.
     *
     * @type lastRow: integer
     * @param lastRow: zero-based index of the message after the last message
     * to retrieve.
     */
    function requestRowRange(self, firstRow, lastRow) {
        return self.getRows(firstRow, lastRow).addCallback(
            function(rows) {
                self._storeRows(firstRow, lastRow, rows);
                return rows;
            });
    },

    function _storeRows(self, firstRow, lastRow, rows) {
        var rowNodes = [];
        for (var i = firstRow; i < rows.length + firstRow; ++i) {
            row = rows[i - firstRow];
            if (i >= self.model.rowCount() || self.model.getRowData(i) == undefined) {
                row.__node__ = self._createRow(i, row);
                self.model.setRowData(i, row);
                rowNodes.push({index: i, node: row.__node__});
            }
        }
        self._addRowsToViewport(rowNodes);
    },

    /**
     * Add C{rows} to the scroll viewport, replacing or splitting any
     * placeholder rows that are in the way.
     *
     * @param rows: array of objects with "index" and "node" members
     */
    function _addRowsToViewport(self, rows) {
        /* this could be made faster, if we have more than one row that falls
         * inside a single placeholder - we only need to split it once instead
         * of once per row, i think */
        var sviewport = self._scrollViewport,
            pmodel = self.placeholderModel,
            placeholder, placeholders, placeholderEntry, above, below;

        var maybeCreatePlaceholder = function(start, stop, replacing) {
            if(start < stop) {
                var obj = self.placeholderModel.createPlaceholder(
                            start, stop, self.makePlaceholderRowElement(
                                            (stop - start) * self._rowHeight));
                sviewport.insertBefore(obj.node, replacing);
                return obj;
            };
        };

        for(var i = 0; i < rows.length; i++) {
            placeholderIndex = pmodel.findPlaceholderIndexForRowIndex(rows[i].index);
            if(placeholderIndex !== null) {
                placeholder = pmodel.getPlaceholderWithIndex(placeholderIndex);

                above = maybeCreatePlaceholder(
                            placeholder.start, rows[i].index, placeholder.node);

                sviewport.insertBefore(rows[i].node, placeholder.node);

                below = maybeCreatePlaceholder(
                            rows[i].index+1, placeholder.stop, placeholder.node);

                sviewport.removeChild(placeholder.node);

                if(above && below) {
                    pmodel.dividePlaceholder(placeholderIndex, above, below);
                } else if(above || below) {
                    pmodel.replacePlaceholder(placeholderIndex, above || below);
                } else {
                    pmodel.removePlaceholder(placeholderIndex);
                }
            } else {
                sviewport.appendChild(rows[i].node);
            }
        }
    },

    /**
     * Remove the indicated row's data from the model and remove its DOM nodes
     * from the document.
     *
     * @type index: integer
     * @param index: The index of the row to remove.
     *
     * @return: The row data for the removed row.
     */
    function removeRow(self, index) {
        var rowData = self.model.removeRow(index);
        rowData.__node__.parentNode.removeChild(rowData.__node__);
        self.placeholderModel.removedRow(index);
        return rowData;
    },

    /**
     * Retrieve a node which is the same height as rows in the table will be.
     */
    function _getRowGuineaPig(self) {
        return MochiKit.DOM.TR(
            {"style": "visibility: hidden",
             "class": "scroll-row",
             "valign": "center"},
            MochiKit.DOM.TD(
                {"class": "scroll-cell"},
                MochiKit.DOM.A({"href": "#"}, "TEST!!!")));
    },

    /**
     * Determine the height of a row in this scrolltable.
     */
    function _getRowHeight(self) {
        var node = self._getRowGuineaPig();
        var rowHeight;

        /*
         * Put the node into the document so that the browser actually figures
         * out how tall it is.  Don't put it into the scrolltable itself or
         * anything clever like that, in case the scrolltable has some style
         * applied to it that would mess things up. (XXX The body could have a
         * style applied to it that could mess things up? -exarkun)
         */
        var tableNode = MochiKit.DOM.TABLE(null, node);
        document.body.appendChild(tableNode);
        rowHeight = Divmod.Runtime.theRuntime.getElementSize(node).h;
        document.body.removeChild(tableNode);

        if (rowHeight == 0) {
            rowHeight = Divmod.Runtime.theRuntime.getElementSize(self._headerRow).h;
        }

        if (rowHeight == 0) {
            rowHeight = 20;
        }

        return rowHeight;
    },

    /**
     * Set the display height of the scroll view DOM node to a height
     * appropriate for displaying the given number of rows, by appending
     * C{rowCount} placeholder rows to it
     *
     * @type rowCount: integer
     * @param rowCount: The number of rows which should fit into the view node.
     */
    function padViewportWithPlaceholderRow(self, rowCount) {
        var row = self.makePlaceholderRowElement(rowCount * self._rowHeight);
        self._scrollViewport.appendChild(row);

        self.placeholderModel.registerInitialPlaceholder(rowCount, row);
    },

    /**
     * This method is responsible for returning the height of the scroll
     * viewport in pixels.  The result is used to calculate the number of
     * rows needed to fill the screen.
     *
     * Under a variety of conditions (for example, a "display: none" style
     * applied to the viewport node), the browser may not report a height for
     * the viewport.  In this case, fall back to the size of the page.  This
     * will result in too many rows being requested, maybe, which is not very
     * harmful.
     */
    function getScrollViewportHeight(self) {
        var height = Divmod.Runtime.theRuntime.getElementSize(
            self._scrollViewport).h;

        /*
         * Firefox returns 0 for the clientHeight of display: none elements, IE
         * seems to return the height of the element before it was made
         * invisible.  There also seem to be some cases where the height will
         * be 0 even though the element has been added to the DOM and is
         * visible, but the browser hasn't gotten around to sizing it
         * (presumably in a different thread :( :( :() yet.  Default to the
         * full window size for these cases.
         */

        if (height == 0 || isNaN(height)) {
            /*
             * Called too early, just give the page height.  at worst we'll end
             * up requesting 5 extra rows or whatever.
             */
            height = Divmod.Runtime.theRuntime.getPageSize().h;
        }
        return height;
    },

    /**
     * Figure out the start and end indexes of rows that should be requested
     *
     * @param scrollingDown: A flag indicating whether we are scrolling down,
     * and so whether the requested rows should be below the current position
     * or not.
     *
     * @return: pair of [startIndex, stopIndex] or null if there isn't a
     * useful row range to request
     */
    function _calculateDesiredRowRange(self, scrollingDown) {
        var scrollViewportHeight = self.getScrollViewportHeight();
        var desiredRowCount = Math.ceil(scrollViewportHeight / self._rowHeight);
        var firstRow = Math.floor(self._scrollViewport.scrollTop / self._rowHeight);
        var requestNeeded = false;
        var i;

        /*
         * Never do less than 1 row of work.  The most likely cause of
         * desiredRowCount being 0 is that the browser screwed up some height
         * calculation.  We'll at least try to get 1 row (and maybe we should
         * actually try to get more than that).
         */
        if (desiredRowCount < 1) {
            desiredRowCount = 1;
        }

        if (scrollingDown) {
            for (i = 0; i < desiredRowCount; i++) {
                if (firstRow >= self.model.rowCount() || self.model.getRowData(firstRow) == undefined) {
                    requestNeeded = true;
                    break;
                }
                firstRow++;
            }
        } else {
            for (i = 0; i < desiredRowCount; i++) {
                var rowIndex = firstRow + desiredRowCount - 1;
                if (rowIndex < 0) {
                    break;
                }
                if (rowIndex >= self.model.rowCount() || self.model.getRowData(rowIndex) == undefined) {
                    requestNeeded = true;
                    break;
                }
                firstRow--;
            }
        }
        if(!requestNeeded) {
            return;
        }
        return [firstRow, firstRow+desiredRowCount];
    },

    /**
     * Retrieve some rows from the server which are likely to be useful given
     * the current state of this ScrollingWidget.  Update the ScrollModel when
     * the results arrive.
     *
     * @param scrollingDown: A flag indicating whether we are scrolling down,
     * and so whether the requested rows should be below the current position
     * or not.
     *
     * @return: A Deferred which fires with an Array of rows retrieve when
     * the update has finished.
     */
    function _getSomeRows(self, scrollingDown) {
        var range = self._calculateDesiredRowRange(scrollingDown);

        /* do we have the rows we need ? */
        if (!range) {
            return Divmod.Defer.succeed([]);
        }

        return self.requestRowRange.apply(self, range);
    },

    /**
     * Remove all row nodes, including placeholder nodes from the scrolltable
     * viewport node.  Also empty the model.
     */
    function empty(self) {
        var sviewport = self._scrollViewport;

        /*
         * Removing children from the viewport will probably cause it to
         * scroll around a bit.  We care not about any of those events, so
         * ignore them temporarily.
         */
        var onscroll = sviewport.onscroll;
        sviewport.onscroll = undefined;
        while (sviewport.firstChild) {
            sviewport.removeChild(sviewport.firstChild);
        }
        sviewport.onscroll = onscroll;

        /*
         * Make everything as new again.
         */
        self.lastScrollPos = 0;
        self.model.empty();
        self.placeholderModel.empty();
    },

    /**
     * Remove all rows from scrolltable, as well as our cache of
     * fetched/unfetched rows, scroll the table to the top, and
     * refill it.
     */
    function emptyAndRefill(self) {
        self.empty();
        return self.refill();
    },

    /**
     * Request the current size (number of rows) from the server
     */
    function getSize(self) {
        return self.callRemote("requestCurrentSize");
    },

    /**
     * Refill an empty scrolltable by asking for more rows, creating
     * placeholder rows and adding a screenful of fresh rows.
     *
     * @return: Deferred firing with pair of [total size, fetched rows]
     */
    function refill(self) {
        var range = self._calculateDesiredRowRange(true);
        if(range[0] != 0) {
            throw new Error("expected first needed row to have index 0");
        }

        var result = Divmod.Defer.gatherResults(
                        [self.getSize(),
                         self.getRows(0, range[1])]);

        return result.addCallback(
                function(response) {
                    self.padViewportWithPlaceholderRow(response[0]);
                    self.model.setTotalRowCount(response[0]);
                    self._storeRows.apply(self, range.concat([response[1]]));
                    return response;
                });
    },

    /**
     * Tell the server to change the sort key for this table.
     *
     * @type columnName: string
     * @param columnName: The name of the new column by which to sort.
     */
    function resort(self, columnName) {
        var result = self.callRemote("resort", columnName);
        result.addCallback(function(isAscendingNow) {
                self._setSortHeader(columnName, isAscendingNow);
                self.emptyAndRefill();
            });
        return result;
    },

    /**
     * Make a placeholder row
     *
     * @type height: integer
     * @param height: the height of the placeholder row
     *
     * @rtype: node
     */
    function makePlaceholderRowElement(self, height) {
        return MochiKit.DOM.TR(
                {"class": "placeholder-scroll-row",
                 "style": "height: " + height + "px"},
                MochiKit.DOM.TD({"class": "placeholder-cell"}));
    },

    /**
     * Update the view to reflect a new sort state.
     *
     * @param currentSortColumn: The name of the column by which the scrolling
     * widget's rows are now ordered, or null if there isn't a current sort
     * column
     *
     * @param isAscendingNow: A flag indicating whether the sort is currently
     * ascending.
     *
     */
    function _setSortHeader(self, currentSortColumn, isAscendingNow) {
        self.currentSort = currentSortColumn;
        self.ascending = isAscendingNow;

        if(currentSortColumn == null) {
            return;
        }

        /*
         * Remove the sort direction arrow from whichever header has it.
         */
        for (var j = 0; j < self._headerNodes.length; j++) {
            while(1 < self._headerNodes[j].childNodes.length) {
                self._headerNodes[j].removeChild(self._headerNodes[j].lastChild);
            }
        }

        /*
         * Put the appropriate sort direction arrow on whichever header
         * corresponds to the new current sort column.
         */
        var c;
        if(isAscendingNow) {
            c = '\u2191'; // up arrow
        } else {
            c = '\u2193'; // down arrow
        }
        var sortOffset = self._columnOffsets[currentSortColumn];
        var sortHeader = self._headerNodes[sortOffset];
        if (sortHeader != undefined) {
            var sortNode = MochiKit.DOM.SPAN({"class": "sort-arrow"}, c);
            sortHeader.appendChild(sortNode);
        }
    },

    /**
     * Called in response to only user-initiated scroll events.
     */
    function onScroll(self) {
        self.scrolled();
    },

    /**
     * Respond to an event which may have caused to become visible rows for
     * which we do not data locally cached.  Retrieve some data, maybe, if
     * necessary.
     */
    function scrolled(self) {
        var result = Divmod.Defer.Deferred();
        self._scrollDeferreds.push(result);

        var proposedTimeout = 250;
        var scrollingDown = self.lastScrollPos < self._scrollViewport.scrollTop;
        self.lastScrollPos = self._scrollViewport.scrollTop;

        if (self._requestWaiting) {
            self._moreAfterRequest = true;
            return result;
        }

        if (self._rowTimeout !== null) {
            clearTimeout(self._rowTimeout);
        }

        function finishDeferreds(result) {
            var scrollDeferreds = self._scrollDeferreds;
            self._scrollDeferreds = [];
            for (var i = 0; i < scrollDeferreds.length; ++i) {
                scrollDeferreds[i].callback(result);
            }
        }

        self._rowTimeout = setTimeout(
            function () {
                self._rowTimeout = null;
                self._requestWaiting = true;
                try {
                    var rowsDeferred = self._getSomeRows(scrollingDown);
                } catch (err) {
                    finishDeferreds(Divmod.Defer.Failure(err));
                    return;
                }
                rowsDeferred.addBoth(
                    function resetRequestWaiting(passthrough) {
                        self._requestWaiting = false;
                        return passthrough;
                    });
                rowsDeferred.addCallback(
                    function rowsReceived(rows) {
                        self._requestWaiting = false;
                        if (self._moreAfterRequest) {
                            self._moreAfterRequest = false;
                            self.scrolled();
                        } else {
                            finishDeferreds(null);
                        }
                        self.cbRowsFetched(rows.length);
                    });
                rowsDeferred.addErrback(
                    function rowsError(err) {
                        finishDeferreds(err);
                    });
            },
            proposedTimeout);
        return result;
    },

    /**
     * Callback for some event.  Don't implement this.
     */
    function cbRowsFetched(self) {
    }
    );

/**
 * ScrollingWidget subclass which adjusts its height each time the viewport is
 * refilled, setting it to the same height as the total height of all
 * available rows, up until C{self.maxRows}.  Example where maxRows is 3 and
 * row height is 10px:
 *
 * if there is 1 row in the model:
 *
 * |HEADERS HEADERS HEADERS|
 * -------------------------
 * |THE ONLY ROW           | <- 10px, no scrollbar
 *
 * 2 rows in the model:
 *
 * |HEADERS HEADERS HEADERS|
 * -------------------------
 * |THE FIRST ROW          | \__ 10px + 10px = 20px, no scrollbar
 * |THE SECOND ROW         | /
 *
 * 3 or more rows in the model (>= maxRows):
 *
 * |HEADERS HEADERS HEADERS|
 * -------------------------
 * | THE FIRST ROW       | | \
 * | THE SECOND ROW      | |  >- 10px + 10px + 10px = 30px, scrollbar
 * | THE THIRD ROW       | | /
 *          |
 *         \|/
 *  rest of the rows obscured
 */

Mantissa.ScrollTable.FlexHeightScrollingWidget = Mantissa.ScrollTable.ScrollingWidget.subclass('Mantissa.ScrollingWidget.FlexHeightScrollingWidget');
Mantissa.ScrollTable.FlexHeightScrollingWidget.methods(
    /**
     * Override default implementation so we can store C{maxRows} and set the
     * initial height once initialization is complete
     */
    function __init__(self, node, metadata, maxRows/*=undefined*/) {
        Mantissa.ScrollTable.FlexHeightScrollingWidget.upcall(self, "__init__", node, metadata);
        self.maxRows = maxRows;
        self.initializationDeferred.addCallback(
            function(passThrough) {
                self._setScrollViewportHeight();
                return passThrough;
            });
    },

    /**
     * Helper method which sets the height of the scrolltable so that it's
     * tall enough to accomodate (without a scrollbar) any number of rows <=
     * C{self.maxRows}
     */
    function _setScrollViewportHeight(self) {
        var rowCount = self.model.totalRowCount();
        if(self.maxRows) {
            rowCount = Math.min(rowCount, self.maxRows);
        }
        self._scrollViewport.style.height = (rowCount * self._rowHeight) + "px";
    },

    /**
     * Override default implementation to never request less than
     * C{self.maxRows} if we're starting from the zeroth row (e.g. after the
     * scrolltable has been emptied or when we make the initial fetch)
     */
    function _calculateDesiredRowRange(self, scrollingDown) {
        var res = Mantissa.ScrollTable.FlexHeightScrollingWidget.upcall(
                    self, "_calculateDesiredRowRange", scrollingDown);
        if(res && res[0] == 0 && res[1] < self.maxRows-1) {
            res[1] = self.maxRows-1;
        }
        return res;
    },

    /**
     * Override default implementation so that we can adjust the height of the
     * scrolltable after the scrolltable has been refilled
     */
    function refill(self) {
        var D = Mantissa.ScrollTable.FlexHeightScrollingWidget.upcall(self, "refill");
        return D.addCallback(
            function(passThrough) {
                self._setScrollViewportHeight();
                return passThrough;
            });
    });


/// CUT HERE: there is too much stuff in this file, but the latency involved
/// in requesting JavaScript files from Mantissa is getting to be
/// excruciating, and every new file adds to that.  Really this should be
/// dealt with in some kind of smooshing-stuff-together layer inside Nevow,
/// but for the time being we're not going to make things worse.  Put this
/// into a new file once all the JS can be efficiently served up as one
/// monolithic, compressed pile.


Mantissa.ScrollTable.Column = Divmod.Class.subclass(
    'Mantissa.ScrollTable.Column');

/**
 * Describes a type of column.
 *
 * @ivar name: a String giving the name of the row property by which rows are
 * sorted.
 */
Mantissa.ScrollTable.Column.methods(
    /**
     * Create a Column with a given name.
     *
     * @param name: the name, or attribute ID, of this column within a
     * scrolltable.
     */
    function __init__(self, name) {
        self.name = name;
    },

    /**
     * Map a column value to a number.  Abstract: implement in subclasses.
     *
     * @param value: a column value depending on the type of this column, as
     * returned by this Column's extractValue method.
     *
     * @rtype: number
     */
    function toNumber(self, value) {
        throw Divmod.Error(self.__class__.__name__ + ".toNumber not implemented");
    },

    /**
     * Map a number to a column value.  Abstract: implement in subclasses.
     *
     * @param ordinal: a number returned by my toNumber method.
     *
     * @rtype: Dependent on the value of this column; same as extractValue.
     */
    function fromNumber(self, ordinal) {
        throw Divmod.Error(self.__class__.__name__ + ".fromNumber not implemented");
    },

    /**
     * Return a representative value object for this column type.  Abstract:
     * implement in subclasses.
     *
     * @rtype: Dependent on the value of this column; same as extractValue.
     */
    function fakeValue(self) {
        throw new Error("fakeValue not implemented");
    },

    /**
     * Extract the value of this column from a row.
     *
     * @param row: An object representing a row within a RegionModel, returned
     * by dataAsRow.
     *
     * @return: a value dependent on the type of this column.
     */
    function extractValue(self, row) {
        return row[self.name];
    },

    /**
     * Extract the key to sort a row by from the row.  By default, this is the
     * same as extractValue, but subclasses may override it to produce sort
     * ordering that differs from the normal JavaScript ordering of the
     * visible data.
     *
     * @param row: An object representing a row within a RegionModel, returned
     * by dataAsRow.
     *
     * @return: a value dependent on the type of this column.
     */
    function extractSortKey(self, row) {
        return self.extractValue(row);
    },

    /**
     * Construct some DOM objects to represent this value in a scrolltable.
     */
    function valueToDOM(self, columnValue) {
        return document.createTextNode(columnValue.toString());
    },

    /**
     * Estimate the value which would appear at a relative position between
     * between two other values, based on the type of this column.
     *
     * @param value1: The first value.
     *
     * @param value2: The second value.
     *
     * @param relativePositionBetween: An indication of the relative closeness
     * to each value.  A value of close to 0.0 indicates that the result
     * should be close to 0.0, a value close to 1.0 indicates the result
     * should be close to value2. A value of 0.5 indicates the result should
     * be exactly half-way between the two given values.
     *
     * @type relativePositionBetween: C{Number} (float between 0 and 1).
     */
    function estimateQueryValue(self, value1, value2, relativePositionBetween) {
        value1 = self.toNumber(value1);
        value2 = self.toNumber(value2);
        return self.fromNumber(
            value1 + (relativePositionBetween * (value2 - value1)));
    });


Mantissa.ScrollTable.WidgetColumn = Mantissa.ScrollTable.Column.subclass(
    'Mantissa.ScrollTable.WidgetColumn');

Mantissa.ScrollTable.WidgetColumn.FAKE_VALUE =
    "Mantissa.ScrollTable.WidgetColumn.FAKE_VALUE";
/**
 * A column that holds Widget which are children of the table widget.
 */
Mantissa.ScrollTable.WidgetColumn.methods(
    /**
     * Override the base implementation to return
     * L{Mantissa.ScrollTable.WidgetColumn.FAKE_VALUE} so we can later check
     * whether it is passed back into L{valueToDOM}.
     */
     function fakeValue(self) {
         return self.FAKE_VALUE;
     },

    /**
     * Override the base implementation to return an empty node which will
     * later contain the node of the widget constructed out of C{widgetInfo}.
     */
    function valueToDOM(self, widgetInfo, tableWidget) {
        var resultNode = document.createElement('div');
        if (widgetInfo !== self.FAKE_VALUE) {
            var addChildDeferred = tableWidget.addChildWidgetFromWidgetInfo(
                widgetInfo);
            addChildDeferred.addCallback(
                function(widget) {
                    resultNode.appendChild(widget.node);
                });
        }
        return resultNode;
    });

Mantissa.ScrollTable.IntegerColumn = Mantissa.ScrollTable.Column.subclass(
    'Mantissa.ScrollTable.IntegerColumn');

/**
 * A column which can hold integers.
 *
 * @ivar name: a String giving the name of the row property by which rows are
 * sorted.
 */
Mantissa.ScrollTable.IntegerColumn.methods(
    /**
     * Override base implementation to pass through the underlying value.
     */
    function toNumber(self, value) {
        return value;
    },

    /**
     * Return a representative integer.
     */
    function fakeValue(self) {
        return 1234;
    },

    /**
     * Override base implementation to leave the number as-is.
     */
    function fromNumber(self, ordinal) {
        return Math.floor(ordinal);
    });


Mantissa.ScrollTable.TextColumn = Mantissa.ScrollTable.Column.subclass(
    'Mantissa.ScrollTable.TextColumn');

/**
 * A column which can hold a string, but cannot (yet) be sorted.
 *
 * @ivar name: a String giving the name of the row property by which rows are
 * sorted.
 */
Mantissa.ScrollTable.TextColumn.methods(
    /**
     * Override the base implementation to do simple case-conversion (using
     * sqlite's naive algorithm) on the result of L{extractSortKey} to
     * correspond to Axiom's case-insensitive sort ordering.
     */
     function extractSortKey(self, row) {
         var input = self.extractValue(row);
         return self._sqliteLowerCase(input);
     },

     /**
      * This method replicates the naive, locale-independent case conversion
      * algorithm implemented by sqlite, to match the sorting that axiom will
      * do.
      *
      * @param input: a string.
      *
      * @return: a string, with the ASCII upper case letters converted to
      * ASCII lower case according to en_US case-conversion rules.
      */
     function _sqliteLowerCase(self, input) {
         var result = '';
         for (var i = 0; i < input.length; ++i) {
             var each = input[i];
             if (each >= 'A' && each <= 'Z') {
                 result += each.toLowerCase();
             } else {
                 result += each;
             }
         }
         return result;
     },

    /**
     * Estimate the string to query for based on two values and the distance
     * between them.  For example, half way between "Jim Jones" and "Jim
     * Zzzxyx" is "Jim R".
     *
     * @param value1: a string
     *
     * @param value2: a string
     *
     * @param relativePositionBetween: a floating point number between 0.0 and 1.0.
     */
     function estimateQueryValue(self, value1, value2, relativePositionBetween) {
         var value1 = self._sqliteLowerCase(value1);
         var value2 = self._sqliteLowerCase(value2);
         // Make sure that value1 is always the lesser value, or shorter value
         // in the case where one is a prefix of the other, to simplify later
         // code.
         if (value1 > value2) {
             var swap;
             swap = value2;
             value2 = value1;
             value1 = swap;
             relativePositionBetween = 1 - relativePositionBetween;
         }
         var i = 0;

         for (i; i < value1.length; i++) {
             if (value1[i] !== value2[i]) {
                 break;
             }
         }

         // Is one string a prefix of the other?
         if (i === value1.length) {
             // In that case, lengthen it by an appropriate amount.
             var diffChars = (value2.length - value1.length);
             var numChars = Math.ceil(diffChars * relativePositionBetween);
             if (numChars === diffChars) {
                 numChars -= 1;
             }
             return value2.substring(0, value1.length + numChars);
         }

         // XXX TODO: If you have 'joe' and 'joe smith', this leaves us in a
         // bad state.  We should simply return 'joe' in that case, or perhaps
         // 'joe\x01'.

         /**
          * Convert the common location in one of the inputs to a character
          * code, skipping the capital letter range.
          */
         var skipUp = function (x) {
             var charval = x.charCodeAt(i);
             if (charval < 'Z'.charCodeAt(0)) {
                 return charval + 26;
             }
             return charval;
         };

         /**
          * Convert a character code which has skipped the uppercase range to
          * a lower case character.
          */
         var skipDown = function (y) {
             if (y <= 'Z'.charCodeAt(0)) {
                 y -= 26;
             }
             return String.fromCharCode(y);
         };

         var c1 = skipUp(value1);
         var c2 = skipUp(value2);
         var distance = c2 - c1;

         if (Math.abs(distance) === 1) {
             return value1+'\u0001';
         }

         var targetCode = c1 + (relativePositionBetween * distance);
         var targetChar = skipDown(targetCode);

         var result = (value1.substring(0, i) + targetChar);
         return result;
     },

    /**
     * Return a representative string.
     */
    function fakeValue(self) {
        return "short";
    });


Mantissa.ScrollTable.BooleanColumn = Mantissa.ScrollTable.Column.subclass(
    'Mantissa.ScrollTable.BooleanColumn');

/**
 * A column which can hold a boolean, but cannot be sorted.
 *
 * @ivar name: a String giving the name of the row property by which rows are
 * sorted.
 */
Mantissa.ScrollTable.BooleanColumn.methods(
    /**
     * Return a representative boolean.
     */
    function fakeValue(self) {
        return true;
    });

Mantissa.ScrollTable.TimestampColumn = Mantissa.ScrollTable.IntegerColumn.subclass(
    'Mantissa.ScrollTable.TimestampColumn');

/**
 * A column which can hold timestamps.
 *
 * @ivar name: a String giving the name of the row property by which rows are
 * sorted.
 */
Mantissa.ScrollTable.TimestampColumn.methods(
    /**
     * Return a representative Date object.
     */
    function fakeValue(self) {
        return new Date();
    },

    /**
     * Construct a C{Date} object from the column value.
     */
    function extractValue(self, rowData) {
        return new Date(
            Mantissa.ScrollTable.TimestampColumn.upcall(
                self, 'extractValue', rowData)
            * 1000);
    },

    /*
     * Convert a C{Date} object into a C{Number} via C{Date.getTime}.
     */
    function toNumber(self, columnValue) {
        return columnValue.getTime();
    },

    /**
     * Convert a C{Number} into something suitable for sending to the server.
     */
    function fromNumber(self, number) {
        // XXX wonky as hell, because we are actually going to send this to
        // the server, and the server thinks that this column is full of
        // floats
        return number / 1000;
    },

    /**
     * Format the timestamp as a human-readable string.
     */
    function valueToDOM(self, columnValue) {
        return Mantissa.ScrollTable.TimestampColumn.upcall(
            self, 'valueToDOM', columnValue.toUTCString());
    });

Mantissa.ScrollTable.RowRegion = Divmod.Class.subclass(
    'Mantissa.ScrollTable.RowRegion');

/**
 * Represent a range of rows at a particular offset.
 *
 * @ivar regionModel: a reference to a L{RegionModel} that this region
 * participates in.
 *
 * @ivar offset: an integer giving the location of the rows in this range in a
 * larger container.
 *
 * @ivar viewPeer: a DOMRegionView instance which deals with rendering this
 * region into to DOM nodes.
 *
 * @ivar rows: an array of objects representing row data.
 */
Mantissa.ScrollTable.RowRegion.methods(
    /**
     * Create a RowRegion from a given region model, at a given offset, with
     * the given data from the server.  Also create its view peer.
     */
    function __init__(self, regionModel, offset, data) {
        if (data.length == 0) {
            throw new Error("Invalid empty row array passed to RowRegion");
        } else if (offset < 0) {
            throw new Error("Invalid negative offset passed to RowRegion");
        }
        self.regionModel = regionModel;
        self._offset = offset;
        self.rows = [];
        for (var i=0; i<data.length; i++) {
            var dataElement = data[i];
            var rowElement = regionModel.dataAsRow(dataElement);
            self.rows.push(dataElement);
        }
        self.viewPeer = self.regionModel.view.createRegionView(self);
    },

    /**
     * Get the region immediately preceding this one, if such a region exists.
     *
     * @rtype: L{Mantissa.ScrollTable.RowRegion} or C{undefined}.
     */
    function previousRegion(self) {
        var regions = self.regionModel._regions;
        var eachRegion;
        var lastRegion = undefined;
        for (var i = 0; i < regions.length; i++) {
            eachRegion = regions[i];
            if (self.followsRegion(eachRegion)) {
                lastRegion = eachRegion;
            } else {
                return lastRegion;
            }
        }
        return lastRegion;
    },

    /**
     * Remove a row from this region.
     *
     * @param offset: the offset within the entire data set (i.e. this
     * RowRegion's RegionModel).
     */
    function removeRegionRow(self, offset) {
        if (self.rows.length === 1) {
            self.destroy();
        } else {
            var innerOffset = offset - self.firstOffset();
            self.rows.splice(innerOffset, 1);
            self.viewPeer.removeViewRow(innerOffset);
        }
    },

    /**
     * Determine if this RowRegion's values come later than the given
     * RowRegion's values according to the current sort column and sort order.
     */
    function followsRegion(self, otherRegion) {
        if (self.regionModel._sortAscending) {
            return (otherRegion.lastValue() < self.firstValue());
        } else {
            return (otherRegion.lastValue() > self.firstValue());
        }
    },

    /**
     * Remove this region from its model and eliminate its view peer from its
     * view.
     */

    function destroy(self) {
        for (var i = 0; i < self.regionModel._regions.length; i++) {
            if (self.regionModel._regions[i] === self) {
                self.regionModel._regions.splice(i, 1);
                break;
            }
        }
        self.viewPeer.destroy();
    },

    /**
     * Return a string representation that describes this region to aid with
     * debugging.
     */
    function toString(self) {
        return 'RowRegion(' + self._offset + ', ' + self.rows.toString() + ')';
    },

    /**
     * Helper method to pull a value out from a row object.  The type depends
     * on the type of the sort column.
     */
    function _extractValue(self, row) {
        return self.regionModel.sortColumn.extractSortKey(row);
    },

    /**
     * Return the current sort column value for the row for the lowest
     * offset in this region. The type depends on the column type.
     */
    function firstValue(self) {
        return self._extractValue(self.rows[0]);
    },

    /**
     * Return the current sort column value for the highest offset in this
     * region.  The type depends on the column type.
     */
    function lastValue(self) {
        return self._extractValue(self.rows[self.rows.length - 1]);
    },

    /**
     * Return the current sort column for the row with the lowest sort value
     * in this region.  The type depends on the column type.
     */
    function lowestValue(self) {
        if (self.regionModel._sortAscending) {
            return self.firstValue();
        } else {
            return self.lastValue();
        }
    },

    /**
     * Return the current sort column for the row with the highest sort value
     * in this region.  The type depends on the column type.
     */
    function highestValue(self) {
        if (self.regionModel._sortAscending) {
            return self.lastValue();
        } else {
            return self.firstValue();
        }
    },

    /**
     * Retrieve the first offset within this region.
     */
    function firstOffset(self) {
        return self._offset;
    },

    /**
     * Retrieve the last offset within this region.
     */
    function lastOffset(self) {
        return self._offset + self.rows.length - 1;
    },

    /**
     * Determine whether the given sort-column value occurs within this
     * region.
     *
     * @param value: a value of the type described by this region's model's
     * sort column.
     *
     * @return: a boolean; true if the value is present within the range
     * defined by this region, false otherwise.
     */
    function overlapsValue(self, value) {
        return ((self.lowestValue() <= value) &&
                (value <= self.highestValue()));
    },

    /**
     * Compare this region to an offset, and return a value representing how
     * it relates to that offset.
     *
     * @param offset: an offset to compare against this region.
     *
     * @return: an integer, 1 to indicate that offset occurs before this
     * region, 0 to indicate that offset occurs within this region (i.e. it
     * overlaps it), and -1 to indicate that the offset occurs after this
     * region.
     */
    function compareToOffset(self, offset) {
        if (offset < self._offset) {
            return 1;
        } else if ((self._offset <= offset) &&
                   (offset <= (self._offset + self.rows.length - 1))) {
            return 0;
        } else {
            return -1;
        }
    },

    /**
     * Acquire the data from another region which is contiguous with the end
     * of this region.
     *
     * @param region: another L{RowRegion}, one which overlaps the end of this
     * region.  By the end of this method, this parameter will be removed from
     * the RegionModel, while 'self' will remain with additional rows.
     *
     * @throws: L{Error} if the supplied region does not have any rows which
     * are also present in this region.
     *
     * @return: null
     */
    function coalesceAtMyEnd(self, region) {
        var rowCount = self.rows.length;
        for (var j = 0; j < rowCount; ++j) {
            if (self.rows[j].exactlyEqualTo(region.rows[0])) {
                // FOUND THE OVERLAP AT J
                var overlappingRows = rowCount - j;
                if (overlappingRows < region.rows.length) {
                    if (self.rows[self.rows.length-1].__TEMPORARY__) {
                        // Back up!
                        overlappingRows--;
                        self.rows.pop();
                        // This next line needs tests.
                        self.viewPeer.removeViewRow(self.rows.length);
                    }
                    self.rows.push.apply(self.rows,
                                         region.rows.slice(overlappingRows));
                    self.viewPeer.mergeWithRegionView(
                        region.viewPeer, overlappingRows);
                } else {
                    // There is no new information in this new region.  Just
                    // clean up its view portion and don't bother!
                    region.viewPeer.destroy();
                }
                return;
            }
        }
        throw new Error("attempted to coalesce region with no overlap");
    },

    /**
     * Adjust the offset of this region, moving it by the specified amount.
     */
    function adjustOffset(self, amount) {
        self._offset += amount;
        self.viewPeer.refreshViewOffset();
    });


Mantissa.ScrollTable.OffsetOutOfBounds = Divmod.Error.subclass(
    'Mantissa.ScrollTable.OffsetOutOfBounds');

/**
 * Error raised when the view exposes an invalid area.
 */
Mantissa.ScrollTable.RegionModel = Mantissa.ScrollTable._ModelBase.subclass(
    'Mantissa.ScrollTable.RegionModel');

/**
 * Model for interacting with the server using inequality-based queries.
 *
 * @ivar _rows: An C{Array} of C{Mantissa.ScrollTable.RowRegion} objects which
 * contains all locally available row data.
 */
Mantissa.ScrollTable.RegionModel.methods(
    /**
     * Create a RegionModel with a RegionModelServer.
     *
     * @param server: an IRegionModelServer provider.
     *
     * @param sortColumn: An L{Mantissa.ScrollTable.Column} instance.
     */
    function __init__(self, view, server, sortColumn,
                      /*optional: default true*/ sortAscending) {
        Mantissa.ScrollTable.RegionModel.upcall(self, "__init__");
        self.server = server;
        self.sortColumn = sortColumn;
        self.view = view;
        self._regions = [];
        // XXX needs to scale based on table height; this should be able to
        // scale at runtime just fine though
        self._pagesize = 2;
        self._initialized = false;
        if (sortAscending === undefined) {
            // By default, sort ascending; don't accept just a random truth value.
            sortAscending = true;
        }
        self._sortAscending = sortAscending;
    },

    ////// Compatibility methods for older ScrollTable API

    // These methods aren't _necessarily_ bad, but the design was copied
    // verbatim from the older ScrollModel.  They are only around as long as
    // the existing Mantissa / Quotient views need them.

    /**
     * Retrieve an array of indices for which local data is available.
     */
    function getRowIndices(self) {
        var region, firstOffset, lastOffset;
        var indices = [];
        for (var i = 0; i < self._regions.length; i++) {
            region = self._regions[i];
            firstOffset = region.firstOffset();
            lastOffset = region.lastOffset();
            for (var j = firstOffset; j <= lastOffset; j++) {
                indices.push(j);
            }
        }
        return indices;
    },

    /**
     * Remove a row at a given index.
     *
     * @param index: an integer describing the index that the offset is at.
     */
    function removeRow(self, index) {
        var reg = self._regionContainingOffset(index);
        reg.removeRegionRow(index);
    },

    /**
     * Retrieve the row data for the row at the given index.
     *
     * @type index: integer
     *
     * @rtype: object
     * @return: The structured data associated with the row at the given index.
     *
     * @throw Divmod.IndexError: Thrown if the given index is out of bounds.
     */
    function getRowData(self, index) {
        var lastRegion = self._regions[self._regions.length - 1];
        if (index < 0 || lastRegion === undefined || lastRegion.lastOffset() < index) {
            throw Divmod.IndexError("Specified index (" + index + ") out of bounds in getRowData.");
        }
        var region;
        for (var i = 0; i < self._regions.length; i++) {
            region = self._regions[i];
            if (region.firstOffset() <= index && index <= region.lastOffset()) {
                return region.rows[index - region.firstOffset()];
            }
        }
        return undefined; // ha
    },

    /**
     * Retrieve the index for the row data associated with the given webID.
     *
     * @type webID: string
     *
     * @rtype: integer
     *
     * @throw NoSuchWebID: Thrown if the given webID corresponds to no row in
     * the model.
     */
    function findIndex(self, webID) {
        var region;
        for (var i = 0; i < self._regions.length; i++) {
            region = self._regions[i];
            for (var j = 0; j < region.rows.length; j++) {
                if (region.rows[j].__id__ == webID) {
                    return j + region.firstOffset();
                }
            }
        }
        throw Mantissa.ScrollTable.NoSuchWebID(webID);
    },

    /**
     * @rtype: integer
     * @return: The number of rows in the model which we have already fetched.
     */
    function rowCount(self) {
        /* note that the previous implementation of this method included rows
           that hadn't been retrieved yet */
        var count = 0;
        for (var i = 0; i < self._regions.length; i++) {
            count += self._regions[i].rows.length;
        }
        return count;
    },

    /**
     * Completely clear the data out of this RegionModel; re-set it to the
     * state it was in when it was originally displayed.
     */

    function empty(self) {
        while (self._regions.length !== 0) {
            var eachRegion = self._regions[0];
            // Do something with it
            eachRegion.destroy();
        }
    },


    ////// End Compatibility Section

    /**
     * This method is a notification from the view that a set of rows has been
     * exposed to the user and should now be loaded.
     *
     * @param offset: a non-negative integer, the index of the first row
     * exposed.
     *
     * @return: a Deferred which will fire when all the requests required to
     * satisfy the exposure at the supplied offset have been satisfied.
     *
     * @throw Mantissa.ScrollTable.OffsetOutOfBounds: If C{offset} is less than
     * zero or greater than the maximum known offset.
     */
    function expose(self, offset) {
        if (offset < 0) {
            throw Mantissa.ScrollTable.OffsetOutOfBounds();
        }
        var madeRequest = null;
        if (!self._initialized) {
            madeRequest = self._initialize().addCallback(function () {
                /* We haven't been initialized.  Issue the expose() call again
                 * once the assumptions about our model have been verified.
                 */
                return self.expose(offset);
            });
        } else {
            /* Did I expose any rows which might actually need requesting?
             * First, let's look for a row which contains the offset I'm
             * looking for.
             */
            var startRegion = self._regionContainingOffset(offset);
            if (startRegion !== null) {
                // OK, is the region long enough to cover my end as well?
                var alreadyThere = ((startRegion.firstOffset() - offset) +
                                    startRegion.rows.length);
                if (self._pagesize > alreadyThere) {
                    // ask for some rows after the end of that region.
                    var lastRow = startRegion.rows[
                        startRegion.rows.length - 1];
                    madeRequest = self.rowsFollowingRow(
                        lastRow).addCallback(
                            function (rows) {
                                self.insertRowData(offset, rows);
                            });
                }
            } else {
                /* Is there a region *exactly* adjacent to the area just
                 * exposed which isn't visible?
                 */
                var adjacentPreviousRegion = self._regionBefore(offset);
                if (adjacentPreviousRegion !== null &&
                    adjacentPreviousRegion.lastOffset() === (offset-1)) {
                    /* Oh goody!  Just grab the contiguous rows.
                     */
                    var adjacentPreviousRow = adjacentPreviousRegion.rows[
                        adjacentPreviousRegion.rows.length - 1];
                    madeRequest = self.rowsFollowingRow(
                        adjacentPreviousRow,
                        /* Expose is telling us that we need to fill up
                         * pagesize rows worth of data on the screen, but one
                         * of the rows is _off_ the screen, specifically the
                         * contiguous row that we selected before.  Ask the
                         * server for one additional row to compensate.
                         */
                        true).addCallback(
                            function (rows) {
                                self.insertRowData(offset - 1, rows);
                            });
                } else {
                    /* We've exposed an area that isn't contiguous with
                     * another region.  We need to request a new group of rows
                     * based on an estimate of the value being identified.
                     */
                    var evao = self.estimateValueAtOffset(offset);
                    madeRequest = self.rowsFollowingValue(
                        evao).addCallback(function (rows) {
                            var pair = self.insertRowData(offset, rows);
                            var newDataCount = pair[0];
                            var newRegion = pair[1];
                            if (newDataCount !== 0) {
                                return;
                            }
                            // There's no data available.  We'll issue a
                            // second request to actually get some.

                            // XXX TODO: if we've requested data where there
                            // is none (past the end of the region, for
                            // example) we should deal with that differently
                            // than some data coming back and no rows being
                            // inserted.

                            // if (newRegion === null) {
                            //     return;
                            // }

                            return self.rowsPrecedingRow(
                                newRegion.rows[0], true
                                ).addCallback(function (moreRows) {
                                    self.insertRowData(offset, moreRows);
                                });
                        });
                }
            }
        }
        if (madeRequest === null) {
            madeRequest = Divmod.Defer.Deferred();
            madeRequest.callback(null);
        }
        return madeRequest;
    },

    /**
     * Return a set of rows including the given row by requesting from our
     * server whose offsets immediately follow that of the given existing row.
     * The offsets of the given rows returned will be increasing according to
     * the current sort order.
     *
     * @param row: a row object retrieved from a region's 'rows' attribute.
     *
     * @param exactlyAdjacent: a boolean, indicating whether the user is
     * looking at the exactly-adjacent area to the given row.  If true, an
     * additional row will be requested in order to ensure that a full page's
     * worth of rows arrive; otherwise, the usual behavior is that
     * (self._pagesize - 1) rows will be retrieved.
     */
    function rowsFollowingRow(self, row, /* optional*/ exactlyAdjacent) {
        return self._rowsRelatedToRow(row, exactlyAdjacent, false);
    },

    /**
     * Return a set of rows including the given row by requesting from our
     * server whose offsets immediately precede that of the given existing row
     * row.  The offsets of the given rows returned will be increasing
     * according to the current sort order.
     *
     * @param row: a row object retrieved from a region's 'rows' attribute.
     *
     * @param exactlyAdjacent: a boolean, indicating whether the user is
     * looking at the exactly-adjacent area to the given row.  If true, an
     * additional row will be requested in order to ensure that a full page's
     * worth of rows arrive; otherwise, the usual behavior is that
     * (self._pagesize - 1) rows will be retrieved.
     */
    function rowsPrecedingRow(self, row, /* optional */ exactlyAdjacent) {
        return self._rowsRelatedToRow(row, exactlyAdjacent, true);
    },

    /**
     * Common, underlying implementation of rowsFollowingRow and
     * rowsPrecedingRow.
     */
    function _rowsRelatedToRow(self, row, exactlyAdjacent, wantPreceding) {
        var result = null;
        var pagesize = self._pagesize;
        if (!exactlyAdjacent) {
            pagesize--;
        }
        var serverRow = {
          __id__: row.__id__,
          __TEMPORARY__: true,
          toString: function () {
                return '<fake server row '+this.__id__+'>';
            }
        };
        serverRow[self.sortColumn.name] = row[self.sortColumn.name];
        if (self._sortAscending) {
            if (wantPreceding) {
                result = self.server.rowsBeforeRow(serverRow, pagesize);
            } else {
                result = self.server.rowsAfterRow(serverRow, pagesize);
            }
        } else {
            if (wantPreceding) {
                result = self.server.rowsAfterRow(serverRow, pagesize);
            } else {
                result = self.server.rowsBeforeRow(serverRow, pagesize);
            }
        }
        if (!self._sortAscending) {
            result.addCallback(function (rows) {
                rows.reverse();
                return rows;
            });
        }
        result.addCallback(function (data) {
                if (wantPreceding) {
                    data.splice(data.length, 0, serverRow);
                } else {
                    data.splice(0, 0, serverRow);
                }
                return data;
            });
        return result;
    },

    /**
     * Return a set of rows from our server including and following the given
     * value.  The rows returned depends on the current sort order.
     */
    function rowsFollowingValue(self, value) {
        var result = null;
        if (self._sortAscending) {
            return self.server.rowsAfterValue(value, self._pagesize);
        } else {
            return self.server.rowsBeforeValue(value, self._pagesize
                ).addCallback(function (result) {
                    return result.reverse();
                });
        }
    },

    /**
     * Estimate the value at a given offset based on the values in the regions
     * before and after it.
     *
     * @param offset: a row offset.
     * @return: a scroll column value.
     */
    function estimateValueAtOffset(self, offset) {
        var r1 = self._regionBefore(offset);
        var r2 = self._regionAfter(offset);
        var v1 = r1.lastValue();
        var v2 = r2.firstValue();
        var blankOffsets = r2.firstOffset() - r1.lastOffset();
        return self.sortColumn.estimateQueryValue(
            v1, v2, (offset - r1.lastOffset()) / blankOffsets);
    },

    function _regionBefore(self, offset) {
        var lastRegionSeen = null;
        for (var i = 0; i < self._regions.length; i++) {
            var region = self._regions[i];
            var cmp = region.compareToOffset(offset);
            if (cmp === 1 || cmp === 0) {
                return lastRegionSeen;
            } else if (cmp === -1) {
                lastRegionSeen = region;
            }
        }
        return lastRegionSeen;
        // throw new Error("shouldn't be possible to get here");
    },

    function _regionAfter(self, offset) {
        for (var i = 0; i < self._regions.length; i++) {
            var region = self._regions[i];
            var cmp = region.compareToOffset(offset);
            if (cmp === 1) {
                return region;
            }
        }
        return null;
    },

    function _regionContainingOffset(self, offset) {
        for (var i = 0; i < self._regions.length; i++) {
            var region = self._regions[i];
            if (region.compareToOffset(offset) === 0) {
                // HIT
                return region;
            }
        }
        return null;
    },


    /**
     * Add the given amount to the offset of all regions at or after
     * startingFromIndex.
     */
    function _adjustRegionOffsets(self, startingFromIndex, amount) {
        for (var i = startingFromIndex; i < self._regions.length; ++i) {
            self._regions[i].adjustOffset(amount);
        }
    },

    /**
     * Figure out if there is offset overlap between two regions and push the
     * rightmost one and all those to its right even further to the right if
     * there is.  Return true if any adjustment is made, false otherwise.
     */
    function _pushRegionsRight(self, startingFromIndex) {
        if ((startingFromIndex >= 0) && (startingFromIndex <
                                         self._regions.length - 1)) {
            var thisRegion = self._regions[startingFromIndex];
            var nextRegion = self._regions[startingFromIndex + 1];
            var end = thisRegion.lastOffset() + 1;
            var offsetOverlap = nextRegion.firstOffset() - end;
            if (offsetOverlap <= 0) {
                self._adjustRegionOffsets(startingFromIndex + 1,
                                          (-offsetOverlap) + 1);
                return true;
            }
            // Do the two regions visually overlap?
            if (thisRegion.viewPeer.pixelBottom() >
                nextRegion.viewPeer.pixelTop()) {
                // If so we need to tell all the regions to update because
                // their pixels may have shifted, even if their offset didn't.
                self._adjustRegionOffsets(startingFromIndex + 1, 0);
                return true;
            }
            return false;
        } else {
            return false;
        }
    },

    /**
     * Convert an element of data from the server into a row object.
     */
    function dataAsRow(self, dataElement) {
        dataElement.exactlyEqualTo = function (otherElement) {
            return dataElement.__id__ === otherElement.__id__;
        };
        return dataElement;
    },

    /**
     * Integrate the given rows into the model at the given offset.
     *
     * @param offset: an integer, the logical offset into the table where we
     * guess they might go.
     *
     * @param data: a list of simple objects retrieved from the server.
     *
     * @return: a list with 2 elements: the first being an integer, the number
     * of new rows inserted into the table as a result of this operation.  The
     * second being the L{RowRegion} in this table ultimately created or
     * affected by this insertion.
     */
    function insertRowData(self, offset, data) {
        // XXX TODO: if there's no actual data being inserted, we can (and
        // really should) skip all of this.
        if (data.length === 0) {
            return [0, null];
        }
        var newRegion = Mantissa.ScrollTable.RowRegion(self, offset, data);
        for (var i = 0; i < self._regions.length; ++i) {
            var thisRegion = self._regions[i];
            if (thisRegion.overlapsValue(newRegion.firstValue())) {
                var originalRegionLength = thisRegion.rows.length;
                thisRegion.coalesceAtMyEnd(newRegion);
                var newRegionLength = thisRegion.rows.length;
                var adjustedNewRowCount = (newRegionLength -
                                           originalRegionLength);
                var offsetChange;
                /* /Also/ check to see if the end of our now merged region
                 * overlaps with the next region, if there is a next region.
                 * First: *is* there a next region?
                 */
                if (i < self._regions.length - 1) {
                    /* There is a next region.  Figure out the distance
                     * between the beginning of this region and the end of the
                     * next region.  It may be important later when
                     * determining if regions to the right of this one need to
                     * be shifted to the left, as is the case when a gap of N
                     * indices is replaced with M rows, where M < N.
                     */
                    var nextRegion = self._regions[i + 1];
                    if (thisRegion.overlapsValue(nextRegion.firstValue())) {
                        /* It does.  Join the current region together with the
                         * next one, dropping any overlapping rows.
                         */
                        var oldOffsetDistance =
                            ((nextRegion.firstOffset() + nextRegion.rows.length)
                             - thisRegion.firstOffset());
                        var nextRegionOrigLen = nextRegion.rows.length;
                        thisRegion.coalesceAtMyEnd(nextRegion);
                        adjustedNewRowCount = (
                            thisRegion.rows.length -
                            (nextRegionOrigLen + originalRegionLength));
                        self._regions.splice(i + 1, 1);
                        var newOffsetDistance = thisRegion.rows.length;
                        offsetChange = newOffsetDistance - oldOffsetDistance;
                    } else {
                        offsetChange = newRegionLength - originalRegionLength;
                    }
                    /* repeat the check because we may have just coalesced the
                     * _last_ region.
                     */
                    if (i < self._regions.length - 1) {
                        /* Check to see if the next region's offset now
                         * overlaps.
                         */
                        if (!self._pushRegionsRight(i)) {
                            self._adjustRegionOffsets(i + 1, offsetChange);
                        }
                    }
                }
                return [adjustedNewRowCount, thisRegion];
            } else if (thisRegion.overlapsValue(newRegion.lastValue())) {
                var existingRowCount = thisRegion.rows.length;
                newRegion.coalesceAtMyEnd(thisRegion);
                var newRowCount = newRegion.rows.length;
                self._regions[i] = newRegion;
                /* This is not the first region, so we may have collided to
                 * the left.
                 */
                self._pushRegionsRight(i - 1);
                return [newRowCount - existingRowCount, newRegion];
            } else {
                /* The given rows are entirely outside of this region.
                 */
            }
        }
        /* The given rows are entirely outside of all regions.  Find the
         * regions they are between and insert them there.
         */
        for (var i = 0; i < self._regions.length; ++i) {
            // XXX I should test this more directly
            if (self._regions[i].followsRegion(newRegion)) {
                self._regions.splice(i, 0, newRegion);
                if (i > 0) {
                    var offsetOverlapBefore = (
                        self._regions[i].firstOffset() -
                        (self._regions[i - 1].firstOffset() +
                         self._regions[i - 1].rows.length));
                    if (offsetOverlapBefore <= 0) {
                        self._regions[i].adjustOffset((-offsetOverlapBefore) + 1);
                    }
                }
                self._pushRegionsRight(i);
                return [newRegion.rows.length, newRegion];
            }
        }
        /* The new region didn't overlap any existing regions or fit before
         * any of them, so it belongs exactly at the end.  Put it there.
         */
        self._regions.push(newRegion);
        /* And make sure that it has a reasonable offset.
         */
        self._pushRegionsRight(self._regions.length - 2);
        return [newRegion.rows.length, newRegion];
    },

    /**
     * Find the RowRegion instance which contains the given offset.  This is a
     * utility method used by tests.
     *
     * @param offset: a row offset into the table.
     *
     * @return: a L{RowRegion}.
     */
    function _rangeContainingOffset(self, offset) {
        for (var i = 0; i < self._regions.length; ++i) {
            if (offset >= self._regions[i].firstOffset()) {
                return i;
            }
        }
        throw new Error("Invalid offset!");
    },

    /**
     * Determine the number of indices initially in the model.
     *
     * The strategy used is to load the first and last rows from the server so
     * that the approximate size of the data set is known.  From this, the
     * total number of rows is estimated.
     *
     * @return: A L{Divmod.Defer.Deferred} which will be called back with the
     * number of row indices initially present in this RegionModel.  This is
     * just an estimate, so it may change later.
     */

    function _initialize(self) {
        var pagesize = self._pagesize;
        if (self._outstandingInitRequest !== undefined) {
            return self._outstandingInitRequest;
        }
        var valueRequests;
        if (self._sortAscending) {
            valueRequests = Divmod.Defer.gatherResults(
                [self.server.rowsAfterValue(null, pagesize),
                 self.server.rowsBeforeValue(null, pagesize)]);
        } else {
            var swap = function (x) {
                x.reverse();
                return x;
            };
            var x1 = self.server.rowsBeforeValue(null, pagesize).addCallback(swap);
            var x2 = self.server.rowsAfterValue(null, pagesize).addCallback(swap);
            valueRequests = Divmod.Defer.gatherResults([x1, x2]);
        }
        self._outstandingInitRequest = valueRequests;
        valueRequests.addCallback(function (result) {
            var firstRows = result[0];
            var lastRows = result[1];

            if (firstRows.length === 0) {
                return 0;
            }
            if (firstRows.length < pagesize) {
                /* This is the "very little data" case.  We asked for N rows,
                 * and got back fewer than N, which means that we have seen
                 * the end of the data set in the same result as the
                 * beginning.  Store the rows and then say that we're done.
                 */
                self.insertRowData(0, firstRows);
                return firstRows.length;
            } else if (firstRows.length === pagesize) {
                /* This is the average case.  We requested some rows and got
                 * back exactly that many, which means there may be some more
                 * rows.  It's also possilbe that the entire data-set matches
                 * the page size exactly.
                 */
                self.insertRowData(0, firstRows);
                // XXX TODO: I need to estimate a reasonable number here; 1000
                // isn't particularly good.
                self.insertRowData(1000, lastRows); 
                var lastRegion = self._regions[self._regions.length - 1];
                return lastRegion.firstOffset() + lastRegion.rows.length;
            } else {
                throw new Error("The server returned more rows than we asked for.");
            }
        });
        valueRequests.addBoth(function (result) {
            delete self._outstandingInitRequest;
            self._initialized = true;
            return result;
        });
        return valueRequests;
    });


Mantissa.ScrollTable.DOMRegionView = Divmod.Class.subclass(
    'Mantissa.ScrollTable.DOMRegionView');

/**
 * A DOMRegionView is the DOM-manipulating view class for a single RowRegion
 * within a RegionModel.
 *
 * @ivar tableView: a L{ScrollTable} representing the view of the entire table
 * that this view is a member of.
 *
 * @ivar rowRegion: a L{RegionModel} instance containing row data for the
 * region that this view is rendering.
 *
 * @ivar node: an absolutely-positioned node within my tableView which
 * contains nodes for rows in this region and nodes for groups of rows merged
 * from other regions.
 */
Mantissa.ScrollTable.DOMRegionView.methods(
    /**
     * Create a DOMRegionView with a ScrollTable and a RowRegion.
     *
     * @param tableView: a L{ScrollTable} used to initialize the tableView
     * attribute.  (See class docstring.)
     *
     * @param rowRegion: a L{RowRegion} used to initialize the L{rowRegion}
     * attribute.  (See class docstring.)
     */
    function __init__(self, tableView, rowRegion) {
        self.tableView = tableView;
        self.rowRegion = rowRegion;
        self.node = self._makeNodeForRegion();
        self.tableView.node.appendChild(self.node);
        self.node.appendChild(self._makeNodeForRows());
        self.refreshViewOffset();
    },

    /**
     * Return the pixel position, relative to the top of the table view's
     * node, of the end of this region's node.
     *
     * @rtype: C{Number} (integer)
     */
    function pixelBottom(self) {
        return self.pixelTop() + self.node.clientHeight;
    },

    /**
     * Return the pixel position, relative to the top of the table view's
     * node, of the beginning of this region's node.
     *
     * @rtype: C{Number} (integer)
     */
    function pixelTop(self) {
        return parseInt(self.node.style.top);
    },

    /**
     * Return the average height, in pixels, of one row in this region.
     */
    function averageRowPixelHeight(self) {
        return Math.floor(self.node.clientHeight / self.rowRegion.rows.length);
    },

    /**
     * Create a DOM element to represent a region and return it.
     *
     * @return: an unparented DOM node with no padding, margin, or borders,
     * which is absolutely positioned at an appropriate offset from the top of
     * the scrolling area.
     */
    function _makeNodeForRegion(self) {
        var regionNode = document.createElement('div');
        regionNode.setAttribute('class', 'mantissa-row-region-node');
        regionNode.style.border = '0px';
        regionNode.style.margin = '0px';
        regionNode.style.padding = '0px';
        regionNode.style.position = 'absolute';
        return regionNode;
    },

    /**
     * Make a container node to hold rows.
     */
    function _makeRowContainerNode(self) {
        var rowsNode = MochiKit.DOM.DIV({"class": "row-container-node"});
        rowsNode.style.border = '0px';
        rowsNode.style.margin = '0px';
        rowsNode.style.padding = '0px';
        return rowsNode;
    },

    /**
     * Create an inner DOM node containing all the rows within this region, as
     * distinct from the region itself, so that the rows can be migrated as a
     * group.
     */
    function _makeNodeForRows(self) {
        var rowsNode = self._makeRowContainerNode();
        var row, rowNode;
        for(var i = 0; i < self.rowRegion.rows.length; i++) {
            row = self.rowRegion.rows[i];
            if (row.__TEMPORARY__) {
                rowNode = MochiKit.DOM.SPAN(
                    {"class": "row-temporary-placeholder"},
                    "TempRow");
            } else {
                /* XXX _createRow shouldn't really take an offset argument,
                 * since the offset of the rows may shift as more rows are
                 * requested; we need to figure out another way to make the
                 * rows alternate colors.  A CSS selector, perhaps?
                 */
                rowNode = self.tableView._createRow(
                    self.rowRegion.offset + i, row);
            }
            rowsNode.appendChild(rowNode);
        }
        return rowsNode;
    },

    /* "public" region view interface, for interacting with RegionModel */

    /**
     * Merge this DOMRegionView with another that follows it by subsuming its
     * only DOM child, the row-containing node.
     *
     * @param regionView: another DOMRegionView object, which is contiguous
     * with this one.
     *
     * @param newDataStart: an integer, the local offset into the regionView
     * argument where new data begins.
     */
    function mergeWithRegionView(self, regionView, newDataStart) {
        for (var i = 0; i < newDataStart; i++) {
            regionView.removeViewRow(0);
        }
        var otherRegionViewNode = regionView.node.childNodes[0];
        otherRegionViewNode.parentNode.removeChild(otherRegionViewNode);
        self.node.childNodes[0].appendChild(otherRegionViewNode);
        regionView.destroy();
    },

    /**
     * Determine if a row node is a container node.
     */
    function _isRowContainerNode(self, node) {
        return MochiKit.DOM.hasElementClass(node, "row-container-node");
    },

    /**
     * Remove a row node from this DOMRegionView's row content node.
     *
     * @param localOffset: an integer representing an offset into this
     * DOMRegionView's data.  The first row in this region is at local offset
     * 0.
     */
    function removeViewRow(self, localOffset) {
        var plat = Divmod.Runtime.Platform;
        var topRegionContainer = self.node.childNodes[0];
        var currentOffset = 0;
        Divmod.Runtime.theRuntime.traverse(
            topRegionContainer,
            function (aNode) {
                if (self._isRowContainerNode(aNode)) {
                    return plat.DOM_DESCEND;
                } else {
                    if (currentOffset === localOffset) {
                        aNode.parentNode.removeChild(aNode);
                        return plat.DOM_TERMINATE;
                    }
                    currentOffset++;
                    return plat.DOM_CONTINUE;
                }
        });
    },

    /**
     * Update this region's node's pixel offset within its parent node to
     * reflect a new offset of its region.
     */
    function refreshViewOffset(self) {
        // Get the previous region
        var prevRegion = self.rowRegion.previousRegion();
        var bottom;
        var lastOffset;
        if (prevRegion === undefined) {
            bottom = 0;
            lastOffset = 0;
        } else {
            bottom = prevRegion.viewPeer.pixelBottom();
            lastOffset = prevRegion.lastOffset() + 1;
        }

        // Add _getRowHeight times the offset difference between the last row
        // of that thing and the first row of our thing
        var offsetDifference = (self.rowRegion.firstOffset() - lastOffset);
        self.node.style.top = ((bottom + (offsetDifference *
                                          self.tableView._getRowHeight()))
                               + "px");
    },

    /**
     * Destroy this region view, removing it from the DOM.
     */
    function destroy(self) {
        self.node.parentNode.removeChild(self.node);
    });


/**
 * This object maps column type names (sent from the server) to column classes
 * on the client.
 */

Mantissa.ScrollTable._columnTypes = {
    'integer': Mantissa.ScrollTable.IntegerColumn,
    'text': Mantissa.ScrollTable.TextColumn,
    'timestamp': Mantissa.ScrollTable.TimestampColumn,
    'boolean': Mantissa.ScrollTable.BooleanColumn,
    'widget': Mantissa.ScrollTable.WidgetColumn
};

Mantissa.ScrollTable.ScrollTable = Mantissa.ScrollTable._ScrollingBase.subclass(
    'Mantissa.ScrollTable.ScrollTable');

/**
 * A ScrollTable is a scrolling viewport which can view a collection of data
 * on the server.  It is designed around the notion that the server's
 * representation is a large B-tree, and it requests data by values in that
 * tree rather than by offset.
 *
 * This is the newest, best scrolling table implementation that everything
 * should use from now on.  L{Mantissa.TDB} and, to a lesser extent,
 * L{Mantissa.ScrollTable.ScrollingWidget} are both sub-optimal
 * implementations of this and will eventually be removed.
 */
Mantissa.ScrollTable.ScrollTable.methods(
    /**
     * Create a scrolltable.
     *
     * @param node: a DOM node, which will be used for the scrolling viewport.
     *
     * @param currentSortColumn: a L{String}, the name of the column that is
     * initially used for sorting.
     *
     * @param columnList: an L{Array} of objects with 'type' and 'name'
     * attributes.
     *
     * @param defaultSortAscending: a boolean, the initial sort ordering of
     * the scroll model; true for ascending, false for descending.
     */
    function __init__(self, node, currentSortColumn, columnList,
                      defaultSortAscending) {
        Mantissa.ScrollTable.ScrollTable.upcall(self, '__init__', node);
        var column, columnClass;
        var columns = {};

        var legacyColumnNames = [];
        var legacyColumnTypes = {};

        for (var i = 0; i < columnList.length; ++i) {
            column = columnList[i];
            columnClass = Mantissa.ScrollTable._columnTypes[column.type];
            if (columnClass === undefined) {
                throw new Error('no handler for column type: ' + column.type);
            }
            columns[column.name] = columnClass(column.name);

            legacyColumnTypes[column.name] = [column.type, false]; // type, sortable
            legacyColumnNames.push(column.name);
        }

        /* These are set for _ScrollingBase.  Hopefully they can be removed
         * when the offending subclass in Mailbox.js stops depending on them.
         * See its docstring.
         */
        self.columnTypes = legacyColumnTypes;
        self.columnNames = legacyColumnNames;
        /* end legacy crap */

        self.columns = columns;
        self.sortColumn = columns[currentSortColumn];
        self.model = Mantissa.ScrollTable.RegionModel(
            self, self, self.sortColumn, defaultSortAscending);

        self.connectDOMEvent("onscroll");
        self._debounceInterval = 0.5;
        self._processingScrollEvent = null;
    },

    ////// Begin compatibility with old scrolltable for easier replacement of
    ////// the Quotient Mailbox view

    /**
     * Upon inserting the node into the DOM, calculate heights for headers,
     * rows, and the table itself.
     */
    function loaded(self) {
        /* XXX This is fakery.  We don't support headers yet, this node is
         * just for satisfying the base class.
         */
        self._headerRow = document.createElement("div");
        /* More legacy attributes are set within resetColumns, and we'll need
         * them for rendering things.
         */
        self.resetColumns();
        self._detectPageSize();
        var feedback = self.startShowingFeedback();
        var d = self.model._initialize();
        d.addCallback(function (result) {
            feedback.stop();
            return result;
        });
        return d;
    },

    /**
     * Invalidate this scrolltable and re-request its seed data from the
     * server.
     */
    function emptyAndRefill(self) {
        self.model.empty();
        return self.model._initialize();
    },

    /**
     * Remove a row at the given offset from the local data-set and DOM.  This
     * method does not affect the server.
     */
    function removeRow(self, offset) {
        self.model.removeRow(offset);
    },

    /**
     * This is invoked internally to get a test row since it is overridden in
     * subclasses, but it should no longer be necessary.
     */
    function _getRowGuineaPig(self) {
        return self._createRow(0, self._makeFakeData());
    },

    /**
     * Override row creation to simplify it from the base implementation,
     * since we require a <DIV> container, not a <TABLE>, for the DOM
     * techniques employed in this scroll area.
     */
    function makeRowElement(self, rowOffset, rowData, cells) {
        return MochiKit.DOM.DIV({"class": "scroll-row",
                "style": "clear: both; border: 0px; padding: 0px; margin: 0px"},
                                cells);
    },

    /**
     * Override cell creation to simplify it from the base implementation,
     * since we require a <DIV> row container, not a <TR>, for the DOM
     * techniques employed in this scroll area.
     */
    function makeCellElement(self, colName, rowData) {
        var attrs = {"class": "scroll-cell",
                     'style': "padding-left: 5px;"};
        if(self.columnWidths && colName in self.columnWidths) {
            attrs["style"] += "width:" + self.columnWidths[colName];
        }
        var columnObject = self.columns[colName];
        var columnValue = columnObject.extractValue(rowData);
        var columnNode = columnObject.valueToDOM(columnValue, self);

        var node = MochiKit.DOM.SPAN(
            attrs,
            /* there is an IE bug (See other implementation of makeCellElement
             * above) which required a containing node.  Perhaps we can
             * abandon the SPAN at some point once we have verified it does
             * not affect IE?
             */
            MochiKit.DOM.A({"href": rowData.__id__}, columnNode));
        return node;
    },

    ////// End compatibility with old scrolltable for Mailbox view

    /**
     * Detect the height of our node and the height of one row, and from that
     * extrapolate the smallest number of rows we must request per page.  Save
     * that value as the model's "_pagesize" attribute.
     */
    function _detectPageSize(self) {
        var rowHeight = self._getRowHeight();
        var viewportHeight = (
            Divmod.Runtime.theRuntime.getElementSize(self.node).h);
        if (viewportHeight !== 0) {
            self.model._pagesize = Math.max(
                Math.ceil(viewportHeight / rowHeight), 2);
        }
    },

    /**
     * event handler for 'onscroll' DOM event, which requests more rows if the
     * scrollbar remains in the same position for long enough.
     */
    function onscroll(self, event) {
        if (self._processingScrollEvent !== null) {
            self._processingScrollEvent.cancel();
        }
        self._processingScrollEvent = self.callLater(
            self._debounceInterval,
            function () {
                self._processingScrollEvent = null;
                /* The user has remained still on a particular row for
                 * _debounceInterval seconds.  Time to issue a real scroll
                 * event to our model.
                 */
                var feedback = self.startShowingFeedback();
                var maybeD = self.model.expose(
                    self.translateScrollOffset(self.visiblePixelTop()));
                if (maybeD instanceof Divmod.Defer.Deferred) {
                    maybeD.addBoth(function (result) {
                        feedback.stop();
                        return result;
                    });
                }
            });
    },

    /**
     * Start showing some "We're loading some rows" feedback and return an
     * object with a 'stop' method to remove it.
     */
    function startShowingFeedback(self) {
        var feedbackTop = self.visiblePixelTop();
        var visibleHeight = self.visiblePixelHeight();
        var node = MochiKit.DOM.DIV({"class": "scrolltable-loading"},
                                    MochiKit.DOM.DIV({}, "Loading..."));
        node.style.position = "absolute";
        node.style.top = feedbackTop + 'px';
        node.style.height = visibleHeight + 'px';
        self.node.appendChild(node);
        return {stop: function() {
                self.node.removeChild(node);
            }};
    },

    /**
     * Get the pixel position of the top edge of this scrolltable's node.
     *
     * Override this method in subclasses, if the table is styled in a way
     * which uses a different scroll bar, to return the topmost visible pixel
     * relative to the top of the scrollable area.
     *
     * @rtype: C{Number} (integer)
     */
    function visiblePixelTop(self) {
        // This technique is ad-hoc and should eventually be replaced with
        // something more general that is not a direct DOM API.  See
        // http://divmod.org/trac/ticket/2182
        // for more information.
        return self.node.scrollTop;
    },

    /**
     * Get the height of the visible portion of this scrolltable's node.  This
     * is used to determine the height of the feedback message.
     *
     * Override this methods in subclasses, if the table is styled in a way
     * which visually exposes a different area.
     *
     * @rtype: C{Number} (integer)
     */
    function visiblePixelHeight(self) {
        // The comment in visiblePixelTop above applies here as well.  See
        // http://divmod.org/trac/ticket/2182 for more information.
        return parseInt(self.node.style.height);
    },

    /**
     * Get the region view before a given pixel offset.
     */
    function regionBeforePixel(self, pixelOffset) {
        var regs = self.model._regions;
        var prevRegion = undefined;
        for (var i = 0; i < regs.length; i++) {
            var eachRegion = regs[i];
            if (eachRegion.viewPeer.pixelTop() > pixelOffset) {
                break;
            }
            prevRegion = eachRegion;
        }
        return prevRegion;
    },

    /**
     * Translate a pixel offset within my node to a desired row offset from my
     * model.
     */
    function translateScrollOffset(self, pixelOffset) {
        var reg = self.regionBeforePixel(pixelOffset);
        if (reg === undefined) {
            return Math.floor(pixelOffset / self._getRowHeight());
        } else {
            if (reg.viewPeer.pixelBottom() < pixelOffset) {
                // we're below the region
                pixelOffset -= reg.viewPeer.pixelBottom();
                return Math.floor((pixelOffset / self._getRowHeight())
                                  + (reg.lastOffset() + 1));
            } else {
                // we're inside the region
                var someHeight = reg.viewPeer.averageRowPixelHeight();
                var internalPixelOffset = pixelOffset - reg.viewPeer.pixelTop();

                /* If the user can't see past the end of the region, let's
                 * return the first offset in the region, so that expose()
                 * won't think that we need to request more data. */

                if ( reg.viewPeer.pixelBottom() >
                     (pixelOffset + self.visiblePixelHeight()) ) {
                    return reg.firstOffset();
                }

                /* We want to know what row in this region the top of the
                 * scroll viewport is looking at.  But we can't know exactly,
                 * because browsers are terrible, and the primary function of
                 * all browsers, that EIGHT BILLION PETABYTES of C++ CODE are
                 * dedicated to, i.e. translating the (x,y) coordinate of a
                 * mouse click into a node, is not exposed to javascript.  We
                 * can't afford expensive, potentially deep DOM traversal of
                 * all row nodes on every click to interrogate them, and
                 * caching all the pixel start/stop locations would be complex
                 * and error-prone, so ...
                 *
                 * What we're doing here is getting the average pixel height
                 * of one row in this region, then figuring out what node we
                 * are *probably* looking at, assuming all of those rows are
                 * actually the same height.  This guess is certainly going to
                 * be wrong if the heights vary significantly, but *actually*
                 * all we care about is whether you can see past the end of
                 * the last node or not, and this will get us a fairly correct
                 * answer all of the time for that particular question.
                 */
                return (Math.ceil(internalPixelOffset / someHeight) +
                        reg.firstOffset());

            }
        }
    },

    /**
     * @return: a fake data object which has all the values from the columns
     * described by this table.  This is used to generate representative data
     * suitable for creating a sample row view with the DOM creation methods,
     * which is used to calculate the height of a single row.
     */
    function _makeFakeData(self) {
        var fakeRow = {};
        for (var columnName in self.columns) {
            var colObj = self.columns[columnName];
            fakeRow[columnName] = colObj.fakeValue();
        }
        return fakeRow;
    },

    /**
     * Calculate the height of a 'standard' row, and return it.
     */

    function _getRowHeight(self) {
        if (self._cachedRowHeight !== undefined) {
            return self._cachedRowHeight;
        }
        // XXX What should probably happen here is we should look for real
        // rows and only create the fake one if we really need it, caching the
        // value...
        var fakeNode = self._getRowGuineaPig();
        var enclosing = document.createElement("div");

        enclosing.appendChild(fakeNode);

        /* Don't show this to the user.  We need to add it to the document to
         * realize it and give it real height and width attributes, but that's
         * all!
         */
        enclosing.style.position = 'absolute';
        enclosing.style.visibility = 'hidden';

        /* Since browsers have an inconsistent box model, we need to make sure
         * that none of the elements which may get involved in calculation of
         * the height of this element have any value whatsoever.
         */
        enclosing.style.border = '0px';
        enclosing.style.margin = '0px';
        enclosing.style.padding = '0px';

        /* Finally the enclosing node must be actually in the document
         * somewhere in order to be measured.  Let's put it within our node so
         * that all the styles and so on apply to it.
         */
        self.node.appendChild(enclosing);
        var theHeight = enclosing.clientHeight;
        /* No reason to leave it there, though. */
        self.node.removeChild(enclosing);
        if (theHeight !== 0) {
            self._cachedRowHeight = theHeight;
        }
        return theHeight;
    },

    /* server methods */
    function rowsBeforeValue(self, value, count) {
        return self.callRemote('rowsBeforeValue', value, count);
    },

    function rowsAfterValue(self, value, count) {
        return self.callRemote('rowsAfterValue', value, count);
    },

    function rowsAfterRow(self, row, count) {
        return self.callRemote('rowsAfterRow', row, count);
    },

    /**
     * Call the remote method C{rowsBeforeRow}, informing it that we'd like
     * C{count} rows before the reference row C{row}.
     *
     * @param row: a reference row.
     * @type row: C{Object}
     *
     * @param count: the desired number of rows.
     * @type row: C{Number}
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function rowsBeforeRow(self, row, count) {
        return self.callRemote('rowsBeforeRow', row, count);
    },

    /* view methods */
    function createRegionView(self, rowRegion) {
        return Mantissa.ScrollTable.DOMRegionView(self, rowRegion);
    });
