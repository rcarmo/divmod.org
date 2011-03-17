// Copyright (c) 2006 Divmod.
// See LICENSE for details.

// Tests for miscellaneous Quotient javascript utilities

// import Quotient.Common

runTests([
    /**
     * Test L{Quotient.Common.Util.uniq}
     */
    function test_uniq() {
        var l = [0, 1, 1, 2, 3, 5];
        assertArraysEqual(Quotient.Common.Util.uniq(l),
                          [0, 1, 2, 3, 5]);
    }]);

