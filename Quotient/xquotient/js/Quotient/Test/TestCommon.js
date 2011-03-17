// -*- test-case-name: xquotient.test.test_javascript -*-
// Copyright (c) 2008 Divmod.
// See LICENSE for details.

// import Divmod.UnitTest
// import Nevow.Test.WidgetUtil
// import Quotient.Common

Quotient.Test.TestCommon.AddPersonTestCase = Divmod.UnitTest.TestCase.subclass(
    'Quotient.Test.TestCommon.AddPersonTestCase');
/**
 * Tests for L{Quotient.Common.AddPerson}.
 */
Quotient.Test.TestCommon.AddPersonTestCase.methods(
    /**
     * Make a node with the class I{person-identifier}, containing the given
     * value.
     */
    function _makeIdentifierNode(self, identifier) {
        var container = document.createElement('div');
        var node = document.createElement('span');
        node.setAttribute('class', 'person-identifier');
        node.appendChild(document.createTextNode(identifier));
        container.appendChild(node);
        return node;
    },

    /**
     * L{Quotient.Common.AddPerson.replaceWithPersonHTML} should replace all
     * I{person-identifier} nodes with the given markup.
     */
    function test_replaceWithPersonHTML(self) {
        var identifier = 'foo@bar.baz';
        var nodes = [
            self._makeIdentifierNode(identifier),
            self._makeIdentifierNode('foo' + identifier),
            self._makeIdentifierNode(identifier)];
        var origNodesByAttr = Nevow.Athena.NodesByAttribute;
        var nodesByAttr = function nodesByAttr(root, attr, value) {
            if(root === document.documentElement
                && attr === 'class'
                && value === 'person-identifier') {
                return nodes;
            }
            return origNodesByAttr(root, attr, value);
        }
        var html = 'the html!';
        var widget = Quotient.Common.AddPerson(
            Nevow.Test.WidgetUtil.makeWidgetNode());
        try {
            Nevow.Athena.NodesByAttribute = nodesByAttr;
            widget.replaceWithPersonHTML(identifier, html);
        } finally {
            Nevow.Athena.NodesByAttribute = origNodesByAttr;
        }
        self.assertIdentical(nodes[0].parentNode.innerHTML, html);
        self.assertIdentical(nodes[1].parentNode.innerHTML, undefined);
        self.assertIdentical(nodes[2].parentNode.innerHTML, html);
    },

    /**
     * L{Quotient.Common.AddPerson.submitSuccess} should call
     * L{Quotient.Common.AddPerson.replaceWithPersonHTML} and call back the
     * submission deferred.
     */
    function test_submitSuccess(self) {
        var widget = Quotient.Common.AddPerson(
            Nevow.Test.WidgetUtil.makeWidgetNode());
        var submitDeferredFired = false;
        widget.submitDeferred.addCallback(
            function() {
                submitDeferredFired = true;
            });
        var email = 'foo.bar@baz-quux';
        widget.gatherInputs = function() {
            return {email: [email]};
        }
        var calls = [];
        widget.replaceWithPersonHTML = function(identifier, html) {
            calls.push([identifier, html]);
        }
        var html = 'the hypertext';
        widget.submitSuccess(html);
        self.assertIdentical(calls.length, 1);
        self.assertIdentical(calls[0][0], email);
        self.assertIdentical(calls[0][1], html);
        self.assertIdentical(submitDeferredFired, true);
    });
