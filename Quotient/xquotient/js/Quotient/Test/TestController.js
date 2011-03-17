// -*- test-case-name: xquotient.test.test_javascript -*-

// import Divmod.UnitTest
// import Quotient.Mailbox

/**
 * Tests for L{Quotient.Mailbox.Controller}.
 */
Divmod.UnitTest.TestCase.subclass(Quotient.Test.TestController, 'MessagePreviewTests').methods(
    /**
     * The C{fillSlots} method of the pattern object returned by
     * L{Controller.onePattern} escapes all ampersands, less than signs, and
     * greater than signs in the value passed to it.
     */
    function test_nextMessagePattern(self) {
        var node = document.createElement('span');
        node.id = "athena:7";
        var controller = Quotient.Mailbox.Controller(node, 0);
        var pattern = controller.onePattern('next-message');
        var markup = pattern.fillSlots('foo', '&&<<>>');
        self.assertIdentical(
            markup,
            '<div xmlns="http://www.w3.org/1999/xhtml">Next: ' +
            '&amp;&amp;&lt;&lt;&gt;&gt;</div>');
    });
