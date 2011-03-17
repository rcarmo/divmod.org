// -*- test-case-name: xmantissa.test.test_javascript -*-
// Copyright (c) 2007-2010 Divmod.
// See LICENSE for details.

// import Divmod.UnitTest
// import Mantissa.DOMReplace

Mantissa.Test.TestDOMReplace.DOMReplaceTestCase = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestDOMReplace.DOMReplaceTestCase');
/**
 * Tests for L{Mantissa.DOMReplace}.
 */
Mantissa.Test.TestDOMReplace.DOMReplaceTestCase.methods(
    /**
     * Assert that C{node} is a text node, and that its content is C{content}.
     *
     * @param node: a node.
     * @type node: node
     *
     * @param content: a string.
     * @type content: C{String}
     *
     * @rtype: C{undefined}
     */
    function assertIsTextNode(self, node, content) {
        self.assertIdentical(node.nodeType, node.TEXT_NODE);
        self.assertIdentical(node.nodeValue, content);
    },

    /**
     * Assert that C{node} looks like something returned from
     * L{_matchOutputFactory}, and that it's wrapping a match for C{content}.
     *
     * @param node: a node.
     * @type node: node
     *
     * @param content: a string.
     * @type content: C{String}
     *
     * @rtype: C{undefined}
     */
    function assertIsMatchNode(self, node, content) {
        self.assertIdentical(node.tagName, 'DIV');
        self.assertIdentical(node.className, 'match');
        self.assertIdentical(node.childNodes.length, 1);
        self.assertIsTextNode(node.childNodes[0], content);
    },

    /**
     * Take a piece of text and wrap it in an easily identifiable node.
     *
     * @param match: a string.
     * @type match: C{String}
     *
     * @return: a node.
     * @rtype: node.
     */
    function _matchOutputFactory(self, match) {
        var matchNode = document.createElement('div');
        matchNode.setAttribute('class', 'match');
        matchNode.appendChild(document.createTextNode(match));
        return matchNode;
    },

    /**
     * Helper which calls L{Mantissa.DOMReplace.replace} on C{topNode}, with a
     * pattern of I{^t.*}, using L{_matchOutputFactory} as the output factory.
     *
     * @param topNode: the node to pass to L{Mantissa.DOMReplace.replace}.
     * @type topNode: node
     *
     * @rtype: C{undefined}
     */
    function _replace(self, topNode) {
        Mantissa.DOMReplace.replace(
            topNode, /^t.*/,
            function(match) {
                return self._matchOutputFactory(match);
            });
    },

    /**
     * L{Mantissa.DOMReplace.replace} should actually replace stuff.
     */
    function test_replace(self) {
        var topNode = document.createElement('div');
        topNode.appendChild(document.createTextNode('tcag'));

        self._replace(topNode);

        self.assertIdentical(topNode.childNodes.length, 1);
        self.assertIsMatchNode(topNode.childNodes[0], 'tcag');
    },

    /**
     * L{Mantissa.DOMReplace.replace} should replace matching nodes that
     * aren't immediate children of the top node.
     */
    function test_deepReplace(self) {
        var topNode = document.createElement('div');
        var nestedNode = document.createElement('div');
        nestedNode.appendChild(document.createTextNode('tcag'));
        topNode.appendChild(nestedNode);

        self._replace(topNode);

        self.assertIdentical(topNode.childNodes.length, 1);
        self.assertIdentical(topNode.childNodes[0], nestedNode);
        self.assertIdentical(nestedNode.childNodes.length, 1);
        self.assertIsMatchNode(nestedNode.childNodes[0], 'tcag');
    },

    /**
     * L{Mantissa.DOMReplace.replace} shouldn't do anything with text nodes
     * that don't match.
     */
    function test_noReplace(self) {
        var topNode = document.createElement('div');
        topNode.appendChild(document.createTextNode('actg'));

        self._replace(topNode);

        self.assertIdentical(topNode.childNodes.length, 1);
        self.assertIsTextNode(topNode.childNodes[0], 'actg');
    },

    /**
     * L{Mantissa.DOMReplace.replace} shouldn't do anything with text nodes
     * that don't match, even when they appear alongside text nodes that do.
     */
    function test_noReplaceNextToMatch(self) {
        var topNode = document.createElement('div');
        topNode.appendChild(document.createTextNode('actg'));
        topNode.appendChild(document.createElement('div'));
        topNode.appendChild(document.createTextNode('tcga'));

        self._replace(topNode);

        self.assertIsTextNode(topNode.childNodes[0], 'actg');
        self.assertIdentical(topNode.childNodes[1].tagName, 'DIV');
        self.assertIdentical(topNode.childNodes[1].childNodes.length, 0);
        self.assertIsMatchNode(topNode.childNodes[2], 'tcga');
    },

    /**
     * L{Mantissa.DOMReplace.replace} should transform multiple matching
     * sibling text nodes.
     */
    function test_replaceMatchingSiblings(self) {
        var topNode = document.createElement('div');
        topNode.appendChild(document.createTextNode('tagc'));
        topNode.appendChild(document.createElement('div'));
        topNode.appendChild(document.createTextNode('tcga'));

        self._replace(topNode);

        self.assertIdentical(topNode.childNodes.length, 3);
        self.assertIsMatchNode(topNode.childNodes[0], 'tagc');
        self.assertIdentical(topNode.childNodes[1].tagName, 'DIV');
        self.assertIdentical(topNode.childNodes[1].childNodes.length, 0);
        self.assertIsMatchNode(topNode.childNodes[2], 'tcga');
    },

    /**
     * L{Mantissa.DOMReplace.urlsToLinks} should really turn urls into links.
     */
    function test_urlsToLinks(self) {
        var topNode = document.createElement('div');
        topNode.appendChild(document.createTextNode('http://x.yz/foo#bar'));

        Mantissa.DOMReplace.urlsToLinks(topNode);

        self.assertIdentical(topNode.childNodes.length, 1);
        var link = topNode.childNodes[0];
        self.assertIdentical(link.tagName, 'A');
        self.assertIdentical(link.href, 'http://x.yz/foo#bar');
        self.assertIdentical(link.target, '_blank');
        self.assertIdentical(link.childNodes[0].nodeValue, link.href);
    },

    /**
     * L{Mantissa.DOMReplace.urlsToLinks} doesn't destroy all of the content
     * around a url on a line.
     */
    function test_urlsToLinksPreservesFollowingText(self) {
        var text = (
            'Hello world, enjoy http://x.yz/foo#bar as a link I give to you');
        var topNode = document.createElement('div');
        topNode.appendChild(document.createTextNode(text));

        Mantissa.DOMReplace.urlsToLinks(topNode);

        /* Now there should be three nodes; the leading text, the anchor, and
         * the trailing text.
         */
        self.assertIdentical(topNode.childNodes.length, 3);

        var leading = topNode.childNodes[0];
        var anchor = topNode.childNodes[1];
        var trailing = topNode.childNodes[2];

        self.assertIdentical(leading.nodeType, document.TEXT_NODE);
        self.assertIdentical(leading.nodeValue, 'Hello world, enjoy ');

        self.assertIdentical(anchor.tagName, 'A');
        self.assertIdentical(anchor.href, 'http://x.yz/foo#bar');
        self.assertIdentical(anchor.target, '_blank');
        self.assertIdentical(anchor.childNodes[0].nodeValue, anchor.href);

        self.assertIdentical(trailing.nodeType, document.TEXT_NODE);
        self.assertIdentical(trailing.nodeValue, ' as a link I give to you');
    },

    /**
     * L{Mantissa.DOMReplace.urlsToLinks} shouldn't try to turn a a url into a
     * link if the url appears anywhere inside an "A" tag.
     */
    function test_urlsToLinksAlreadyLinks(self) {
        var topNode = document.createElement('a');
        topNode.href = 'http://x.yz/internet';
        topNode.appendChild(document.createTextNode(topNode.href));

        Mantissa.DOMReplace.urlsToLinks(topNode);

        self.assertIdentical(topNode.tagName, 'A');
        self.assertIdentical(topNode.href, 'http://x.yz/internet');
        self.assertIdentical(topNode.childNodes.length, 1);
        self.assertIdentical(topNode.childNodes[0].nodeValue, 'http://x.yz/internet');
    });
