// import Nevow.Athena.Test

// import Mantissa
// import Mantissa.ScrollTable
// import Mantissa.Test.TestRegionModel

Mantissa.Test.TestRegionLive.ScrollingElementTestCase = Nevow.Athena.Test.TestCase.subclass(
    'Mantissa.Test.TestRegionLive.ScrollingElementTestCase');
Mantissa.Test.TestRegionLive.ScrollingElementTestCase.methods(
    Mantissa.Test.TestRegionModel.makeRow,
    /**
     * Get a scrolling element from the server.
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function _getScrollingElement(self, /*optional*/rowCount) {
        if (rowCount === undefined) {
            rowCount = 0;
        }
        var D = self.callRemote('getScrollingElement', rowCount);
        D.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        D.addCallback(
            function(widget) {
                self.node.appendChild(widget.node);
                return widget;
            });
        return D;
    },

    function _testRowsBeforeAfterValue(self, elt, rowsBefore, rowsAfter) {
        var assertValueInRow = function (value, row) {
            self.assertEqual(value, row.value);
        };
        var result = elt.model.server.rowsBeforeValue(null, 10);
        result.addCallback(
            function(recvdRowsBefore) {
                self.assertArraysEqual(rowsBefore, recvdRowsBefore,
                                       assertValueInRow);
                return elt.model.server.rowsAfterValue(null, 10);
            });
        result.addCallback(
            function(recvdRowsAfter) {
                self.assertArraysEqual(rowsAfter, recvdRowsAfter,
                                       assertValueInRow);
            });
        return result;
    },

    /**
     * Verify that an empty set of results on the server side results in empty
     * arrays being returned for rowsBeforeValue and rowsAfterValue on null
     * values.
     */
    function test_emptyModelServerCommunication(self) {
        return self._getScrollingElement().addCallback(
            function (elt) {
                return self._testRowsBeforeAfterValue(elt, [], []);
            });
    },

    /**
     * Verify that a single result on the server side results in a 1-row
     * result for rowsBeforeValue and rowsAfterValue on null values.
     */
    function test_oneRowModelServerCommunication(self) {
        return self._getScrollingElement(1).addCallback(
            function (elt) {
                return self._testRowsBeforeAfterValue(elt, [50], [50]);
            });
    },

    /**
     * Verify that rowsAfterRow returns the correct number of rows that appear
     * after the reference row.
     */
    function test_rowsAfterRow(self) {
        var ROW_COUNT = 6;
        var result = self._getScrollingElement(ROW_COUNT);
        var elt;
        result.addCallback(
            function (theElt) {
                elt = theElt;
                /* alternatively we could make the web IDs a predictable
                 * sequence */
                return elt.model._initialize();
            });
        result.addCallback(
            function (ign) {
                return elt.model.server.rowsAfterRow(
                    elt.model._regions[0].rows[0], 10);
            });
        result.addCallback(
            function (rows) {
                self.assertEqual(rows.length, ROW_COUNT - 1);
            });
        return result;
    },

    /**
     * Verify that rowsBeforeRow returns the correct number of rows that appear
     * before the reference row.
     */
    function test_rowsBeforeRow(self) {
        var ROW_COUNT = 9;
        var result = self._getScrollingElement(ROW_COUNT);
        var elt;
        result.addCallback(
            function (theElt) {
                elt = theElt;
                return elt.model._initialize();
            });
        result.addCallback(
            function (ign) {
                var lastRegion = elt.model._regions[
                    elt.model._regions.length - 1];
                var lastRow = lastRegion.rows[lastRegion.rows.length - 1];
                return elt.model.server.rowsBeforeRow(lastRow, 10);
            });
        result.addCallback(
            function (rows) {
                self.assertEqual(rows.length, ROW_COUNT - 1);
            });
        return result;
    },

    /**
     * Verify that initializing the scroll model will result in 2 regions
     * being created.  This test is a sanity check, to make sure that
     * adjustments to default page sizes, etc, will not invalidate the results
     * of other tests looking for behavior in the gap between regions.
     */
    function test_initialRequests(self) {
        var st = null;
        return self._getScrollingElement(10).addCallback(
            function (elt) {
                st = elt;
                return elt.model._initialize();
            }).addCallback(function () {
                self.assertEqual(st.model._regions.length, 2);
            });
    },

    /**
     * Verify that exposing a region in the middle of the table will ask the
     * server for a new, third region.
     */
    function test_estimateMiddleExpose(self) {
        var st = null;
        return self._getScrollingElement(10).addCallback(
            function (elt) {
                st = elt;
                return elt.model._initialize();
            }).addCallback(function () {
                return st.model.expose(5);
            }).addCallback(function () {
                self.assertEqual(st.model._regions.length, 3);
            });
    },

    /**
     * Test that L{Mantissa.ScrollTable.ScrollTable.createRegionView} returns
     * a L{Mantissa.ScrollTable.DOMRegionView}, which has C{tableView} and
     * C{rowRegion} attributes set to the correct values.
     */
    function test_createRegionView(self) {
        var result = self._getScrollingElement();
        result.addCallback(
            function(scrollTable) {
                scrollTable.model.insertRowData(
                    0, [self.makeRow(1234)]);
                var regionView = scrollTable.model._regions[0].viewPeer;
                self.failUnless(
                    regionView instanceof Mantissa.ScrollTable.DOMRegionView);
            });
        return result;
    },

    /**
     * Verify that after calling empty() on a full L{ScrollTable}'s model, the
     * L{ScrollTable} will no longer have any DOMRegionViews in it, and its
     * node will be empty.
     */
    function test_emptyEmptiesDOM(self) {
        var st;
        return self._getScrollingElement(10).addCallback(
            function (elt) {
                st = elt;
                return elt.model._initialize();
            }).addCallback(function () {
                self.assertEqual(st.node.childNodes.length, 2); // sanity check
                st.model.empty();
                self.assertEqual(st.node.childNodes.length, 0);
            });
    },

    /**
     * Verify that invoking emptyAndRefill will scroll the table back to the
     * top, as well as re-initializing the table.
     */
    function test_emptyAndRefill(self) {
        var st;
        return self._getScrollingElement(10).addCallback(
            function (elt) {
                st = elt;
                return elt.model._initialize();
            }).addCallback(function () {
                return st.model.expose(5);
            }).addCallback(function () {
                self.assertEqual(st.model._regions.length, 3); // sanity check
                self.assertEqual(st.node.childNodes.length, 3); // sanity check
                return st.emptyAndRefill();
            }).addCallback(function () {
                self.assertEqual(st.node.childNodes.length, 2);
                self.assertEqual(st.model._regions.length, 2);
                self.assertEqual(st.model._initialized, true);
                // user shouldn't find themselves looking at some random blank
                // space in the middle of the table
                self.assertEqual(st.node.scrollTop, 0);
            });
    },

    /**
     * Verify that the scrolled area translates into appropriate expose()
     * calls on the model.
     */
    function test_exposeCorrectRegions(self) {
        return self._getScrollingElement().addCallback(
            function (scrollTable) {
                var origModel = scrollTable.model;
                self.dataAsRow = origModel.dataAsRow;
                self.view = scrollTable;
                scrollTable.model = self;
                scrollTable.callLater = function (delay, thunk) {
                    thunk();
                    return {
                      cancel: function () {
                        }
                    };
                };

                // RowRegion's constructor is going to look at this, we just
                // want it to forget about it.
                self._regions = [];

                /* We need to pad out the scrolltable's height so that there
                 * will actually be a scrollbar that can move.  Otherwise,
                 * every assignment to scrollTop will instantly be truncated
                 * to 0.
                 */
                Mantissa.ScrollTable.RowRegion(self, 10000, [{value: 1234}]);
                var oneRowHeight = scrollTable._getRowHeight();
                /* We won't be testing anything if the height doesn't get
                 * bigger when you multiply it by things. */
                self.assertNotEqual(oneRowHeight, 0);
                scrollTable.node.scrollTop = oneRowHeight * 5;
                /* Make sure our little trick above actually worked; can we
                 * really scroll as far as we think we can?
                 */
                var exposure = self.tryExposing(scrollTable, 5);
                exposure.addCallback(
                    function(offset) {
                        self.assertEqual(offset, 5);
                    });
                exposure.addCallback(
                    function(ign) {
                        return self.tryExposing(scrollTable, 10);
                    });
                exposure.addCallback(
                    function(offset) {
                        self.assertEqual(offset, 10);
                    });
                return exposure;
            });

    },

    /**
     * Adjust a scrollTable's node to scroll to a particular row offset and
     * set up a Deferred which will be invoked by the next call to my expose()
     * method.
     *
     * @param scrollTable: a ScrollTable instance.
     *
     * @param rowCount: an offset to attempt an exposure at.
     */
    function tryExposing(self, scrollTable, rowCount) {
        self._pendingExposure = Divmod.Defer.Deferred();
        scrollTable.node.scrollTop = (
            scrollTable._getRowHeight() * rowCount);
        return self._pendingExposure;
    },

    /**
     * Stub implementation of RegionModel.expose which fires the deferred set
     * up by tryExposing.
     */
    function expose(self, rowOffset) {
        var pendingExposure = self._pendingExposure;
        delete self._pendingExposure;
        pendingExposure.callback(rowOffset);
    },

    /**
     * Retrieve the data inserted into a DOM node by looking at the text in
     * the node.
     *
     * @param regionNode: a node associated with a DOMRegionView.
     *
     * @return: an Array of strings associated with the values exposed to the
     * user.
     */
    function _scrapeRowDataFromRegion(self, regionNode) {
        var data = [];
        var node;
        for(var i = 0; i < regionNode.childNodes.length; i++) {
            node = regionNode.childNodes[i];
            if(node.firstChild.tagName) {
                data = data.concat(
                    self._scrapeRowDataFromRegion(node));
            } else {
                data.push(node.firstChild.nodeValue);
            }

        }
        return data;
    },

    /**
     * Verify that removing local rows will remove nodes from the regions.
     */
    function test_removeRowsRemovesNodes(self) {
        var it = null;
        return self._getScrollingElement(10).addCallback(function (that) {
            it = that;
            return it.model._initialize();
        }).addCallback(function () {
            it.removeRow(0);
            self.assertArraysEqual(
                self._scrapeRowDataFromRegion(it.node.firstChild),
                ['100']);
        });
    },

    /**
     * Test that L{Mantissa.ScrollTable.DOMRegionView.mergeWithRegionView}
     * correctly performs the merge DOM manipulations.
     */
    function test_mergeWithRegionView(self) {
        var result = self._getScrollingElement();
        result.addCallback(
            function(scrollTable) {
                scrollTable.model._initialize().addCallback(function () {
                    scrollTable.model.insertRowData(
                        0, [self.makeRow(1234), self.makeRow(1235),
                            self.makeRow(1236), self.makeRow(1237)]);
                    var regionView = scrollTable.model._regions[0].viewPeer;
                    scrollTable.model.insertRowData(
                        0, [self.makeRow(1236), self.makeRow(1237),
                            self.makeRow(1238), self.makeRow(1239)]);
                    self.assertEqual(scrollTable.node.childNodes.length, 1);
                    self.assertEqual(
                        // the first region's row container has 4 data rows and 1
                        // merged-from-next-region row.
                        scrollTable.node.firstChild.firstChild.childNodes.length, 5);
                    self.assertArraysEqual(
                        self._scrapeRowDataFromRegion(scrollTable.node.firstChild),
                        ['1234', '1235', '1236', '1237', '1238', '1239']);
                });
            });
        return result;
    });
