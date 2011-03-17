// -*- test-case-name: hyperbola.test.test_javascript -*-

// import Divmod.UnitTest

// import Hyperbola


Hyperbola.ConsoleTest.TestScrollTable.ScrollTableTestCase = (
    Divmod.UnitTest.TestCase.subclass(
        'Hyperbola.ConsoleTest.TestScrollTable.ScrollTableTestCase'));
Hyperbola.ConsoleTest.TestScrollTable.ScrollTableTestCase.methods(
    /**
     * L{Hyperbola.ScrollTable.skipColumn} should skip the "dateCreated"
     * timestamp column.
     */
    function test_skipColumn(self) {
        var node = document.createElement('div');
        node.id = 'athena:1'
        var scrollTable = Hyperbola.ScrollTable(node, [], false);
        self.assertIdentical(scrollTable.skipColumn("dateCreated"), true);
        self.assertIdentical(scrollTable.skipColumn("blurbView"), false);
    });
