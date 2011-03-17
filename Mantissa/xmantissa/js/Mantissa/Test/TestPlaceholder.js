// Copyright (c) 2006 Divmod.
// See LICENSE for details.

/**
 * Tests for L{Mantissa.ScrollTable.PlaceholderModel}
 */

// import Divmod.UnitTest
// import Mantissa.ScrollTable

Mantissa.Test.TestPlaceholder.PlaceholderTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPlaceholder.PlaceholderTests');
Mantissa.Test.TestPlaceholder.PlaceholderTests.methods(
    /**
     * Set up a placeholder model with an initial placeholder which extends as far
     * as C{totalRows}.
     *
     * @type totalRows: integer
     * @rtype: L{Mantissa.ScrollTable.PlaceholderModel}
     */
    function setUp(self) {
        var totalRows = 5;
        self.model = Mantissa.ScrollTable.PlaceholderModel();
        self.model.registerInitialPlaceholder(totalRows, null);
    },


    /**
     * Set up a placeholder model with as many placeholders are there are entries
     * in C{ranges}, each start and stop indices equal to the first and second
     * entries in the corresponding pair.
     *
     * @param ranges: pairs of [start index, stop index]
     * @type ranges: sorted C{Array} of C{Array}
     *
     * @rtype: L{Mantissa.ScrollTable.PlaceholderModel}
     */
    function createPlaceholderLayout(self, ranges) {
        var model = Mantissa.ScrollTable.PlaceholderModel();
        for (var i = 0; i < ranges.length; i++) {
            model._placeholderRanges.push(
                model.createPlaceholder(ranges[i][0], ranges[i][1], null));
        }
        return model;
    },

    /**
     * Test L{Mantissa.ScrollTable.PlaceholderModel.createPlaceholder}
     */
    function test_createPlaceholder(self) {
        var p = self.model.createPlaceholder(0, 1, null);

        self.assertIdentical(p.start, 0, "expected a start of 0");
        self.assertIdentical(p.stop, 1, "expected a stop of 1");
        self.assertIdentical(p.node, null, "expected a null node");

        p = self.model.createPlaceholder(5, 11, 6);

        self.assertIdentical(p.start, 5, "expected a start of 5");
        self.assertIdentical(p.stop, 11, "expected a stop of 11");
        self.assertIdentical(p.node, 6, "expected a node of 6");
    },

    /**
     * Test
     * L{Mantissa.ScrollTable.PlaceholderModel.registerInitialPlaceholder}
     */
    function test_registerInitialPlaceholder(self) {
        self.assertIdentical(
            self.model.getPlaceholderCount(), 1,
            "expected one placeholder");

        var p = self.model.getPlaceholderWithIndex(0);

        self.assertIdentical(p.start, 0, "expected a start of 0");
        self.assertIdentical(p.stop, 5, "expected a stop of 5");
        self.assertIdentical(p.node, null, "expected a null node");
    },

    /**
     * Test L{Mantissa.ScrollTable.PlaceholderModel.replacePlaceholder}
     */
    function test_replacePlaceholder(self) {
        self.model.replacePlaceholder(
            0, self.model.createPlaceholder(0, 1, null));

        self.assertIdentical(
            self.model.getPlaceholderCount(), 1,
            "expected one placeholder");

        var p = self.model.getPlaceholderWithIndex(0);

        self.assertIdentical(p.start, 0, "expected a start of 0");
        self.assertIdentical(p.stop, 1, "expected a stop of 1");
        self.assertIdentical(p.node, null, "expected a null node");
    },

    /**
     * Test L{Mantissa.ScrollTable.PlaceholderModel.dividePlaceholder}
     */
    function test_dividePlaceholder(self) {
        var above = self.model.createPlaceholder(0, 1, null);
        var below = self.model.createPlaceholder(1, 2, null);

        self.model.dividePlaceholder(0, above, below);

        self.assertIdentical(
            self.model.getPlaceholderCount(), 2,
            "expected two placeholders");

        var p1 = self.model.getPlaceholderWithIndex(0);

        self.assertIdentical(p1.start, above.start, "start doesn't match");
        self.assertIdentical(p1.stop, above.stop, "stop doesn't match");
        self.assertIdentical(p1.node, above.node, "node doesn't match");

        var p2 = self.model.getPlaceholderWithIndex(1);

        self.assertIdentical(p2.start, below.start, "start doesn't match");
        self.assertIdentical(p2.stop, below.stop, "stop doesn't match");
        self.assertIdentical(p2.node, below.node, "node doesn't match");
    },

    /**
     * Test
     * L{Mantissa.ScrollTable.PlaceholderModel.findPlaceholderIndexForRowIndex}
     * when there is only one placeholder in the model
     */
    function test_findPlaceholderIndexForRowIndexOnePlaceholder(self) {
        var i, index, indices = [0, 1, 2, 3, 4];

        for(i = 0; i < indices.length; i++) {
            index = self.model.findPlaceholderIndexForRowIndex(indices[i]);
            self.assertIdentical(index, 0, "expected index=zero");
        }
        self.assertIdentical(
            self.model.findPlaceholderIndexForRowIndex(5), null,
            "expected null");
    },

    /**
     * Test
     * L{Mantissa.ScrollTable.PlaceholderModel.findPlaceholderIndexForRowIndex}
     * where there are multiple placeholders in the model
     */
    function test_findPlaceholderIndexForRowIndexMultiplePlaceholders(self) {
        var one = self.model.createPlaceholder(0, 3, null);
        var two = self.model.createPlaceholder(3, 5, null);
        var three = self.model.createPlaceholder(5, 10, null);

        self.model.dividePlaceholder(0, one, two);
        self.model.dividePlaceholder(1, two, three);

        /* check that the return result of findPlaceholderIndexForRowIndex is
         * C{output} across C{inputs} */
        var checkOutputMany = function(inputs, output) {
            for(i = 0; i < inputs.length; i++) {
                res = self.model.findPlaceholderIndexForRowIndex(inputs[i]);
                self.assert(res == output, ("expected " + output + " for "
                                            + inputs[i] + " not " + res));
            }
        }

        checkOutputMany([0, 1, 2], 0);
        checkOutputMany([3, 4], 1);
        checkOutputMany([5, 6, 7, 8, 9], 2);
        checkOutputMany([10, 11], null);
    },

    /**
     * Test
     * L{Mantissa.ScrollTable.PlaceholderModel.findPlaceholderIndexForRowIndex}
     * for the case where we're looking for a placeholder that doesn't exist,
     * but is between two valid placeholders
     */
    function test_findPlaceholderIndexForRowIndexMultiplePlaceholdersNeg(self) {
        var above = self.model.createPlaceholder(0, 1, null);
        var below = self.model.createPlaceholder(2, 3, null);

        self.model.dividePlaceholder(0, above, below);

        self.assert(
            self.model.findPlaceholderIndexForRowIndex(1) == null,
            "expected to find null");
    },

    /**
     * Test
     * L{Mantissa.ScrollTable.PlaceholderModel.findFirstPlaceholderIndexAfterRowIndex}
     * for the case where the row index is > placeholders[-1].stop-1
     */
    function test_findFirstPlaceholderIndexAfterRowIndexOnePlaceholderNeg(self) {
        self.assertIdentical(
            self.model.findFirstPlaceholderIndexAfterRowIndex(50), null);
    },

    /**
     * Test
     * L{Mantissa.ScrollTable.PlaceholderModel.findFirstPlaceholderIndexAfterRowIndex}
     * for the case where the row index is == placeholders[0].start
     */
    function test_findFirstPlaceholderIndexAfterRowIndexOnePlaceholderNeg2(self) {
        self.assertIdentical(
            self.model.findFirstPlaceholderIndexAfterRowIndex(0), null);
    },

    /**
     * Test
     * L{Mantissa.ScrollTable.PlaceholderModel.findFirstPlaceholderIndexAfterRowIndex}
     * for the case where the correct result for the index we pass is the only
     * gap in the placeholder list, and there are multiple placeholders
     */
    function test_findFirstPlaceholderIndexAfterRowIndexMultiplePlaceholders(self) {
        var model = self.createPlaceholderLayout([[0, 1],
                                                  [2, 3]]);

        self.assertIdentical(
            model.findFirstPlaceholderIndexAfterRowIndex(1), 1);
    },

    /**
     * Test
     * L{Mantissa.ScrollTable.PlaceholderModel.findFirstPlaceholderIndexAfterRowIndex}
     * for the case where there are multiple gaps in the placeholder list, and
     * the correct result for the index we pass is the first gap
     */
    function test_findFirstPlaceholderIndexAfterRowIndexMultiplePlaceholders2(self) {
        var model = self.createPlaceholderLayout([[0, 1],
                                                  [2, 4],
                                                  [5, 6],
                                                  [7, 10]]);

        self.assertIdentical(model.findFirstPlaceholderIndexAfterRowIndex(1), 1);
        self.assertIdentical(model.findFirstPlaceholderIndexAfterRowIndex(6), 3);
    },

    /**
     * Test
     * L{Mantissa.ScrollTable.PlaceholderModel.findFirstPlaceholderIndexAfterRowIndex}
     * for the case where there are multiple gaps in the placeholder list, and
     * the correct result for the index we pass is the last gap
     */
     function test_findFirstPlaceholderIndexAfterRowIndexMultiplePlaceholders3(self) {
        var model = self.createPlaceholderLayout([[0, 1],
                                                  [2, 4],
                                                  [5, 6],
                                                  [7, 10]]);

        self.assertIdentical(model.findFirstPlaceholderIndexAfterRowIndex(6), 3);
    },

    /**
     * Test
     * L{Mantissa.ScrollTable.PlaceholderModel.findFirstPlaceholderIndexAfterRowIndex}
     * for the case where there is a single gap in the placeholder list, which
     * appears at the beginning of the placeholder, and so doesn't have a
     * placeholder before it
     */
    function test_findFirstPlaceholderIndexAfterRowIndexMultiplePlaceholders4(self) {
        var model = self.createPlaceholderLayout([[1, 2]]);

        self.assertIdentical(model.findFirstPlaceholderIndexAfterRowIndex(0), 0);
    },

    /**
     * Test
     * L{Mantissa.ScrollTable.PlaceholderModel.findFirstPlaceholderIndexAfterRowIndex}
     * for the case where there are multiple gaps in the placeholder list, and
     * the correct result for the index we pass is the first gap, which
     * appears at the beginning of the placeholder list, and so doesn't have a
     * placeholder before it
     */
    function test_findFirstPlaceholderIndexAfterRowIndexMultiplePlaceholders5(self) {
        var model = self.createPlaceholderLayout([[1, 2],
                                                  [3, 5]]);

        self.assertIdentical(model.findFirstPlaceholderIndexAfterRowIndex(0), 0);
    },

    /**
     * Test that L{Mantissa.ScrollTable.PlaceholderModel.removedRow} shunts
     * down the start/stop indices of all placeholders after the removed row
     * index
     */
    function test_removedRow(self) {
        var model = self.createPlaceholderLayout([[0, 1],
                                                  [2, 3]]);

        model.removedRow(1);

        var first = model.getPlaceholderWithIndex(0);
        self.assertIdentical(first.start, 0);
        self.assertIdentical(first.stop, 1);

        var second = model.getPlaceholderWithIndex(1);
        self.assertIdentical(second.start, 1);
        self.assertIdentical(second.stop, 2);
    },

    /**
     * Test that L{Mantissa.ScrollTable.PlaceholderModel.removedRow} doesn't do
     * anything if there aren't any placeholders after the index of the removed
     * row.
     */
    function test_removedRowNeg(self) {
        var model = self.createPlaceholderLayout([[0, 1]]);

        model.removedRow(2);

        self.assertIdentical(model.getPlaceholderCount(), 1);
        self.assertIdentical(model.getPlaceholderWithIndex(0).start, 0);
        self.assertIdentical(model.getPlaceholderWithIndex(0).stop, 1);
    });
