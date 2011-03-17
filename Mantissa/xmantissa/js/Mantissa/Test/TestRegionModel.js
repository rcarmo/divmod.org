// -*- test-case-name: xmantissa.test.test_javascript -*-
// Copyright (c) 2006 Divmod.
// See LICENSE for details.

/**
 * Unit tests for the scroll model which uses regions of inequality-defined
 * potentially non-contiguous data to make efficient queries against the
 * server.
 *
 * Note for future maintainers: some of these tests contain some unnecessary
 * duplication.  You are invited to eliminate that duplication wherever
 * possible, but be warned that many of the apparently duplicated test set-ups
 * are actually subtly different.
 */

// import Divmod.UnitTest
// import Divmod.Defer
// import Mantissa.ScrollTable
// import Nevow.Test.WidgetUtil

Mantissa.Test.TestRegionModel.ArrayRegionServer = Divmod.Class.subclass(
    'Mantissa.Test.TestRegionModel.ArrayRegionServer');

/**
 * Implement the IRegionServer API back-ended to a list.
 *
 * @ivar array: the array being viewed
 */
Mantissa.Test.TestRegionModel.ArrayRegionServer.methods(
    /**
     * Initialize an ArrayRegionServer with an array of data.
     *
     * @param array: an array of objects with 'value' properties, in ascending
     * order according to those properties.
     */
    function __init__(self, array) {
        self.array = array;
        self.requests = 0;
        self.paused = false;
    },

    /**
     * Stop answering requests immediately.  This allows tests to verify the
     * behavior of latency in answering requests.
     */
    function pause(self) {
        self.paused = true;
        self.buffer = [];
    },

    /**
     * Answser all requests made while paused, and begin answering requests
     * immediately again.
     */
    function unpause(self) {
        self.paused = false;
        while (self.buffer.length !== 0) {
            self.deliverOneResult();
        }
        delete self.buffer;
        self.paused = false;
    },

    /**
     * Answer only one request.
     */
    function deliverOneResult(self) {
        if (!self.paused) {
            throw new Error("You can only do this while we're paused.");
        }
        var pair = self.buffer.shift();
        var deferred = pair[0];
        var value = pair[1];
        deferred.callback(value);
    },

    /**
     * Shorthand alias for Defer.succeed for all Deferred returns in this
     * class.
     */
    function deferredReturn(self, value) {
        self.requests++;
        if (self.paused) {
            var d = Divmod.Defer.Deferred();
            self.buffer.push([d, value]);
            return d;
        } else {
            return Divmod.Defer.succeed(value);
        }
    },

    /* Everything method from here down is the server interface required by
     * the actual application code.  There are 4 methods: rowsBeforeValue,
     * rowsAfterValue, rowsAfterRow, and rowsBeforeRow.
     */

    /**
     * Retrieve C{count} rows from the model, starting at the first with a sort
     * column value greater than or equal to C{value}.
     *
     * @param value: A value of the type of the sort column for this model
     * which will be used as a lower (inclusive) bound in determining the rows
     * to return.  If this is C{null}, it will be treated the same as a value
     * smaller than any actually present in the data set.
     *
     * @return: A L{Divmod.Defer.Deferred} which will be called back with an
     * C{Array} of row data, where the first element of the array is the row
     * with the smallest sort column value greater than or equal to C{value},
     * the second element is the row with the smallest sort column value
     * greater than or equal to the sort column value of the first row, etc.
     * Ties are resolved in a stable but unpredictable order.  The array will
     * have at most C{count} elements, and may have fewer if there are fewer
     * rows available.
     */
    function rowsAfterValue(self, value, count) {
        if (count === undefined) {
            throw new Error("Undefined counts not allowed.");
        }
        if (value === null) {
            return self.deferredReturn(self.array.slice(0, count));
        }
        for (var i = 0; i < self.array.length; ++i) {
            if (self.array[i].value >= value) {
                var result = self.array.slice(i, i + count);
                return self.deferredReturn(result);
            }
        }
        return self.deferredReturn([]);
    },

    /**
     * Like L{rowsAfterValue}, but for retrieving rows with sort column values
     * less than C{value}.
     *
     * @param value: A value of the type of the sort column for this model
     * which will be used as an upper (exclusive) bound in determining the rows
     * to return.  If this is C{null}, it will be treated the same as a value
     * larger than any actually present in the data set.
     *
     * @return: A L{Divmod.Defer.Deferred} which will be called back with an
     * C{Array} of row data, where the last element of the array is the row
     * with the largest sort column value less than C{value}, the second to
     * last element is the row with the largest sort column value less than the
     * sort column value of the last row, etc.  Ties are resolved in the same
     * way as they are resolved by L{rowsAfterValue}.  The array will have at
     * most C{count} elements, and may have fewer if there are fewer rows
     * available.
     */
    function rowsBeforeValue(self, value, count) {
        var result = [];
        if (value === null) {
            result = self.array.slice(
                self.array.length - count,
                self.array.length);
        } else {
            for (var i = 0; i < self.array.length; ++i) {
                if (self.array[i].value > value) {
                    result = self.array.slice(i - count, i);
                    break;
                }
            }
        }
        return self.deferredReturn(result);
    },

    /**
     * Retrieve rows after a given Row object, which was itself retrieved from
     * this model previously.
     */
    function rowsAfterRow(self, row, count) {
        return self.rowsAfterValue(row.value, count+1).addCallback(
            function (result) {
                return result.slice(1);
            });
    },

    /**
     * Retrieve rows before a given ID.
     */
    function rowsBeforeRow(self, row, count) {
        return self.rowsBeforeValue(row.value, count+1).addCallback(
            function (result) {
                return result.slice(0, -1);
            });
    });

/**
 * This is a subclass which skews a numeric value for testing purposes so that
 * tests can easily detect whether it has been skewed or not.
 */
Mantissa.Test.TestRegionModel.SkewedColumn = Mantissa.ScrollTable.Column.subclass(
    'Mantissa.Test.TestRegionModel.SkewedColumn');
Mantissa.Test.TestRegionModel.SkewedColumn.methods(
    /**
     * Convert the input number to a much larger number.
     */
    function toNumber(self, value) {
        return value+50000;
    },

    /**
     * Reverse the translation performed in L{toNumber}.
     */
    function fromNumber(self, ordinal) {
        return ordinal-50000;
    });


/* The next two functions are non-anonymous on purpose, they're used as a sort
 * of ad-hoc mixin mechanism so I don't have to type the name again in every
 * single test (there are enough fully-qualified names in our JS code to last
 * everybody a lifetime already).
 */

/**
 * Generate a fake row object with a toString method so that we can see what
 * the heck is going wrong when we're debugging.
 */
Mantissa.Test.TestRegionModel.makeRow = function makeRow(self, value) {
    return {value: value,
            __id__: "TEST_"+value+"_VALUE",
            toString: function () {
            return '<Fake Row: ' + value + '>';
        }};
};

/**
 * Create a region model with a dummy view, by using the given server object
 * and sort-column description object.
 */
Mantissa.Test.TestRegionModel.makeRegionModel = function makeRegionModel(
    self, server, column, ascending) {
    self.dummyTableView = Mantissa.Test.TestRegionModel.DummyTableView(
        self, server, column, ascending);
    return self.dummyTableView.model;
};

Mantissa.Test.TestRegionModel.InsertRowDataTests =
    Divmod.UnitTest.TestCase.subclass(
        'Mantissa.Test.TestRegionModel.InsertRowDataTests');

/**
 * Unit tests for the insertRowData method of RegionModel.
 */
Mantissa.Test.TestRegionModel.InsertRowDataTests.methods(
    /* ad-hoc mixin - see above */
    Mantissa.Test.TestRegionModel.makeRegionModel,
    Mantissa.Test.TestRegionModel.makeRow,

    /**
     * Verify that just inserting a single row will result in a region being
     * added.
     */
    function test_firstInsertRowData(self) {
        var server = null;
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        var result = model.insertRowData(
            0, [self.makeRow(1), self.makeRow(3),
                self.makeRow(5), self.makeRow(7)]);
        self.assertIdentical(model._regions.length, 1);
        var reg = model._regions[0];
        self.assertIdentical(reg.rows.length, 4);
        self.assertIdentical(reg.rows[0].value, 1);
        self.assertIdentical(reg.rows[1].value, 3);
        self.assertIdentical(reg.rows[2].value, 5);
        self.assertIdentical(reg.rows[3].value, 7);
        self.assertIdentical(result[0], 4);
        self.assertIdentical(result[1], reg);
    },

    /**
     * Verify that storing two arrays of rows which do not have any overlap
     * results in two underlying row regions which each contain one of the row
     * arrays.
     */
    function test_nonOverlapping(self) {
        var server = null;
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        model.insertRowData(0, [self.makeRow(12), self.makeRow(34)]);
        model.insertRowData(4, [self.makeRow(56), self.makeRow(78)]);
        self.assertIdentical(model._regions.length, 2);
        var firstRegion = model._regions[0];
        self.assertIdentical(firstRegion.firstOffset(), 0);
        self.assertIdentical(firstRegion.rows.length, 2);
        self.assertIdentical(firstRegion.rows[0].value, 12);
        self.assertIdentical(firstRegion.rows[1].value, 34);
        var secondRegion = model._regions[1];
        self.assertIdentical(secondRegion.firstOffset(), 4);
        self.assertIdentical(secondRegion.rows.length, 2);
        self.assertIdentical(secondRegion.rows[0].value, 56);
        self.assertIdentical(secondRegion.rows[1].value, 78);
    },

    /**
     * Verify that storing two arrays of rows which do not have any overlap in
     * reverse order results in two underlying row regions which each contain
     * one of the row arrays.
     */
    function test_nonOverlappingBackwards(self) {
        var server = null;
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        model.insertRowData(4, [self.makeRow(56), self.makeRow(78)]);
        model.insertRowData(0, [self.makeRow(12), self.makeRow(34)]);
        self.assertIdentical(model._regions.length, 2);
        var firstRegion = model._regions[0];
        self.assertIdentical(firstRegion.firstOffset(), 0);
        self.assertIdentical(firstRegion.rows.length, 2);
        self.assertIdentical(firstRegion.rows[0].value, 12);
        self.assertIdentical(firstRegion.rows[1].value, 34);
        var secondRegion = model._regions[1];
        self.assertIdentical(secondRegion.firstOffset(), 4);
        self.assertIdentical(secondRegion.rows.length, 2);
        self.assertIdentical(secondRegion.rows[0].value, 56);
        self.assertIdentical(secondRegion.rows[1].value, 78);
    },


    /**
     * Verify that storing an array of rows in between two existing regions
     * with no overlap results in three underlying row regions which each
     * contain one of the row arrays.
     */
    function test_nonOverlappingBetween(self) {
        var server = null;
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        model.insertRowData(0, [self.makeRow(12), self.makeRow(34)]);
        model.insertRowData(4, [self.makeRow(78), self.makeRow(90)]);
        var between = model.insertRowData(2, [self.makeRow(56)]);
        self.assertIdentical(model._regions.length, 3);
        var firstRegion = model._regions[0];
        self.assertIdentical(firstRegion.firstOffset(), 0);
        self.assertIdentical(firstRegion.rows.length, 2);
        self.assertIdentical(firstRegion.rows[0].value, 12);
        self.assertIdentical(firstRegion.rows[1].value, 34);
        var secondRegion = model._regions[1];
        self.assertIdentical(secondRegion.firstOffset(), 3);
        self.assertIdentical(secondRegion.rows.length, 1);
        self.assertIdentical(secondRegion.rows[0].value, 56);
        self.assertIdentical(between[0], secondRegion.rows.length);
        self.assertIdentical(between[1], secondRegion);
        var thirdRegion = model._regions[2];
        self.assertIdentical(thirdRegion.firstOffset(), 5);
        self.assertIdentical(thirdRegion.rows.length, 2);
        self.assertIdentical(thirdRegion.rows[0].value, 78);
        self.assertIdentical(thirdRegion.rows[1].value, 90);
    },

    /**
     * Verify that storing two overlapping ranges at adjacent offsets results
     * in one underlying row range which contains the merged row data.  In so
     * doing, the merged region should acquire the offset of the inserted
     * data, because that is where the user will be looking if this insertion
     * is in response to an expose() request.
     */
    function test_overlapDetectionNoGap(self) {
        var server = null;
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        model.insertRowData(0, [self.makeRow(12), self.makeRow(34)]);
        model.insertRowData(2, [self.makeRow(34), self.makeRow(56)]);
        self.assertIdentical(model._regions[0].firstOffset(), 0);
        self.assertIdentical(model._regions.length, 1);
        var rows = model._regions[0].rows;
        self.assertIdentical(rows.length, 3);
        self.assertIdentical(rows[0].value, 12);
        self.assertIdentical(rows[1].value, 34);
        self.assertIdentical(rows[2].value, 56);
    },


    /**
     * Verify that storing two overlapping ranges at adjacent offsets in
     * reverse order results in one underlying row range which contains the
     * merged row data.
     */
    function test_overlapDetectionNoGapBackwards(self) {
        var server = null;
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        model.insertRowData(1234, [self.makeRow(34), self.makeRow(56)]);
        var overlap = model.insertRowData(6, [self.makeRow(12), self.makeRow(34)]);
        self.assertIdentical(model._regions.length, 1);
        self.assertIdentical(model._regions[0].firstOffset(), 6);
        var rows = model._regions[0].rows;
        self.assertIdentical(rows.length, 3);
        self.assertIdentical(rows[0].value, 12);
        self.assertIdentical(rows[1].value, 34);
        self.assertIdentical(rows[2].value, 56);
        self.assertIdentical(overlap[0], 1); // just 1 new row, "12"
        self.assertIdentical(overlap[1], model._regions[0]);
    },


    /**
     * Verify that storing a new array of rows which overlaps with two
     * existing regions results in a single underlying row range consisting of
     * the rows from both existing regions, as well as the new rows.
     */
    function test_doubleOverlap(self) {
        var server = null;
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        model.insertRowData(0, [self.makeRow(12), self.makeRow(34)]);
        model.insertRowData(3, [self.makeRow(78), self.makeRow(90)]);
        var overlap = model.insertRowData(
            1, [self.makeRow(34), self.makeRow(56), self.makeRow(78)]);
        self.assertIdentical(model._regions.length, 1);
        self.assertIdentical(model._regions[0].firstOffset(), 0);
        var rows = model._regions[0].rows;
        self.assertIdentical(rows[0].value, 12);
        self.assertIdentical(rows[1].value, 34);
        self.assertIdentical(rows[2].value, 56);
        self.assertIdentical(rows[3].value, 78);
        self.assertIdentical(rows[4].value, 90);
        self.assertIdentical(rows.length, 5);
        // Only 1 new row was inserted.
        self.assertIdentical(overlap[0], 1);
        self.assertIdentical(overlap[1], model._regions[0]);
    },

    /**
     * Verify that storing an array of rows, then storing another array of
     * rows with smaller values, will cause the indices of the first array of
     * rows to be increased.
     */
    function test_pushRightNoOverlapLargerFirst(self) {
        var server = null;
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        model.insertRowData(0, [self.makeRow(78), self.makeRow(90)]);
        model.insertRowData(0, [self.makeRow(12), self.makeRow(34)]);

        var regions = model._regions;
        self.assertIdentical(regions.length, 2);
        self.assertIdentical(regions[0].firstOffset(), 0);
        self.assertIdentical(regions[1].firstOffset(), 3);

        var firstRows = model._regions[0].rows;
        self.assertIdentical(firstRows.length, 2);
        self.assertIdentical(firstRows[0].value, 12);
        self.assertIdentical(firstRows[1].value, 34);
        var secondRows = model._regions[1].rows;
        self.assertIdentical(secondRows.length, 2);
        self.assertIdentical(secondRows[0].value, 78);
        self.assertIdentical(secondRows[1].value, 90);
    },


    /**
     * Verify that storing an array of rows A, then storing another array of
     * rows B with larger values at the same offset, will cause the offset of
     * B to be set to leave a gap of one offset beyond the end of A (since we
     * are not sure if A and B actually overlap or not, we don't have enough
     * information).
     */
    function test_pushRightNoOverlapSmallerFirst(self) {
        var server = null;
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        model.insertRowData(0, [self.makeRow(12), self.makeRow(34)]);
        model.insertRowData(0, [self.makeRow(78), self.makeRow(90)]);

        var regions = model._regions;
        self.assertIdentical(regions.length, 2);
        self.assertIdentical(regions[0].firstOffset(), 0);
        self.assertIdentical(regions[1].firstOffset(), 3);

        var firstRows = model._regions[0].rows;
        self.assertIdentical(firstRows.length, 2);
        self.assertIdentical(firstRows[0].value, 12);
        self.assertIdentical(firstRows[1].value, 34);

        var secondRows = model._regions[1].rows;
        self.assertIdentical(secondRows.length, 2);
        self.assertIdentical(secondRows[0].value, 78);
        self.assertIdentical(secondRows[1].value, 90);
    },

    /**
     * Verify that storing an array of rows, C, such that an existing region,
     * A, is extended to the right encroaching on the index space of a second
     * region, B, but without overlapping its values, results in the offset of
     * B (and all regions to its right) is (are) increased to make space for
     * the new A+C amalgam as well as a gap, as C's values do not overlap with
     * B's values.
     */
    function test_pushRightLeftOverlap(self) {
        var server = null;
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        // A
        model.insertRowData(0, [self.makeRow(12), self.makeRow(23)]);
        // B (according to test_pushRightLeftOverlap, this will be
        // shifted over to index 3...)
        model.insertRowData(0, [self.makeRow(78), self.makeRow(89)]);
        // OMEGA ("all regions to its right")
        model.insertRowData(50, [self.makeRow(90)]);
        // sanity check?
        self.assertIdentical(model._regions[2].firstOffset(), 50);
        self.assertIdentical(model._regions[1].firstOffset(), 3);

        // C
        model.insertRowData(1, [self.makeRow(23), self.makeRow(34), self.makeRow(45)]);

        var regions = model._regions;
        self.assertIdentical(regions.length, 3);
        self.assertIdentical(regions[0].firstOffset(), 0);
        self.assertIdentical(regions[1].firstOffset(), 5);
        self.assertIdentical(regions[2].firstOffset(), 52);

        var firstRows = model._regions[0].rows;
        self.assertIdentical(firstRows.length, 4);
        self.assertIdentical(firstRows[0].value, 12);
        self.assertIdentical(firstRows[1].value, 23);
        self.assertIdentical(firstRows[2].value, 34);
        self.assertIdentical(firstRows[3].value, 45);

        var secondRows = model._regions[1].rows;
        self.assertIdentical(secondRows.length, 2);
        self.assertIdentical(secondRows[0].value, 78);
        self.assertIdentical(secondRows[1].value, 89);

        var thirdRows = model._regions[2].rows;
        self.assertIdentical(thirdRows.length, 1);
        self.assertIdentical(thirdRows[0].value, 90);
    },

    /**
     * Similar to test_pushRightLeftOverlap, except the new A+C amalgam
     * does not occupy the same offset area as B.  B should be shifted left
     * regardless.
     */
    function test_pushRightLeftOverlapNoConflict(self) {
        var server = null;
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        // A
        model.insertRowData(0, [self.makeRow(12), self.makeRow(23)]);
        // B (according to test_pushRightLeftOverlap, this will be
        // shifted over to index 3...)
        model.insertRowData(25, [self.makeRow(78), self.makeRow(89)]);
        // OMEGA ("all regions to its right")
        model.insertRowData(50, [self.makeRow(90)]);
        // sanity check?
        self.assertIdentical(model._regions[2].firstOffset(), 50);
        self.assertIdentical(model._regions[1].firstOffset(), 25);

        // C
        model.insertRowData(1, [self.makeRow(23), self.makeRow(34), self.makeRow(45)]);

        var regions = model._regions;
        self.assertIdentical(regions.length, 3);
        self.assertIdentical(regions[0].firstOffset(), 0);
        self.assertIdentical(regions[1].firstOffset(), 27);
        self.assertIdentical(regions[2].firstOffset(), 52);

        var firstRows = model._regions[0].rows;
        self.assertIdentical(firstRows.length, 4);
        self.assertIdentical(firstRows[0].value, 12);
        self.assertIdentical(firstRows[1].value, 23);
        self.assertIdentical(firstRows[2].value, 34);
        self.assertIdentical(firstRows[3].value, 45);

        var secondRows = model._regions[1].rows;
        self.assertIdentical(secondRows.length, 2);
        self.assertIdentical(secondRows[0].value, 78);
        self.assertIdentical(secondRows[1].value, 89);

        var thirdRows = model._regions[2].rows;
        self.assertIdentical(thirdRows.length, 1);
        self.assertIdentical(thirdRows[0].value, 90);
    },

    /**
     * Let there be an array of rows, C, that overlaps with the beginning of
     * another region, B, and expands it to its left such that B's new offset
     * is less than the offset of the last row in a third region, A.  Let
     * there also be a region, D, to the right of B.
     *
     * Verify that upon C's insertion, the new, expanded B's offset will be
     * corrected so as to leave a gap between it and the end of A, and D's
     * offset will be corrected to leave a gap between it and the end of B.
     */
    function test_pushRightRightOverlap(self) {
        var server = null;
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        // A
        model.insertRowData(0, [self.makeRow(12), self.makeRow(23)]);
        // B (according to test_pushRightLeftOverlap, this will be
        // shifted over to index 3...)
        model.insertRowData(0, [self.makeRow(78), self.makeRow(89)]);
        // D
        model.insertRowData(0, [self.makeRow(90)]);
        // sanity check?
        self.assertIdentical(model._regions[1].firstOffset(), 3);
        self.assertIdentical(model._regions[2].firstOffset(), 6);

        // C
        model.insertRowData(1, [self.makeRow(34), self.makeRow(56), self.makeRow(78)]);

        var regions = model._regions;
        self.assertIdentical(regions.length, 3);
        self.assertIdentical(regions[0].firstOffset(), 0);
        self.assertIdentical(regions[1].firstOffset(), 3);
        self.assertIdentical(regions[2].firstOffset(), 8);

        var firstRows = model._regions[0].rows;
        self.assertIdentical(firstRows.length, 2);
        self.assertIdentical(firstRows[0].value, 12);
        self.assertIdentical(firstRows[1].value, 23);

        var secondRows = model._regions[1].rows;
        self.assertIdentical(secondRows.length, 4);
        self.assertIdentical(secondRows[0].value, 34);
        self.assertIdentical(secondRows[1].value, 56);
        self.assertIdentical(secondRows[2].value, 78);
        self.assertIdentical(secondRows[3].value, 89);

        var thirdRows = model._regions[2].rows;
        self.assertIdentical(thirdRows.length, 1);
        self.assertIdentical(thirdRows[0].value, 90);
    },

    /**
     * Verify that storing an array of rows, C, such that it causes two
     * existing regions (A and B) to be coalesced into a single contiguous
     * region, results in a region D, which is to the right of A, B, and C,
     * has its offset increased by the difference in size between the initial
     * offset gap between the end of A and the beginning of B, and the number
     * of values in C between the last value in A and the first value in B.
     */
    function test_pushRightDoubleOverlap(self) {
        var server = null;
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        // A
        model.insertRowData(0, [self.makeRow(12), self.makeRow(23)]);
        // B (according to test_pushRightLeftOverlap, this will be
        // shifted over to index 3...)
        model.insertRowData(0, [self.makeRow(45), self.makeRow(56)]);
        // D
        model.insertRowData(0, [self.makeRow(90)]);
        // sanity check
        self.assertIdentical(model._regions[2].firstOffset(), 6);
        self.assertIdentical(model._regions.length, 3);
        // C
        model.insertRowData(1, [self.makeRow(23), self.makeRow(33),
                                self.makeRow(34), self.makeRow(45)]);

        var regions = model._regions;
        // should have coalesced at this point
        self.assertIdentical(regions.length, 2);
        self.assertIdentical(regions[0].firstOffset(), 0);
        self.assertIdentical(regions[1].firstOffset(), 7);

        var firstRows = model._regions[0].rows;
        self.assertIdentical(firstRows.length, 6);
        self.assertIdentical(firstRows[0].value, 12);
        self.assertIdentical(firstRows[1].value, 23);
        self.assertIdentical(firstRows[2].value, 33);
        self.assertIdentical(firstRows[3].value, 34);
        self.assertIdentical(firstRows[4].value, 45);
        self.assertIdentical(firstRows[5].value, 56);

        var secondRows = model._regions[1].rows;
        self.assertIdentical(secondRows.length, 1);
        self.assertIdentical(secondRows[0].value, 90);
    },

    /**
     * Same as test_pushRightDoubleOverlap, but with values in a descending order.
     */
    function test_pushRightDoubleOverlapDescending(self) {
        var server = null;
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'),
            false);
        // A
        model.insertRowData(0, [self.makeRow(90), self.makeRow(89)]);
        // B (according to test_pushRightLeftOverlap, this will be
        // shifted over to index 3...)
        model.insertRowData(0, [self.makeRow(67), self.makeRow(56),
                                self.makeRow(45)]);
        // D
        model.insertRowData(0, [self.makeRow(43), self.makeRow(21)]);
        // sanity check
        self.assertIdentical(model._regions[2].firstOffset(), 7);
        self.assertIdentical(model._regions.length, 3);
        // C
        model.insertRowData(1, [self.makeRow(89), self.makeRow(78),
                                self.makeRow(67), self.makeRow(56)]);

        var regions = model._regions;
        // should have coalesced at this point
        self.assertIdentical(regions.length, 2);
        self.assertIdentical(regions[0].firstOffset(), 0);
        self.assertIdentical(regions[1].firstOffset(), 7);

        var firstRows = model._regions[0].rows;
        self.assertIdentical(firstRows.length, 6);
        self.assertIdentical(firstRows[0].value, 90);
        self.assertIdentical(firstRows[1].value, 89);
        self.assertIdentical(firstRows[2].value, 78);
        self.assertIdentical(firstRows[3].value, 67);
        self.assertIdentical(firstRows[4].value, 56);
        self.assertIdentical(firstRows[5].value, 45);

        var secondRows = model._regions[1].rows;
        self.assertIdentical(secondRows.length, 2);
        self.assertIdentical(secondRows[0].value, 43);
        self.assertIdentical(secondRows[1].value, 21);
    },

    /**
     * Similar to test_pushRightLeftOverlap, except that fewer rows are
     * inserted than would have fit into the existing gap.
     */
    function test_pullLeftDoubleOverlap(self) {
        var server = null;
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        // A
        model.insertRowData(0, [self.makeRow(12), self.makeRow(23)]);
        // B (according to test_pushRightLeftOverlap, this will be
        // shifted over to index 3...)
        model.insertRowData(0, [self.makeRow(45), self.makeRow(56)]);
        // D
        model.insertRowData(0, [self.makeRow(90)]);
        // sanity check
        self.assertIdentical(model._regions[2].firstOffset(), 6);
        self.assertIdentical(model._regions.length, 3);
        // C (as tycho would say, 'despicable continuity' or something like
        // that)
        model.insertRowData(1, [self.makeRow(23), self.makeRow(45)]);

        var regions = model._regions;
        // should have coalesced at this point
        self.assertIdentical(regions.length, 2);
        self.assertIdentical(regions[0].firstOffset(), 0);
        self.assertIdentical(regions[1].firstOffset(), 5);

        var firstRows = model._regions[0].rows;
        self.assertIdentical(firstRows.length, 4);
        self.assertIdentical(firstRows[0].value, 12);
        self.assertIdentical(firstRows[1].value, 23);
        self.assertIdentical(firstRows[2].value, 45);
        self.assertIdentical(firstRows[3].value, 56);

        var secondRows = model._regions[1].rows;
        self.assertIdentical(secondRows.length, 1);
        self.assertIdentical(secondRows[0].value, 90);
    },

    /**
     * Similar to test_pushRightLeftOverlap, except that exactly the
     * right number of rows are inserted to fill the gap, resulting in no
     * offset adjustments.
     */
    function test_stationaryDoubleOverlap(self) {
        var server = null;
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        // A
        model.insertRowData(0, [self.makeRow(12), self.makeRow(23)]);
        // B (according to test_pushRightLeftOverlap, this will be
        // shifted over to index 3...)
        model.insertRowData(0, [self.makeRow(45), self.makeRow(56)]);
        // D
        model.insertRowData(0, [self.makeRow(90)]);
        // sanity check
        self.assertIdentical(model._regions[0].firstOffset(), 0);
        self.assertIdentical(model._regions[1].firstOffset(), 3);
        self.assertIdentical(model._regions[2].firstOffset(), 6);
        self.assertIdentical(model._regions.length, 3);
        // C (as tycho would say, 'despicable continuity' or something like
        // that)
        model.insertRowData(1, [self.makeRow(23), self.makeRow(34), self.makeRow(45)]);

        var regions = model._regions;
        // should have coalesced at this point
        self.assertIdentical(regions.length, 2);
        self.assertIdentical(regions[0].firstOffset(), 0);
        self.assertIdentical(regions[1].firstOffset(), 6);

        var firstRows = model._regions[0].rows;
        self.assertIdentical(firstRows.length, 5);
        self.assertIdentical(firstRows[0].value, 12);
        self.assertIdentical(firstRows[1].value, 23);
        self.assertIdentical(firstRows[2].value, 34);
        self.assertIdentical(firstRows[3].value, 45);
        self.assertIdentical(firstRows[4].value, 56);

        var secondRows = model._regions[1].rows;
        self.assertIdentical(secondRows.length, 1);
        self.assertIdentical(secondRows[0].value, 90);
    },

    /**
     * Verify that initializing a region model against a back-end with no row
     * data causes the model to initialize with 0 rows.
     */
    function test_noRows(self) {
        var size = null;
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        model._initialize().addCallback(function (result) {
            size = result;
        });
        self.assertIdentical(size, 0);
    },

    /**
     * Verify that initializing the model multiple times before its results
     * are available will not cause additional requests to be made.
     */
    function test_racyInitialize(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        self.assertIdentical(server.requests, 0); // sanity check
        server.pause();
        model._initialize();
        self.assertIdentical(server.requests, 2);
        model._initialize();
        self.assertIdentical(server.requests, 2);
    },

    /**
     * Verify that initializing a region model against a back-end with one row
     * causes the model to _exactly_ estimate the size of the server's data as
     * '1', as well as populating an internal data structure for tracking the
     * retrieved row data.
     */
    function test_oneRow(self) {
        var size = null;
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([self.makeRow(1234)]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        model._initialize().addCallback(function (result) {
            size = result;
        });
        self.assertIdentical(size, 1);

        var index = model._rangeContainingOffset(0);
        var range = model._regions[index];
        self.assertIdentical(index, 0);
        self.assertIdentical(range.firstOffset(), 0);
        self.assertIdentical(range.rows.length, 1);
        self.assertIdentical(range.rows[0].value, 1234);
    },

    /**
     * Verify that initializing a region model against a back-end with two
     * rows with identical values causes the model to _exactly_ estimate the
     * size of the server's data as '2', as well as populating an internal
     * data structure for tracking the retrieved row data.
     */
    function test_twoRowsSameValue(self) {
        var size = null;
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer(
            [self.makeRow(1234), self.makeRow(1234)]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        model._initialize().addCallback(function (result) {
            size = result;
        });
        self.assertIdentical(size, 2);

        var index = model._rangeContainingOffset(0);
        var range = model._regions[index];
        self.assertIdentical(index, 0);
        self.assertIdentical(range.firstOffset(), 0);
        self.assertIdentical(range.rows.length, 2);
        self.assertIdentical(range.rows[0].value, 1234);
        self.assertIdentical(range.rows[1].value, 1234);
    },

    /**
     * Verify that initializing a region model against a back-end with two
     * rows with differing values causes the model to _exactly_ estimate the
     * size of the server's data as '2', as well as populating an internal
     * data structure for tracking the retrieved row data.
     */
    function test_twoRowsDifferentValues(self) {
        var size = null;
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer(
            [self.makeRow(1234), self.makeRow(5678)]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        model._initialize().addCallback(function (result) {
            size = result;
        });
        self.assertIdentical(size, 2);

        var index = model._rangeContainingOffset(0);
        var range = model._regions[index];
        self.assertIdentical(index, 0);
        self.assertIdentical(range.firstOffset(), 0);
        self.assertIdentical(range.rows.length, 2);
        self.assertIdentical(range.rows[0].value, 1234);
        self.assertIdentical(range.rows[1].value, 5678);
    },

    /**
     * Verify that lowestValue and highestValue will properly return the
     * lowest and highest values in an ascending table.
     */
    function test_lowestHighestAscending(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'),
            true);
        model.insertRowData(0, [self.makeRow(30),
                         self.makeRow(31),
                         self.makeRow(32)]);
        var theRegion = model._regions[0];
        self.assertIdentical(theRegion.firstValue(), 30);
        self.assertIdentical(theRegion.lastValue(), 32);
        self.assertIdentical(theRegion.lowestValue(), 30);
        self.assertIdentical(theRegion.highestValue(), 32);
    },


    /**
     * Verify that lowestValue and highestValue will properly return the
     * lowest and highest values in an ascending table.
     */
    function test_lowestHighestDescending(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'),
            false);
        model.insertRowData(0, [self.makeRow(32),
                         self.makeRow(31),
                         self.makeRow(30)]);
        var theRegion = model._regions[0];
        self.assertIdentical(theRegion.firstValue(), 32);
        self.assertIdentical(theRegion.lastValue(), 30);
        self.assertIdentical(theRegion.lowestValue(), 30);
        self.assertIdentical(theRegion.highestValue(), 32);
    },

    /**
     * Verify that overlapsValue will properly identify a region that is
     * sorted in descending order.
     */
    function test_descendingOverlapsValue(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'),
            false);
        model.insertRowData(0, [self.makeRow(3),
                         self.makeRow(2),
                         self.makeRow(1)]);
        var theRegion = model._regions[0];
        self.assertIdentical(theRegion.overlapsValue(2.5), true);
    },


    /**
     * Verify that when storing a range of rows with less data available than
     * the already-stored range, we do not lose any information.
     */
    function test_smallAfterBigAtStart(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'),
            true);
        model.insertRowData(0, [self.makeRow(1),
                                self.makeRow(2),
                                self.makeRow(3),
                                self.makeRow(4),
                                self.makeRow(5)]);
        model.insertRowData(0, [self.makeRow(1),
                                self.makeRow(2)]);
        self.assertIdentical(model._regions.length, 1);
        var theRegion = model._regions[0];
        // Are the values where we expect?
        self.assertIdentical(theRegion.rows.length, 5);
        self.assertIdentical(theRegion.rows[0].value, 1);
        self.assertIdentical(theRegion.rows[4].value, 5);
        // Also check to make sure the view is cleaned up.
        self.assertIdentical(self.dummyTableView.destroyed.length, 1);
    },

    /**
     * Verify that initializing a region model with a pagesize of 2 against a
     * backend with 3 rows will detect overlap between those rows and result
     * in one contiguous range.
     */
    function test_threeRowsDifferentValues(self) {
        var size = null;
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer(
            [self.makeRow(1234), self.makeRow(5678), self.makeRow(9123)]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        model._initialize().addCallback(function (result) {
            size = result;
        });
        self.assertIdentical(size, 3);

        var index = model._rangeContainingOffset(0);
        var range = model._regions[index];
        self.assertIdentical(index, 0);
        self.assertIdentical(range.firstOffset(), 0);
        self.assertIdentical(range.rows.length, 3);
        self.assertIdentical(range.rows[0].value, 1234);
        self.assertIdentical(range.rows[1].value, 5678);
        self.assertIdentical(range.rows[2].value, 9123);
    });

Mantissa.Test.TestRegionModel.DummyRegionView = Divmod.Class.subclass(
    'Mantissa.Test.TestRegionModel.DummyRegionView');
/**
 * A dummy region view which fakes out DOMRegionView in order to record
 * actions performed on it so tests can verify that appropriate notifications
 * are happening.
 */
Mantissa.Test.TestRegionModel.DummyRegionView.methods(
    /**
     * Create a view for one particular region.
     *
     * @param tableView: a L{DummyTableView} to record events on.
     *
     * @parma model: a L{RowRegion}.
     */
    function __init__(self, tableView, model) {
        self.tableView = tableView;
        self.model = model;
        self.refreshes = [];
    },

    /**
     * _pushRegionsRight needs to use this to determine pixel overlap; just
     * always return 0.
     */
    function pixelTop(self) {
        return 0;
    },

    /**
     * _pushRegionsRight needs to use this to determine pixel overlap; just
     * always return 0.
     */
    function pixelBottom(self) {
        return 0;
    },

    /**
     * Fake implementation of DOMRegionView.mergeWithRegionView.  Record the
     * participants in this merge on the L{DummyTableView}.
     *
     * @param otherDummyView: another L{DummyRegionView}.
     *
     * @param rowOffset: the local row offset.
     */
    function mergeWithRegionView(self, otherDummyView, rowOffset) {
        otherDummyView.trash();
        self.tableView.merges.push([otherDummyView, rowOffset]);
    },

    /**
     * Fake implementation of DOMRegionView.removeViewRow.  Record the fact
     * that a row was removed on the L{DummyTableView}.
     */
    function removeViewRow(self, innerOffset) {
        self.tableView.removals.push([self, innerOffset]);
    },

    /**
     * Fake implementation of DOMRegionView.refreshViewOffset.  Record the
     * fact that the view offset was refreshed on the L{DummyTableView}.
     */
    function refreshViewOffset(self) {
        self.refreshes.push(self.model.firstOffset());
    },

    /**
     * Fake implementation of DOMRegionView.destroy.  Record the fact that
     * this L{DummyRegionView} was destroyed on the L{DummyTableView}.
     */
    function destroy(self) {
        self.tableView.destroyed.push(self);
    },
    // End interface expected by regions

    /**
     * Internal method used by L{mergeWithRegionView}.  Update the
     * L{DummyTableView} to note that this region should be removed from the
     * active view, and put it into the list of regions destroyed by merges.
     */
    function trash(self) {
        for (var i = 0; i < self.tableView.regions.length; i++) {
            if (self.tableView.regions[i] === self) {
                self.tableView.regions.splice(i, 1);
                break;
            }
        }
        self.tableView.trash.push(self);
    });

Mantissa.Test.TestRegionModel.DummyTableView = Divmod.Class.subclass(
    'Mantissa.Test.TestRegionModel.DummyTableView');

Mantissa.Test.TestRegionModel.DummyTableView.methods(
    /**
     * Create a dummy scrolling table view with a given region model.
     */
    function __init__(self, test, server, column, ascending) {
        self.test = test;
        self.model = Mantissa.ScrollTable.RegionModel(
            self, server, column, ascending);
        self.regions = [];
        self.trash = [];
        self.merges = [];
        self.destroyed = [];
        self.removals = [];
    },

    /**
     * Create a new region view.
     */
    function createRegionView(self, rowRegion) {
        if (rowRegion.rows.length === 0) {
            self.test.fail("Empty regions are never allowed.");
        }
        var regview = Mantissa.Test.TestRegionModel.DummyRegionView(
            self, rowRegion);
        self.regions.push(regview);
        return regview;
    }
    );

Mantissa.Test.TestRegionModel.RegionModelViewTests =
    Divmod.UnitTest.TestCase.subclass(
        'Mantissa.Test.TestRegionModel.RegionModelViewTests');

/**
 * Tests for notifications issued by the insertRowData method of RegionModel
 * to its view.
 */
Mantissa.Test.TestRegionModel.RegionModelViewTests.methods(
    /* ad-hoc mixin - see above */
    Mantissa.Test.TestRegionModel.makeRegionModel,
    Mantissa.Test.TestRegionModel.makeRow,

    /**
     * Verify that when the first range of rows is created, it will create a
     * view for that region and populate it with appropriate rows.
     */
    function test_makeFirstRegion(self) {
         var server = Mantissa.Test.TestRegionModel.ArrayRegionServer(
             [self.makeRow(1234)]);
         var model = self.makeRegionModel(
             server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
         var view = self.dummyTableView;

         model.insertRowData(0, [self.makeRow(1234)]);

         self.assertIdentical(view.regions.length, 1);
         self.assertIdentical(view.regions[0].model.rows.length, 1);
         self.assertIdentical(view.regions[0].model.rows[0].value, 1234);
    },

    /**
     * Verify that when two disjoint ranges of values are passed to
     * insertRowData, a second region containing the new values is created.
     */
    function test_makeSecondRegion(self) {
         var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
         var model = self.makeRegionModel(
             server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
         var view = self.dummyTableView;

         model.insertRowData(0, [self.makeRow(1234), self.makeRow(2345)]);
         model.insertRowData(10, [self.makeRow(3456), self.makeRow(4567)]);

         // The view should have two disjoint regions at this point.

         self.assertIdentical(view.regions.length, 2);
         self.assertIdentical(view.regions[0].model.rows.length, 2);
         self.assertIdentical(view.regions[1].model.rows.length, 2);
         self.assertIdentical(view.regions[0].model.rows[0].value, 1234);
         self.assertIdentical(view.regions[1].model.rows[0].value, 3456);
    },

    /**
     * Verify that making a region and merging another region to the end of it
     * will result in a single region in the trash (the second one added) and
     * a correct judgement of the overlap between the second set of rows.
     */
    function test_makeOneRegionAndExtendIt(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
         var model = self.makeRegionModel(
             server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
         var view = self.dummyTableView;

         model.insertRowData(0, [self.makeRow(12), self.makeRow(23),
                          self.makeRow(34), self.makeRow(45),
                          self.makeRow(56)]);
         model.insertRowData(0, [self.makeRow(34), self.makeRow(45), self.makeRow(56),
                          self.makeRow(67), self.makeRow(78)]);
         // sanity check
         self.assertIdentical(model._regions.length, 1);
         self.assertIdentical(model._regions[0].rows.length, 7);
         self.assertIdentical(view.regions.length, 1);
         self.assertIdentical(view.trash.length, 1);
         self.assertIdentical(view.merges.length, 1);
         self.assertIdentical(view.merges[0][0], view.trash[0]);
         self.assertIdentical(view.merges[0][1], 3);
    },

    /**
     * Verify that creating two regions and then a region which overlaps with
     * them both (one at the beginning and one at the end) results in the
     * model containing only a single, contiguous region.
     */
    function test_makeTwoRegionsAndMergeThem(self) {
         var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
         var model = self.makeRegionModel(
             server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
         var view = self.dummyTableView;

         model.insertRowData(0, [self.makeRow(1234), self.makeRow(4567)]);
         model.insertRowData(10, [self.makeRow(7890), self.makeRow(8901)]);
         model.insertRowData(5, [self.makeRow(4567), self.makeRow(6789),
                          self.makeRow(7890)]);

         // the view should have a single, contiguous 1234, 4567, 6789, 7890, 8901
         self.assertIdentical(view.regions.length, 1);
         self.assertIdentical(view.regions[0].model.rows.length, 5);
         self.assertIdentical(view.trash.length, 2);
    },

    /**
     * Verify that "expose()" raises an exception when passed a negative
     * value.
     */
    function test_exposeOutOfBounds(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));

        self.assertThrows(
            Mantissa.ScrollTable.OffsetOutOfBounds,
            function () {
                model.expose(-5);
            });
    },

    /**
     * Verify that the first expose() will request data from the beginning and
     * end of the dataset.
     */
    function test_firstExpose(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer(
            [
                self.makeRow(12),
                self.makeRow(23),
                self.makeRow(34),

                self.makeRow(45),
                self.makeRow(56),
                self.makeRow(67),

                self.makeRow(78),
                self.makeRow(89),
                self.makeRow(90),
                ]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));

        // expose 2 rows at offset 0.  this should do two things:
        // 1: figure out how big the scroll table should be; i.e. initialize it
        // 2: populate all the rows that we asked to see.
        model.expose(0);
        self.assertIdentical(model._regions.length, 2);
    },

    /**
     * Verify that exposing some rows, then scrolling down to expose some
     * more, will unify the regions as expected.
     */
    function test_scrollAndExpand(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer(
            [
                self.makeRow(12),
                self.makeRow(23),

                self.makeRow(34),

                self.makeRow(89),
                self.makeRow(90),
                ]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));

        model.expose(0);     // gets 12, 23, and 89, 90. (same as _initialize)
        self.assertIdentical(model._regions.length, 2);
        model.expose(1);     // sees 23, gets 23, 34, which becomes 12, 23,
                                // 34
        self.assertIdentical(model._regions.length, 2);
        model.expose(2);     // sees 34, gets 34, 89, which connects 12, 23,
                             // 34 and 89, 90
        self.assertIdentical(model._regions.length, 1);
    },

    /**
     * Verify that if expose() receives data which completely overlaps with
     * data that it already has, it will issue another request for data which
     * is contiguous with the region that it is requesting for.
     */
    function test_exposeNotEnough(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer(
            [
                self.makeRow(12),
                self.makeRow(23),

                self.makeRow(34),
                self.makeRow(45),

                self.makeRow(890000),
                self.makeRow(900000),
                ]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        // More than one page size, but small enough that it won't be
        // considered contiguous with the first region if we move this far up
        // from the bottom.  At the time of this writing, the estimate was a
        // fixed "1000", which meant this value was always fine, but that
        // might not always be so.
        var SMALL_OFFSET_DIFF = model._pagesize * 4;

        model.expose(0);
        // Sanity check.
        self.assertIdentical(model._regions.length, 2);
        self.assertIdentical(server.requests, 2);
        server.pause();

        // Now we're going to ask for a region that will be really close to
        // the end of the (very extremely long) table; that will cause the
        // estimate to think it is "very close" to 890000, which is wrong,
        // because actually it's 45.
        var lastRegion = function () {
            return model._regions[model._regions.length - 1];
        }
        self.assertIdentical(lastRegion().rows.length, 2);
        var requestedOffset = lastRegion().firstOffset() - SMALL_OFFSET_DIFF;
        var answerDelivered = false;
        model.expose(requestedOffset).addCallback(function (result) {
            answerDelivered = true;
        });
        // That will cause us to make a request...
        self.assertIdentical(server.requests, 3);
        self.assertIdentical(server.buffer.length, 1);
        // Sanity check (this first request should not have been enough to
        // give us more data)
        server.deliverOneResult();
        self.assertIdentical(lastRegion().rows.length, 2);
        self.assertIdentical(answerDelivered, false);
        // but it will not be satisfactory, so we'll make _another_ request
        self.assertIdentical(server.buffer.length, 1);
        self.assertIdentical(server.requests, 4);
        self.assertIdentical(answerDelivered, false);
        // and when _that_ gets answered
        server.deliverOneResult();
        // the expose as a whole operation is complete
        self.assertIdentical(answerDelivered, true);
        // and there should now be some results where the user is looking
        self.assertIdentical(lastRegion().firstOffset(), requestedOffset);
        self.assertIdentical(lastRegion().rows.length, 4);
    },

    /**
     * Verify that exposing rows which are exactly on a boundary will cause
     * the region which is on the boundary to be expanded, and expanded enough
     * that the visible area is fully covered.
     */
    function test_exposeExactlyAdjacent(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer(
            [
                self.makeRow(12),
                self.makeRow(23),

                self.makeRow(34),
                self.makeRow(45),

                self.makeRow(89),
                self.makeRow(90),
                ]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));

        model.expose(0);
        self.assertIdentical(model._regions.length, 2);
        model.expose(2);
        self.assertIdentical(model._regions.length, 2);
        // Now, let's make sure it covered our entire exposed area.
         self.assertIdentical(model._regions[0].rows.length, 4);
    },

    /**
     * Verify that a row estimated exactly halfway between 1 and 0 ends up
     * being 0.5.
     */
    function test_estimateSimpleValue(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer(
            [
                self.makeRow(0),
                self.makeRow(0.25),

                self.makeRow(0.6), // This value is NOT 0.5, on purpose.

                self.makeRow(0.75),
                self.makeRow(1.0),
                ]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));

        model._initialize();    // deferred fires synchronously

        var exactlyHalfway = (
            model._regions[model._regions.length - 1].lastOffset() / 2);

        self.assertIdentical(model.estimateValueAtOffset(exactlyHalfway), 0.5);
    },

    /**
     * Verify that a row estimated exactly halfway between 1000 and 1001 ends up
     * being 1000.5.
     */
    function test_estimateSkewedValue(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer(
            [
                self.makeRow(1000),
                self.makeRow(1000.25),

                self.makeRow(1000.6), // This value is NOT 0.5, on purpose.

                self.makeRow(1000.75),
                self.makeRow(1001.0),
                ]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));

        model._initialize();    // deferred fires synchronously

        var exactlyHalfway = (
            model._regions[model._regions.length - 1].lastOffset() / 2);

        self.assertIdentical(model.estimateValueAtOffset(exactlyHalfway), 1000.5);
    },

    /**
     * Verify that a row estimated exactly 1/4 of the way between 1 and 0 ends
     * up being 0.75.
     */
    function test_estimateDifferentRatio(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer(
            [
                self.makeRow(-0.5),
                self.makeRow(0.0),

                self.makeRow(0.10),

                self.makeRow(1.0),
                self.makeRow(1.5),
                ]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));

        model._initialize();    // deferred fires synchronously

        self.assertIdentical(model._regions.length, 2);

        var firstRegion = model._regions[0];
        var lastRegion = model._regions[1];
        var threeQuarterOffset = (((lastRegion.firstOffset() - firstRegion.lastOffset()) /
                                  4) * 3) + firstRegion.lastOffset();

        self.assertIdentical(
            model.estimateValueAtOffset(threeQuarterOffset),
            0.75);
    },

    /**
     * L{Mantissa.ScrollTable.TextColumn.estimateQueryValue} should yield a
     * string proportionally between two alphabetical values.
     */
    function test_estimateTextQueryValue(self) {
        var column = Mantissa.ScrollTable.TextColumn();
        self.assertIdentical(
            column.estimateQueryValue('A', 'Z', 0.75),
            String.fromCharCode(
                'a'.charCodeAt(0) +
                    ((('z'.charCodeAt(0) - 'a'.charCodeAt(0)) / 4) * 3)));
    },

    /**
     * L{Mantissa.ScrollTable.TextColumn.estimateQueryValue} should skip the
     * capital letters when estimating between characters which come before
     * the range of capital letters.
     */
    function test_estimateTextQueryValueSkipCase(self) {
        var column = Mantissa.ScrollTable.TextColumn();
        self.assertIdentical(
            column.estimateQueryValue('@', 'n', 0.5),
            'd');
        self.assertIdentical(
            column.estimateQueryValue('0', '9', 0.5),
            '4');
    },

    /**
     * L{Mantissa.ScrollTable.TextColumn.estimateQueryValue} should pad out
     * its lower argument in the case where it is given adjacent strings,
     * i.e. strings where the difference is exactly one code point.  (It can't
     * use NULLs to pad out the result (SQLite doesn't recognize them), so it
     * should use \N{START OF HEADING}, code point 1).
     */
    function test_estimateAdjacentTextValue(self) {
        var column = Mantissa.ScrollTable.TextColumn();
        self.assertIdentical(
            column.estimateQueryValue('person 100', 'person 2', 0.5),
            "person 100\u0001");
        self.assertIdentical(
            column.estimateQueryValue('person 2', 'person 100', 0.5),
            "person 100\u0001");
    },

    /**
     * L{Mantissa.ScrollTable.TextColumn.estimateQueryValue} should give back
     * an extended version of one of its arguments in the case where one of
     * its arguments is a prefix of the other.
     */
    function test_estimatePrefixTextValue(self) {
        var column = Mantissa.ScrollTable.TextColumn();
        self.assertIdentical(
            column.estimateQueryValue('0123456789', '012345', 0.5),
            "01234567");
        self.assertIdentical(
            column.estimateQueryValue('012345', '0123456789', 0.5),
            "01234567");
        self.assertIdentical(
            column.estimateQueryValue('012345', '0123456789', 0.9999),
            "012345678");
        self.assertIdentical(
            column.estimateQueryValue('012345', '0123456789', 0.0001),
            "0123456");
        self.assertIdentical(
            column.estimateQueryValue('0123456789', '012345', 0.9999),
            "0123456");
        self.assertIdentical(
            column.estimateQueryValue('0123456789', '012345', 0.0001),
            "012345678");
    },

    /**
     * L{Mantissa.ScrollTable.TextColumn}'s sort values should be lower-cased
     * according to SQLite's simplistic algorithm - a simple conversion of
     * uppercase latin letters to lowercase, not full case conversion.
     */
    function test_extractTextSortKey(self) {
        self.assertIdentical(
            Mantissa.ScrollTable.TextColumn('value').extractSortKey(
                {value: 'A VALue\u00F8\u00D8'}),
            'a value\u00F8\u00D8');
    },

    /**
     * L{Mantissa.ScrollTable.RegionModel.estimateValueAtOffset} should work
     * correctly with L{Mantissa.ScrollTable.TextColumn}.
     */
    function test_estimateTextValue(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer(
            [self.makeRow('AA'),
             self.makeRow('AB'),

             self.makeRow('AY'),
             self.makeRow('AZ')
             ]);
        var model = self.makeRegionModel(
            server, Mantissa.ScrollTable.TextColumn('value'));
        model._initialize();
        var firstRegion = model._regions[0];
        var lastRegion = model._regions[1];
        var halfwayOffset = ((lastRegion.firstOffset() - firstRegion.lastOffset()) /
                                  2) + firstRegion.lastOffset();
        var ordB = 'b'.charCodeAt(0);
        var halfwayChar = String.fromCharCode(
            ordB + (('y'.charCodeAt(0) - ordB) / 2)); // 'm'
        self.assertIdentical(
            model.estimateValueAtOffset(halfwayOffset), 'a' + halfwayChar);
    },

    /**
     * Verify that scrolling to the middle of an empty region will result in a
     * request for some rows at the appropriate offset.
     */
    function test_scrollToMiddle(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer(
            [
                self.makeRow(10),
                self.makeRow(20),

                self.makeRow(33),
                self.makeRow(34),
                self.makeRow(35),

                self.makeRow(80),
                self.makeRow(90),
                ]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));

        // Expose a region  very close to the top, but  not quite touching the
        // top region.  Because it's only got  2 rows, it won't be long enough
        // to touch the 3rd region.
        model.expose(3);

        // There should be a third, floating middle region now.
        self.assertIdentical(model._regions.length, 3);
    },

    /**
     * Verify that scrolling to the middle of an empty region when the table
     * is descending will result in a request for some rows at the appropriate
     * offset and a new, independent region.
     */
    function test_scrollToMiddleDescending(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer(
            [
                self.makeRow(10),
                self.makeRow(20),

                self.makeRow(33),
                self.makeRow(34),
                self.makeRow(35),

                self.makeRow(80),
                self.makeRow(90),
                ]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'),
            false);

        // Expose a region very close to the top, but not quite touching the
        // top region.  Because it's only got 2 rows, it won't be long enough
        // to touch the 3rd region.
        model.expose(3);

        // There should be a third, floating middle region now.
        self.assertIdentical(model._regions.length, 3);
    },

    /**
     * Verify that an expose call which is contiguous with the initial region
     * in a descending table will request rows contiguous with the first
     * region.
     */
    function test_scrollDownALittleDescending(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer(
            [
                self.makeRow(10),
                self.makeRow(20),

                self.makeRow(33),
                self.makeRow(34),
                self.makeRow(35),

                self.makeRow(80),
                self.makeRow(90),
                ]);

        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'),
            false);

        model.expose(1);
        self.assertIdentical(model._regions.length, 2);
        self.assertIdentical(model._regions[0].rows.length, 3);
        self.assertIdentical(model._regions[0].rows[0].value, 90);
        self.assertIdentical(model._regions[0].rows[1].value, 80);
        self.assertIdentical(model._regions[0].rows[2].value, 35);
    },

    /**
     * Verify that an expose call which is exactly contiguous with the initial
     * region in a descending table will request rows contiguous with the
     * first region.
     */
    function test_scrollDownExactlyOnePageDescending(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer(
            [
                self.makeRow(10),
                self.makeRow(20),

                self.makeRow(33),
                self.makeRow(34),
                self.makeRow(35),

                self.makeRow(80),
                self.makeRow(90),
                ]);

        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'),
            false);

        model.expose(2);
        self.assertIdentical(model._regions.length, 2);
        self.assertIdentical(model._regions[0].rows.length, 4);
        self.assertIdentical(model._regions[0].rows[0].value, 90);
        self.assertIdentical(model._regions[0].rows[1].value, 80);
        self.assertIdentical(model._regions[0].rows[2].value, 35);
        self.assertIdentical(model._regions[0].rows[3].value, 34);
    },

    /**
     * Verify that exposing rows that already exist in the model does not make
     * any requests of the server.
     */
    function test_exposeExistingRows(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer(
            [
                self.makeRow(10),
                self.makeRow(20),

                self.makeRow(33),
                self.makeRow(34),
                self.makeRow(35),

                self.makeRow(80),
                self.makeRow(90),
                ]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        model.expose(0);
        self.assertIdentical(server.requests, 2);
        model.expose(0);
        self.assertIdentical(server.requests, 2);
        self.assertIdentical(model._regions.length, 2);
        // Now check the end of the table as well just to be sure.
        model.expose(model._regions[1].firstOffset());
        self.assertIdentical(server.requests, 2);
        self.assertIdentical(model._regions.length, 2);
    },

    /**
     * Verify that getRowIndices returns the indices of all rows that have
     * been fetched.
     */
    function test_getRowIndices(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(server,
                                         Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        model.insertRowData(0, [self.makeRow(1), self.makeRow(2), self.makeRow(3)]);
        model.insertRowData(500, [self.makeRow(4), self.makeRow(5), self.makeRow(6)]);

        var indices = model.getRowIndices();
        self.assertIdentical(indices.length, 6);
        self.assertIdentical(indices[0], 0);
        self.assertIdentical(indices[1], 1);
        self.assertIdentical(indices[2], 2);
        self.assertIdentical(indices[3], 500);
        self.assertIdentical(indices[4], 501);
        self.assertIdentical(indices[5], 502);
    },

    /**
     * Verify that findRowData returns the data for the row at the index it is
     * passed.
     */
    function test_findRowData(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(
            server,
            Mantissa.Test.TestRegionModel.SkewedColumn('value'));

        model.insertRowData(0, [self.makeRow(1), self.makeRow(2), self.makeRow(3)]);
        model.insertRowData(500, [self.makeRow(4), self.makeRow(5), self.makeRow(6)]);

        var rowData = model.findRowData(model._regions[0].rows[0].__id__);
        self.assertIdentical(rowData.value, 1);

        rowData = model.findRowData(model._regions[1].rows[2].__id__);
        self.assertIdentical(rowData.value, 6);
    },

    /**
     * followsRegion should determine the value ordering relationship between
     * two regions.
     */
    function test_followsRegion(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(
            server,
            Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        model.insertRowData(0, [self.makeRow(1), self.makeRow(2)]);
        model.insertRowData(0, [self.makeRow(3), self.makeRow(4)]);
        var reg1 = model._regions[0];
        var reg2 = model._regions[1];

        self.assertIdentical(reg2.followsRegion(reg1), true);
        self.assertIdentical(reg1.followsRegion(reg2), false);
        self.assertIdentical(reg1.followsRegion(reg1), false);
        self.assertIdentical(reg2.followsRegion(reg2), false);

        var reg1merge = Mantissa.ScrollTable.RowRegion(
            model, 0, [self.makeRow(2), self.makeRow(2.5)]);

        // Overlapping regions should be merged, so they should *not* be
        // considered 'following'.
        self.assertIdentical(reg1merge.followsRegion(reg1), false);

        // But regions which haven't yet been inserted should be able to be
        // compared.
        self.assertIdentical(reg2.followsRegion(reg1merge), true);
    },

    /**
     * followsRegion should determine the value ordering relationship between
     * two regions dependent upon sort ordering.
     */
    function test_followsRegionDescending(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(
            server,
            Mantissa.Test.TestRegionModel.SkewedColumn('value'), false);
        model.insertRowData(0, [self.makeRow(4), self.makeRow(3)]);
        model.insertRowData(0, [self.makeRow(2), self.makeRow(1)]);
        var reg1 = model._regions[0];
        var reg2 = model._regions[1];

        self.assertIdentical(reg2.followsRegion(reg1), true);
        self.assertIdentical(reg1.followsRegion(reg2), false);
        self.assertIdentical(reg1.followsRegion(reg1), false);
        self.assertIdentical(reg2.followsRegion(reg2), false);
        var reg1merge = Mantissa.ScrollTable.RowRegion(
            model, 0, [self.makeRow(3), self.makeRow(2.5)]);

        // Overlapping regions should be merged, so they should *not* be
        // considered 'following'.
        self.assertIdentical(reg1merge.followsRegion(reg1), false);

        // But regions which haven't yet been inserted should be able to be
        // compared.
        self.assertIdentical(reg2.followsRegion(reg1merge), true);
    },

    /**
     * Verify that getRowData returns the data for the row at the index it is
     * passed.
     */
    function test_getRowData(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));

        model.insertRowData(0, [self.makeRow(1),
                                self.makeRow(2),
                                self.makeRow(3)]);

        model.insertRowData(500, [self.makeRow(4),
                                  self.makeRow(5),
                                  self.makeRow(6)]);

        var rowData = model.getRowData(0);
        self.assertIdentical(rowData.value, 1);

        rowData = model.getRowData(502);
        self.assertIdentical(rowData.value, 6);
    },

    /**
     * Make a region model with five rows and the given ascending-ness.
     */
    function _makeSimpleModel(self, ascending/*= true*/, rowcount/*= 5*/) {
        var rows = [];
        if (rowcount === undefined) {
            rowcount = 5;
        }
        for (var i = 0; i < rowcount; i++) {
            rows.push(self.makeRow(i+1));
        }
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer(rows);
        return self.makeRegionModel(
            server,
            Mantissa.Test.TestRegionModel.SkewedColumn('value'),
            ascending);
    },

    /**
     * Verify that rowsFollowingRow will retrieve the appropriate rows from
     * the server when the sort-order is ascending.
     */
    function test_rowsFollowingRow(self) {
        var model = self._makeSimpleModel();
        var capture = null;
        model.rowsFollowingRow(self.makeRow(3)).addCallback(
            function (result) {
                capture = result;
            });
        self.assertIdentical(capture.length, 2); // pagesize
        self.assertIdentical(capture[0].value, 3);
        self.assertIdentical(capture[0].__TEMPORARY__, true);
        self.assertIdentical(capture[1].value, 4);
        self.assertIdentical(capture[1].__TEMPORARY__, undefined);
    },

    /**
     * Verify that rowsFollowingRowAtOffset will retrieve the appropriate rows
     * from the server when the sort-order is descending.
     */
    function test_rowsFollowingRowDescending(self) {
        var model = self._makeSimpleModel(false);
        var capture = null;
        model.rowsFollowingRow(self.makeRow(3)).addCallback(
            function (result) {
                capture = result;
            });
        self.assertIdentical(capture.length, 2); // pagesize
        self.assertIdentical(capture[0].value, 3);
        self.assertIdentical(capture[0].__TEMPORARY__, true);
        self.assertIdentical(capture[1].value, 2);
        self.assertIdentical(capture[1].__TEMPORARY__, undefined);
    },

    /**
     * Verify that L{Mantissa.ScrollTable.RegionModel.rowsPrecedingRow} will
     * retrieve the appropriate rows from the server when the sort-order is
     * ascending.
     */
    function test_rowsPrecedingRow(self) {
        var model = self._makeSimpleModel(true, 7);
        // 3 is the minimum page size where you can verify the interactions
        // with the sort requested of the server, because if you ask for a
        // pagesize of 2 then only 1 result comes back from the server, no
        // ordering...
        model._pagesize = 3;
        var capture;
        model.rowsPrecedingRow(self.makeRow(5)).addCallback(
            function(result) {
                capture = result;
            });
        self.assertIdentical(capture.length, 3);
        self.assertIdentical(capture[0].value, 3);
        self.assertIdentical(capture[0].__TEMPORARY__, undefined);
        self.assertIdentical(capture[1].value, 4);
        self.assertIdentical(capture[1].__TEMPORARY__, undefined);
        self.assertIdentical(capture[2].value, 5);
        self.assertIdentical(capture[2].__TEMPORARY__, true);
    },

    /**
     * Verify that L{Mantissa.ScrollTable.RegionModel.rowsPrecedingRow} will
     * retrieve the appropriate rows from the server when the sort-order is
     * descending.
     */
    function test_rowsPrecedingRowDescending(self) {
        var model = self._makeSimpleModel(false, 7);
        model._pagesize = 3;
        var capture;
        model.rowsPrecedingRow(self.makeRow(3)).addCallback(
            function(result) {
                capture = result;
            });
        self.assertIdentical(capture.length, 3);
        self.assertIdentical(capture[0].value, 5);
        self.assertIdentical(capture[0].__TEMPORARY__, undefined);
        self.assertIdentical(capture[1].value, 4);
        self.assertIdentical(capture[1].__TEMPORARY__, undefined);
        self.assertIdentical(capture[2].value, 3);
        self.assertIdentical(capture[2].__TEMPORARY__, true);
    },

    /**
     * L{Mantissa.ScrollTable.RowRegion.coalesceAtMyEnd} should notice if the
     * region "on top" ends with a temporary row, and remove that row from the
     * resulting coalesced data.
     */
    function test_insertTemporaryRowAbove(self) {
        var model = self._makeSimpleModel(false, 7);
        model._pagesize = 3;
        var capture;
        model.rowsPrecedingRow(self.makeRow(4)).addCallback(
            function (result) {
                capture = result;
            });
        var realRegion = Mantissa.ScrollTable.RowRegion(
            model, 2, [self.makeRow(4), self.makeRow(3), self.makeRow(2)]);
        var newRegionWithTemp = Mantissa.ScrollTable.RowRegion(
            model, 0, capture);
        self.assertIdentical(
            newRegionWithTemp.rows[newRegionWithTemp.rows.length - 1].__TEMPORARY__, true);
        newRegionWithTemp.coalesceAtMyEnd(realRegion);
        for (var i = 0; i < newRegionWithTemp.rows.length; i++) {
            self.assertIdentical(newRegionWithTemp.rows[i].__TEMPORARY__, undefined);
        }
        // The view should have had its temporary row purged as well.
        self.assertIdentical(model.view.removals.length, 1);
        self.assertIdentical(model.view.removals[0][0], newRegionWithTemp.viewPeer);
        self.assertIdentical(model.view.removals[0][1], 2);
    },

    /**
     * L{Mantissa.ScrollTable.RowRegion.coalesceAtMyEnd} should notice if the
     * region "on the bottom" begins with a temporary row, and remove that row
     * from the resulting coalesced data.
     */
    function test_insertTemporaryRowBelow(self) {
        var model = self._makeSimpleModel(false, 7);
        model._pagesize = 3;
        var capture;
        model.rowsFollowingRow(self.makeRow(4)).addCallback(
            function (result) {
                capture = result;
            });
        var realRegion = Mantissa.ScrollTable.RowRegion(
            model, 2, [self.makeRow(6), self.makeRow(5), self.makeRow(4)]);
        var newRegionWithTemp = Mantissa.ScrollTable.RowRegion(
            model, 0, capture);
        self.assertIdentical(newRegionWithTemp.rows[0].__TEMPORARY__, true);
        realRegion.coalesceAtMyEnd(newRegionWithTemp);
        for (var i = 0; i < realRegion.rows.length; i++) {
            self.assertIdentical(realRegion.rows[i].__TEMPORARY__, undefined);
        }
    },

    /**
     * Verify that rowsFollowingValue will retrieve the appropriate rows from
     * the server when the sort-order is ascending.
     */
    function test_rowsFollowingValue(self) {
        var model = self._makeSimpleModel();
        var capture = null;
        model.rowsFollowingValue(3).addCallback(
            function (result) {
                capture = result;
            });
        self.assertIdentical(capture.length, 2); // pagesize
        self.assertIdentical(capture[0].value, 3);
        self.assertIdentical(capture[1].value, 4);
    },

    /**
     * Verify that rowsFollowingValue will retrieve the appropriate rows from
     * the server when the sort-order is descending.
     */
    function test_rowsFollowingValueDescending(self) {
        var model = self._makeSimpleModel(false);
        var capture = null;
        model.rowsFollowingValue(3).addCallback(
            function (result) {
                capture = result;
            });
        self.assertIdentical(capture.length, 2); // pagesize
        self.assertIdentical(capture[0].value, 3);
        self.assertIdentical(capture[1].value, 2);
    },

    /**
     * Verify that the data initially requested from the server will be placed
     * into appropriate regions if the sort order is descending.
     */
    function test_initializeRespectsDescending(self) {
        var model = self._makeSimpleModel(false);
        model._initialize();    // deferred fires synchronously
        // Some sanity checks...
        self.assertIdentical(model._regions.length, 2);
        self.assertIdentical(model._regions[0].rows.length, 2);
        self.assertIdentical(model._regions[1].rows.length, 2);
        // And now, make sure it's actually descending...
        self.assertIdentical(model._regions[0].rows[0].value, 5);
        self.assertIdentical(model._regions[1].rows[1].value, 1);
    },

    /**
     * Verify that getRowData handles out-of-bounds indices correctly.
     */
    function test_getRowDataOOB(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));

        self.assertThrows(
            Divmod.IndexError,
            function() {
                model.getRowData(0);
            });
        self.assertThrows(
            Divmod.IndexError,
            function() {
                model.getRowData(-1);
            });

        /* check that the return value is undefined if the index isn't out of
           bounds but a row isn't found */
        model.insertRowData(0, [self.makeRow(1), self.makeRow(2), self.makeRow(3)]);
        model.insertRowData(500, [self.makeRow(4), self.makeRow(5), self.makeRow(6)]);

        self.assertIdentical(model.getRowData(499), undefined);
    },

    /**
     * Verify that findIndex correctly returns the index of the row with the
     * given web ID.
     */
    function test_findIndex(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));

        model.insertRowData(0, [self.makeRow(1), self.makeRow(2), self.makeRow(3)]);
        model.insertRowData(500, [self.makeRow(4), self.makeRow(5), self.makeRow(6)]);

        var rowIndex = model.findIndex(model._regions[0].rows[0].__id__);
        self.assertIdentical(rowIndex, 0);
        rowIndex = model.findIndex(model._regions[1].rows[0].__id__);
        self.assertIdentical(rowIndex, 500);
    },

    /**
     * Verify that findIndex correctly handles the case where the given webID
     * does not correspond to a row that has been fetched.
     */
    function test_findIndexBadWebID(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        self.assertThrows(
            Mantissa.ScrollTable.NoSuchWebID,
            function() {
                model.findIndex('not really a web id');
            });
    },


    /**
     * Verify that rowCount really returns the number of rows that have been
     * retrieved.
     */
    function test_rowCount(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));

        self.assertIdentical(model.rowCount(), 0);
        model.insertRowData(0, [self.makeRow(1), self.makeRow(2), self.makeRow(3)]);
        self.assertIdentical(model.rowCount(), 3);
        model.insertRowData(500, [self.makeRow(4), self.makeRow(5), self.makeRow(6)]);
        self.assertIdentical(model.rowCount(), 6);
    },
    function _makeFakeNode(self, widgetID) {
        var el = document.createElement("span");
        el.id = 'athena:'+widgetID;
        el.scrollTop = 0;
        return el;
    },

    /**
     * Verify that the ScrollTable widget will correctly construct column
     * objects depending on the types of the attributes it is passed
     */
    function test_columnTypeDispatch(self) {
        var fakeNode = self._makeFakeNode('1');

        var myScrollTable = Mantissa.ScrollTable.ScrollTable(
            fakeNode, 'value', [
                {name: 'value', type: 'integer'},
                {name: 'name', type: 'text'},
                {name: 'truefalse', type: 'boolean'},
                {name: 'datetime', type: 'timestamp'},
                {name: 'thingy', type: 'widget'}
                ]);

        self.assert(
            myScrollTable.columns['value'] instanceof
            Mantissa.ScrollTable.IntegerColumn);
        self.assert(
            myScrollTable.columns['name'] instanceof
            Mantissa.ScrollTable.TextColumn);
        self.assert(
            myScrollTable.columns['truefalse'] instanceof
            Mantissa.ScrollTable.BooleanColumn);
        self.assert(
            myScrollTable.columns['datetime'] instanceof
            Mantissa.ScrollTable.TimestampColumn);
        self.assert(
            myScrollTable.columns['thingy'] instanceof
            Mantissa.ScrollTable.WidgetColumn);

        self.assertIdentical(
            myScrollTable.columns['value'], myScrollTable.sortColumn);

        var columnCount = 0;
        for(var k in myScrollTable.columns) {
            columnCount++;
        }
        self.assertIdentical(columnCount, 5);
    },

    /**
     * Verify that the RegionModel will remove all of its rows and tell the
     * view to remove all of its regions when asked to empty itself.
     */
    function test_empty(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));

        model.insertRowData(0, [self.makeRow(1), self.makeRow(2), self.makeRow(3)]);
        model.insertRowData(500, [self.makeRow(4), self.makeRow(5), self.makeRow(6)]);

        model.empty();
        self.assertIdentical(model._regions.length, 0);
        self.assertIdentical(model._initialized, false);
        self.assertIdentical(self.dummyTableView.destroyed.length, 2);
    },

    /**
     * Verify that removing a row will eliminate its data from both the model
     * and the view.
     */
    function test_removeRow(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        model.insertRowData(0, [self.makeRow(1), self.makeRow(2), self.makeRow(3)]);
        model.insertRowData(500, [self.makeRow(4), self.makeRow(5), self.makeRow(6)]);
        model.insertRowData(1000, [self.makeRow(7), self.makeRow(8), self.makeRow(9)]);
        model.removeRow(0);
        model.removeRow(500);
        self.assertIdentical(model._regions[0].rows.length, 2);
        self.assertIdentical(model._regions[1].rows.length, 2);
        self.assertIdentical(model._regions[2].rows.length, 3);
        self.assertIdentical(self.dummyTableView.removals.length, 2);
        self.assertIdentical(self.dummyTableView.removals[0][0],
                             model._regions[0].viewPeer);
        self.assertIdentical(self.dummyTableView.removals[1][0],
                             model._regions[1].viewPeer);
        // Should the model also shift the other regions' offsets?
    },

    /**
     * Verify that removing the last row from a region will delete the region
     * entirely.
     */
    function test_removeLastRow(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        model.insertRowData(0, [self.makeRow(1)]);
        model.removeRow(0);
        self.assertIdentical(model._regions.length, 0);
    },

    /**
     * Verify that adjusting a region's offset will change its offset and
     * update its view peer.
     */
    function test_adjustRefreshesView(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));
        model.insertRowData(0, [self.makeRow(1)]);
        model._regions[0].adjustOffset(10);
        var refreshes = model._regions[0].viewPeer.refreshes;
        self.assertIdentical(refreshes.length, 1);
        self.assertIdentical(refreshes[0], 10);
    },

    /**
     * When a region is inserted which overlaps visually with the next region,
     * but does not overlap its offset, it should still tell the region view
     * to adjust its view offset.
     */
    function test_visualOverlapWithoutOffsetOverlap(self) {
        var server = Mantissa.Test.TestRegionModel.ArrayRegionServer([]);
        var model = self.makeRegionModel(
            server, Mantissa.Test.TestRegionModel.SkewedColumn('value'));

        var realView = model.view;
        model.view = {
          createRegionView: function (rowReg) {
                var viewReg = realView.createRegionView(rowReg);
                var pixTop = this.pixTop;
                var pixBot = this.pixBot;
                viewReg.pixelTop = function () {
                    return pixTop;
                };
                viewReg.pixelBottom = function () {
                    return pixBot;
                };
                return viewReg;
            }
        };
        var LAST_REGION_OFFSET = 10;
        model.view.pixTop = 50;
        model.view.pixBot = 100;
        model.insertRowData(LAST_REGION_OFFSET, [self.makeRow(2)]);

        model.view.pixTop = 0;
        model.view.pixBot = 13;
        model.insertRowData(0, [self.makeRow(1)]);

        // The region below should NOT have been adjusted yet, since this was
        // not visually tall enough.

        // sanity check
        self.assertIdentical(model._regions.length, 2);
        // real assertion
        self.assertIdentical(model._regions[1].viewPeer.refreshes.length, 0);

        // Now let's move it.
        model.view.pixTop = 15;
        model.view.pixBot = 1000;
        model.insertRowData(3, [self.makeRow(1.5)]);

        // sanity check
        self.assertIdentical(model._regions.length, 3);
        // it was adjusted
        self.assertIdentical(model._regions[2].viewPeer.refreshes.length, 1);
        // but only visually, no offset change
        self.assertIdentical(model._regions[2].viewPeer.refreshes[0],
                             LAST_REGION_OFFSET);
    });



Mantissa.Test.TestRegionModel.TestableWidget =
    Mantissa.ScrollTable.ScrollingWidget.subclass(
        "Mantissa.Test.TestRegionModel.TestableWidget");
/**
 * Testable version of the ScrollingWidget class that provides fake
 * implementations of a few methods whose implementations have tight
 * dependencies on browser functionality or templates.
 */

Mantissa.Test.TestRegionModel.TestableWidget.methods(
    /**
     * Always return a 'dummy' element that has been added to the document
     * when asked for a node by attribute.
     */
    function nodeByAttribute(self, attributeName, attributeValue) {
        var el = document.createElement("dummy");
        self.node.appendChild(el);
        return el;
    },

    /**
     * Respond to every remote call by returning the empty list, since none of
     * the tests which use this class expect responses.
     */
    function callRemote(self) {
        return Divmod.Defer.succeed([]);
    });

Mantissa.Test.TestRegionModel.LegacyDOMTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestRegionModel.LegacyDOMTests');

/**
 * Unit Tests for DOM manipulation logic in the old-style index-based
 * ScrollableWidget and related components.
 */

Mantissa.Test.TestRegionModel.LegacyDOMTests.methods(
    /**
     * Set up a ScrollingWidget instance to verify legacy behavior against.
     */
    function setUp(self) {
        self.fakeNode = document.createElement("table");
        self.fakeNode.id = 'athena:1';
        document.body.appendChild(self.fakeNode);
        var metadata = [
            // columnNames
            ["value"],
            // columnTypes
            {value: "integer"},
            // rowCount
            10,
            // currentSort
            "value",
            // isAscendingNow
            true];
        self.table = Mantissa.Test.TestRegionModel.TestableWidget(
            self.fakeNode, metadata);
    },

    /**
     * Verify that old (placeholder-based) scrolling widgets create table rows
     * by default for their row nodes.
     */
    function test_oldMakeRowElement(self) {
        var re = self.table.makeRowElement(0, [], []);
        self.assertIdentical(re.tagName, "TR");
        self.assertIdentical(re.getAttribute("class"), "scroll-row");
    },

    /**
     * Verify that old (placeholder-based) scrolling widgets create table
     * cells by default for their cell nodes.
     */
    function test_oldMakeCellElement(self) {
        var ce = self.table.makeCellElement('value', "hello");
        self.assertIdentical(ce.tagName, 'TD');
    },

    /**
     * L{Mantissa.ScrollTable._ScrollingBase._makeActionsCells} should return a
     * TD element with action names separated by spaces as children.
     */
    function test_makeActionsCells(self) {
        self.table.actions = [
            Mantissa.ScrollTable.Action('foo', 'Foo'),
            Mantissa.ScrollTable.Action('bar', 'Bar')];
        var actionsCells = self.table._makeActionsCells({});
        self.assertIdentical(actionsCells.tagName, 'TD');
        self.assertIdentical(actionsCells.childNodes.length, 3);
        self.assertIdentical(actionsCells.childNodes[0].tagName, 'A');
        self.assertIdentical(actionsCells.childNodes[0].childNodes.length, 1);
        self.assertIdentical(actionsCells.childNodes[0].childNodes[0].nodeValue, 'Foo');
        self.assertIdentical(actionsCells.childNodes[1].nodeValue, ' ');
        self.assertIdentical(actionsCells.childNodes[2].tagName, 'A');
        self.assertIdentical(actionsCells.childNodes[2].childNodes.length, 1);
        self.assertIdentical(actionsCells.childNodes[2].childNodes[0].nodeValue, 'Bar');
    },

    /**
     * L{Mantissa.ScrollTable._ScrollingBase._makeActionsCells} should return a
     * TD element with no child nodes if there are no actions.
     */
    function test_makeNoActionsCells(self) {
        self.table.actions = [];
        var actionsCells = self.table._makeActionsCells({});
        self.assertIdentical(actionsCells.tagName, 'TD');
        self.assertIdentical(actionsCells.childNodes.length, 0);
    });

Mantissa.Test.TestRegionModel.RegionDOMTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestRegionModel.RegionDOMTests');

/**
 * Test cases for DOM manipulation within DOMRegionView and its associated
 * components.
 */

Mantissa.Test.TestRegionModel.RegionDOMTests.methods(

    /**
     * Set up a ScrollTable instance to trigger DOM manipulations on, and
     * adjust global Nevow state so that events can be processed.
     */
    function setUp(self) {
        self.table = self.makeFakeTable();
        self.unmock = Nevow.Test.WidgetUtil.mockTheRDM();
        self.originalWidget = Nevow.Athena.Widget._athenaWidgets['1'];
        Nevow.Athena.Widget._athenaWidgets['1'] = self.table;
    },


    /**
     * Re-adjust global Nevow state so that events to the state it was in
     * before this test ran, so that this test will run properly in
     * environments that may initialize more properly than nevow.
     */
    function tearDown(self) {
        self.unmock();
        Nevow.Athena.Widget._athenaWidgets['1'] = self.originalWidget;
    },

    /**
     * L{Mantissa.ScrollTable.DOMRegionView._makeNodeForRows} should create an
     * empty node for rows that are marked as temporary.
     */
    function test_temporaryRowNode(self) {
        var fakeTableView = {
          node: document.createElement('div'),
          _getRowHeight: function () {
                return 3;
            }
        };
        var fakeRowRegion = {
          rows: [{__TEMPORARY__: true}],
          firstOffset: function () {
                return 0;
            },
          previousRegion: function () {
                return undefined;
            }
        };

        // This test _intentionally_ does not invoke the entire operation of
        // rowsFollowingRow -> insertRowData -> createRegionView, because by
        // the end of that sequence of events, the fake row _always_ should
        // have been removed from the actual DOM.

        var regionView = Mantissa.ScrollTable.DOMRegionView(
            fakeTableView, fakeRowRegion);
        var regionNode = fakeTableView.node.childNodes[0];
        self.assertIdentical(regionNode.childNodes.length, 1);
        var rowNode = regionNode.childNodes[0].childNodes[0];
        //                       ^ rows container node
        self.assertIdentical(rowNode.className, "row-temporary-placeholder");
    },

    /**
     * Verify that the ScrollTable widget's C{visiblePixelTop} method returns
     * the vertical offset of the node's scrollbar.
     */
    function test_visiblePixelTop(self) {
        self.table.node.scrollTop = 131;
        self.assertIdentical(self.table.visiblePixelTop(), 131);
    },

    /**
     * Verify that the ScrollTable widget's C{visiblePixelHeight} method
     * returns the actual height of the node.
     */
    function test_visiblePixelHeight(self) {
        self.table.node.style.height = "133px";
        self.assertIdentical(self.table.visiblePixelHeight(), 133);
    },

    /**
     * Verify that the ScrollTable widget will hook up scrolling event
     * handlers to its DOM node upon initialization.
     */
    function test_onscrollHookup(self) {
        var exposures = [];
        var exposeDeferred = Divmod.Defer.Deferred();
        self.table.model = {
          expose: function (rowOffset) {
                if (exposures === undefined) {
                    exposures = [];
                }
                exposures.push(rowOffset);
                return exposeDeferred;
            },
          _regions: []          // needed by handler to compute offsets
        };
        document.body.appendChild(self.table.node);

        self.table.node.scrollTop = 0;
        self.table.node.onscroll();

        /* Nothing should happen immediately */
        self.assertIdentical(exposures.length, 0);

        self.table.flushCallLaters();

        /* Make sure that the scroll event is actually hooked up. */
        self.assertIdentical(exposures.length, 1);
        self.assertIdentical(exposures[0], 0);

        // Let's go and grab the 'loading...' node...
        var loadingNode = self.table.node.childNodes[
            self.table.node.childNodes.length - 1];
        // Sanity check.
        self.assertIdentical(loadingNode.className, "scrolltable-loading");
        self.assertIdentical(loadingNode.parentNode, self.table.node);

        // Now allow the loading to complete by firing the 'expose' Deferred.
        exposeDeferred.callback(null);
        // Make sure it's been removed.
        self.assertIdentical(loadingNode.parentNode, null);
    },

    /**
     * A ScrollTable should display a "Loading..." throbber until the initial
     * set of rows has finished being requested.
     */
    function test_initialLoad(self) {
        // We can't use the default table, it's already been loaded.
        var unloaded = self.makeFakeTable(true, false);

        var remoteCalls = [];
        unloaded.callRemote = function () {
            var d = Divmod.Defer.Deferred();
            remoteCalls.push(d);
            return d;
        };
        unloaded.loaded();
        var n = unloaded.node;
        // This should be the progress node.
        var lastNode = n.childNodes[n.childNodes.length - 1];
        self.assertIdentical(lastNode.className, "scrolltable-loading");
        for (var i = 0; i < remoteCalls.length; i++) {
            var eachCall = remoteCalls[i];
            eachCall.callback([]);
        }
        // Should have fired / been loaded by now, and the node should have
        // been removed.
        self.assertIdentical(lastNode.parentNode, null);
    },

    /**
     * L{Mantissa.ScrollTable.ScrollTable.loaded} should return a deferred,
     * which is called back upon completion of the remote calls initiated by
     * the model's initialization.
     */
    function test_loadedDeferred(self) {
        var unloaded = self.makeFakeTable(true, false);
        var deferred = Divmod.Defer.Deferred();
        unloaded.callRemote = function() {
            return deferred;
        }
        var resultDeferred = unloaded.loaded();
        if(!(resultDeferred instanceof Divmod.Defer.Deferred)) {
            self.fail('expected deferred from loaded');
        }
        var calledBack = false;
        resultDeferred.addCallback(
            function() {
                calledBack = true;
            });
        deferred.callback([]);
        self.assertIdentical(calledBack, true);
    },

    /**
     * Create a fake ScrollTable instance.
     */
    function makeFakeTable(self, /* optional */ sortAscending, doLoad) {
        var tableNode = document.createElement("div");
        tableNode.id = 'athena:1';
        var table = Mantissa.ScrollTable.ScrollTable(
            tableNode, 'value', [
                {type: 'integer', name: 'value'},
                {type: 'text', name: 'text'},
                {type: 'timestamp', name: 'date'},
                {type: 'boolean', name: 'bit'}],
            sortAscending);
        table.callRemote = function () {
            // Answer every call to the server with empty rows, so that we can
            // pretend to completely initialize.
            return Divmod.Defer.succeed([]);
        };
        table.callQueue = [];
        table.callLater = function (seconds, thunk) {
            table.callQueue.push(thunk);
            return {cancel: function () {}};
        };
        table.flushCallLaters = function () {
            for (var i = 0; i < table.callQueue.length; i++) {
                table.callQueue[i]();
            }
            table.callQueue = [];
        };

        if (doLoad === undefined) {
            doLoad = true;
        }

        if (doLoad) {
            // Set up the rest of the legacy attriubtes we need for DOM
            // manipulation.
            table.loaded();
        }
        return table;
    },

    /**
     * Verify that the given page size will be detected from the given row and
     * viewport heights.
     */
    function _verifyPageSize(self, pageSize, rowHeight, viewportHeight) {
        // XXX only works with the mock DOM implementation.  There's no other
        // way to run these tests right now, but what if, one day...?
        self.table.node.setMockElementSize(1234, viewportHeight);
        self.table._getRowHeight = function () {
            return rowHeight;
        }
        self.table.loaded();    // It was calculated (wrong) when the test
                                // started, but loaded() has to do this
                                // calculation so that the first request will
                                // be the right size.
        self.assertIdentical(self.table.model._pagesize, pageSize);

    },

    /**
     * Verify that the sort order passed to the table's constructor also
     * reflects the model's sort order.
     */
    function test_sortAffectsModel(self) {
        var ascendingTable = self.makeFakeTable(true);
        var descendingTable = self.makeFakeTable(false);
        self.assertIdentical(ascendingTable.model._sortAscending, true);
        self.assertIdentical(descendingTable.model._sortAscending, false);
    },

    /**
     * Verify that the user will retrieve at least as many rows from the
     * server as will cover one visible page.
     */
    function test_detectPageSize(self) {
        self._verifyPageSize(26, 5, 126);
    },

    /**
     * Verify that the minimum detected page-size will be 2, even if you can
     * only see one row at a time.
     */
    function test_minimumPageSize(self) {
        self._verifyPageSize(2, 100, 10);
    },

    /**
     * Verify that scrolltables whose nodes have not yet been realized
     * (e.g. given a height and width by the browser) will nevertheless stick
     * to a minimum pagesize of '2'.
     */
    function test_unrealizedPageSize(self) {
        self._verifyPageSize(2, 0, 0);
    },

    /**
     * Verify that new (position-based) scrolling widgets create block (div)
     * nodes by default for their row nodes.
     */
    function test_newMakeRowElement(self) {
        var re = self.table.makeRowElement(0, [], []);
        self.assertIdentical(re.tagName, "DIV");
        self.assertIdentical(re.getAttribute("class"), "scroll-row");
    },

    /**
     * Verify that new (position-based) scrolling widgets create table cells
     * by default for their cell nodes.
     */
    function test_newMakeCellElement(self) {
        var ce = self.table.makeCellElement('value', {value: 'hello'});
        self.assertIdentical(ce.tagName, "SPAN");
    },

    /**
     * DOMRegionViews should not visually overlap with each other when the
     * actual row heights based on filling out the DOM are greater than the
     * expected row heights from estimating with _getRowHeight.  In other
     * words, they should be inserted at a pixel offset based on the distance
     * from the preceding region, not an absolute offset.
     */
    function test_overlappingRegionView(self) {
        self.table._getRowHeight = function () {
            return 22;
        };
        self.table.model.insertRowData(0, [self._makeFake(1),
                                           self._makeFake(2)]);
        self.table.model._regions[0].viewPeer.node.setMockElementSize(
            100, 5000);
        self.table.model.insertRowData(3, [self._makeFake(6),
                                           self._makeFake(7)]);
        // sanity check
        self.assertIdentical(self.table.node.childNodes.length, 2);
        var theNode = self.table.model._regions[1].viewPeer.node;

        self.assertIdentical(theNode.style.top, '5022px');
    },

    /**
     * When the user scrolls to a particular pixel offset, the view should
     * translate that pixel offset into a row offset based on the end of the
     * previous row.
     */
    function test_requestAppropriateOffset(self) {
        self.table._getRowHeight = function () {
            return 33;
        };
        self.table.model.insertRowData(0, [self._makeFake(1),
                                           self._makeFake(2)]);
        // Now, rather than 66 pixels down, let's make that inordinately big.
        self.table.model._regions[0].viewPeer.node.setMockElementSize(
            100, 5000);

        self.assertIdentical(
            self.table.translateScrollOffset(5050),
            3);

        self.assertIdentical(
            self.table.translateScrollOffset(5000 + (33 * 10)),
            12);

        self.assertIdentical(
            self.table.translateScrollOffset(4999),
            2);

        self.assertIdentical(
            self.table.translateScrollOffset(0),
            0);
    },

    /**
     * translateScrollOffset should always return the first scroll offset
     * within the region unless we can see past the end of the region.
     */
    function test_shortCircuitExposeWithinRegion(self) {
        self.table._getRowHeight = function () {
            return 33;
        };
        // We can see 3 rows at a time, normally.
        self.table.visiblePixelHeight = function () {
            return 99;
        };
        self.table.model.insertRowData(0, [self._makeFake(1),
                                           self._makeFake(2)]);
        // Now, rather than 66 pixels down, let's make that inordinately big.
        self.table.model._regions[0].viewPeer.node.setMockElementSize(
            100, 5000);

        // 4902 pixels in, our virtual viewport (99 pixels high) should be
        // able to see two rows of whitespace, which means we can see offset
        // 2.
        self.assertIdentical(self.table.translateScrollOffset(4902), 2);
        // 4900 pixels in, our virtual viewport is still entirely covered by
        // the 5000-pixel-high first region, so we should translate that to
        // the first offset in the visible region.
        self.assertIdentical(self.table.translateScrollOffset(4900), 0);
        // The beginning of the viewport should still be at the actual
        // beginning of the viewport; no change there.
        self.assertIdentical(self.table.translateScrollOffset(0), 0);
        // Some other values at various points between the beginning and the
        // end of the region should give the same results, just to make sure.
        self.assertIdentical(self.table.translateScrollOffset(20), 0);
        self.assertIdentical(self.table.translateScrollOffset(200), 0);
        self.assertIdentical(self.table.translateScrollOffset(1000), 0);

    },

    /**
     * Verify that L{Mantissa.ScrollTable.Column.valueToDOM} returns a
     * text node which contains only the value of the column.
     */
    function test_defaultColumnDOM(self) {
        var column = Mantissa.ScrollTable.Column('column');
        var textNode = column.valueToDOM(167);
        self.assertIdentical(textNode.nodeValue, '167');
    },

    /**
     * Verify that L{Mantissa.ScrollTable.TimestampColumn.valueToDOM} returns
     * a text node which contains only the value of the column, properly
     * formatted.
     */
    function test_timestampColumnDOM(self) {
        var column = Mantissa.ScrollTable.TimestampColumn('timestamp');
        var aDate = new Date(8274);
        var textNode = column.valueToDOM(aDate);
        self.assertIdentical(textNode.nodeValue, aDate.toUTCString());
    },

    /**
     * Verify that L{Mantissa.ScrollTable.TimestampColumn.extractValue}
     * correctly constructs a C{Date} object from the rowdata.
     */
    function test_timestampColumnExtractValue(self) {
        var column = Mantissa.ScrollTable.TimestampColumn('timestamp');
        // can't compare the Date objects directly.
        self.assertIdentical(
            column.extractValue({'timestamp': 12}).getTime(),
            new Date(12 * 1000).getTime());
    },

    /**
     * Verify that L{Mantissa.ScrollTable.TimestampColumn.toNumber} correctly
     * converts a C{Date} object into a C{Number}.
     */
    function test_timestampColumnToNumber(self) {
        var column = Mantissa.ScrollTable.TimestampColumn('timestamp');
        var theDate = new Date(101);
        self.assertIdentical(column.toNumber(theDate), theDate.getTime());
    },

    /**
     * Verify that L{Mantissa.ScrollTable.TimestampColumn.fromNumber}
     * correctly convers a C{Number} into a C{Date}.
     */
    function test_timestampColumnFromNumber(self) {
        var column = Mantissa.ScrollTable.TimestampColumn('timestamp');
        // this should really be a Date but oh well.
        self.assertIdentical(column.fromNumber(103), 103 / 1000);
    },

    /**
     * Verify that L{Mantissa.ScrollTable.WidgetColumn.valueToDOM} returns the
     * result of passing the supplied widget info to the parent widget's
     * C{addChildWidgetFromWidgetInfo} method.
     */
    function test_widgetColumnDOM(self) {
        var column = Mantissa.ScrollTable.WidgetColumn('widget');
        var theWidgetInfo = {'stuff': 'hi'};
        var deferred = Divmod.Defer.Deferred();
        var parentWidget = {addChildWidgetFromWidgetInfo: function(wigetInfo) {
            return deferred;
        }};
        resultNode = column.valueToDOM(theWidgetInfo, parentWidget);
        self.assertIdentical(resultNode.childNodes.length, 0);
        deferred.callback({node: document.createTextNode('hi')});
        self.assertIdentical(resultNode.childNodes.length, 1);
        self.assertIdentical(resultNode.childNodes[0].nodeValue, 'hi');
    },

    /**
     * L{WidgetColumn} should not attempt to add a widget from the fake value
     * returned by L{WidgetColumn.fakeValue}; it should return an empty node,
     * because there is no general mechanism for determining the
     * representative height of a widget (whose class we may not even know).
     */
    function test_widgetColumnFakeValue(self) {
        var column = Mantissa.ScrollTable.WidgetColumn('widget');
        // Table widget has no properties here because we should not interact
        // with it in any way in this case.
        var trivialNode = column.valueToDOM(column.fakeValue(), {});
        self.assertIdentical(trivialNode.tagName, 'DIV');
        self.assertIdentical(trivialNode.childNodes.length, 0);
    },


    /**
     * Verify that view offsets are properly calculated based on row height.
     */
    function test_viewOffsetSetting(self) {
        self.table._getRowHeight = function () {
            return 33;
        };
        self.table.model.insertRowData(0, [self.table._makeFakeData()]);
        var regionNode = self.table.model._regions[0].viewPeer.node;
        self.assertIdentical(regionNode.style.top, '0px');
        self.table.model._regions[0].adjustOffset(15);
        self.assertIdentical(regionNode.style.top, '495px');
    },

    /**
     * Make a representative fake row with the given value.
     */
    function _makeFake(self, value) {
        var fakeData = self.table._makeFakeData();
        fakeData.value = value;
        fakeData.__id__ = value;
        return fakeData;
    },

    /**
     * Create an array of fake data between the two numbers.
     */
    function _makeFakes(self, begin, end) {
        var result = [];
        for (var i = begin; i < end; i++) {
            result.push(self._makeFake(i));
        }
        return result;
    },

    /**
     * DOM has NodeLists which are implemented using interpreter magic that
     * cannot be replicated with JavaScript itself.  Although my mock browser
     * implementation actually uses an Array (because it is impossible to
     * implement an object that accurately reflects the semantics of JS DOM's
     * NodeList) we can't rely on it having a "slice()" attribute.
     */
    function _copyNodeListToArray(self, nodeList) {
        var resultingArray = [];
        for (var i = 0; i < nodeList.length; i++) {
            resultingArray.push(nodeList[i]);
        }
        return resultingArray;
    },

    /**
     * Verify that you can remove view rows from a freshly created view.
     */
    function test_simpleRemoveViewRow(self) {
        self.table.model.insertRowData(0, self._makeFakes(10, 20));
        var domRegionView = self.table.model._regions[0].viewPeer;
        // Sanity check.
        var rowContainerNode = domRegionView.node.childNodes[0];
        self.assertIdentical(rowContainerNode.childNodes.length, 10);
        var expectNodes = self._copyNodeListToArray(rowContainerNode.childNodes);
        expectNodes.splice(9, 1);
        expectNodes.splice(5, 1);
        expectNodes.splice(0, 1);
        domRegionView.removeViewRow(9);
        domRegionView.removeViewRow(5);
        domRegionView.removeViewRow(0);
        self.assertIdentical(rowContainerNode.childNodes.length, 7);
        self.assertIdentical(expectNodes.length, 7); // sanity check
        for (var i = 0; i < expectNodes.length; i++) {
            self.assertIdentical(rowContainerNode.childNodes[i],
                expectNodes[i]);
        }
    },

    /**
     * Verify that you can remove rows from a DOMRegionView that has merged in
     * several other row sets.
     */
    function test_nestedRemoveViewRow(self) {
        self.table.model.insertRowData(0, self._makeFakes(10, 20));
        var domRegionView = self.table.model._regions[0].viewPeer;
        var rowContainerNode = domRegionView.node.childNodes[0];
        // Rummage around in the DOM to create a situation like what would
        // happen if we had merged some nodes.
        var popNode = function () {
            var it = rowContainerNode.childNodes[
                rowContainerNode.childNodes.length - 1];
            rowContainerNode.removeChild(it);
            return it;
        }
        var b = popNode();
        var a = popNode();
        var rcn = domRegionView._makeRowContainerNode();
        rcn.appendChild(a);
        rcn.appendChild(b);
        rowContainerNode.appendChild(rcn);

        // sanity check
        self.assertIdentical(rcn.childNodes.length, 2);
        // Now remove that row and make sure the last one works.
        domRegionView.removeViewRow(9);
        self.assertIdentical(rcn.childNodes.length, 1);
        self.assertIdentical(rcn.childNodes[0], a);
    },

    /**
     * Verify that merging two DOMRegionView nodes results in a DOM structure
     * where the rows from the second one are together.
     */
    function test_mergeSomeRows(self) {
        self.table.model.insertRowData(0, self._makeFakes(10, 20));
        self.table.model.insertRowData(0, self._makeFakes(15, 25));
        var domRegionView = self.table.model._regions[0].viewPeer;
        var topContainer = domRegionView.node.childNodes[0];
        self.assertIdentical(
            topContainer.childNodes.length,
            11);
        self.assertIdentical(
            topContainer.childNodes[
                topContainer.childNodes.length - 1].childNodes.length,
            5);
    },

    /**
     * Verify that a table using all types of columns can create a useful set
     * of fake data for calculating a row.
     */
    function test_makeFakeData(self) {
        fakeData = self.table._makeFakeData();
        self.assert(typeof fakeData.value === 'number');
        self.assert(typeof fakeData.text === 'string');
        self.assert(typeof fakeData.bit == 'boolean');
        self.assert(fakeData.date instanceof Date);
    },

    /**
     * Verify that the given node has no implicit or explicit style attributes
     * that will interfere with measuring its height in a browser-portable
     * fashion.
     */
    function assertZeroCruft(self, node) {
        self.assertIdentical(node.style.border, '0px');
        self.assertIdentical(node.style.margin, '0px');
        self.assertIdentical(node.style.padding, '0px');
    },

    /**
     * _getRowHeight should continue to return the same result, but should not
     * create unnecessary nodes.
     */
    function test_getRowHeightNodes(self) {
        var elementCount = 0;
        document.origCreateElement = document.createElement;
        document.createElement = function (name) {
            elementCount++;
            return document.origCreateElement(name);
        };
        // put it into the document so it will have a height, and caching will
        // take effect.
        document.body.appendChild(self.table.node);
        try {
            var height1 = self.table._getRowHeight();
            var finalElementCount = elementCount;
            var height2 = self.table._getRowHeight();
            self.assertIdentical(finalElementCount, elementCount);
            self.assertIdentical(height1, height2);
        } finally {
            delete document.createElement;
            delete document.origCreateElement;
            document.body.removeChild(self.table.node);
        }
    },

    /**
     * Verify that there will be no borders, padding, or margins on region or
     * row-container nodes to interfere with placement logic.
     */
    function test_nodesHaveNoCruft(self) {
        self.table.model.insertRowData(0, [self.table._makeFakeData()]);
        var regionNode = self.table.model._regions[0].viewPeer.node;
        self.assertZeroCruft(regionNode);
        self.assertIdentical(regionNode.style.position, 'absolute');
        self.assertZeroCruft(regionNode.childNodes[0]);
    });
