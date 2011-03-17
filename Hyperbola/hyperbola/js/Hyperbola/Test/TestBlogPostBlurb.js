// -*- test-case-name: hyperbola.test.test_javascript -*-
// Copyright (c) 2007 Divmod.
// See LICENSE for details.

// import Divmod.UnitTest
// import Nevow.Test.WidgetUtil
// import Hyperbola

Hyperbola.Test.TestBlogPostBlurb.TestableBlogPostBlurbController = Hyperbola.BlogPostBlurbController.subclass(
    'Hyperbola.Test.TestBlogPostBlurb.TestableBlogPostBlurbController');
/**
 * Trivial L{Hyperbola.BlogPostBlurbController} subclass which overrides
 * C{firstNodeByAttribute}.
 *
 * @ivar _fnbaNode: the node to return from L{firstNodeByAttribute}.
 * @type _fnbaNode: node
 */
Hyperbola.Test.TestBlogPostBlurb.TestableBlogPostBlurbController.methods(
    function __init__(self, node, fnbaNode) {
        self._fnbaCalls = [];
        self._fnbaNode = fnbaNode;
        Hyperbola.Test.TestBlogPostBlurb.TestableBlogPostBlurbController.upcall(
            self, '__init__', node);
    },

    function firstNodeByAttribute(self, attrName, attrValue) {
        self._fnbaCalls.push([attrName, attrValue]);
        return self._fnbaNode;
    });

Hyperbola.Test.TestBlogPostBlurb.BlogPostBlurbTestCase = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestBlogPostBlurb.BlogPostBlurbTestCase');

/**
 *  Tests for L{Hyperbola.BlogPostBlurbController}.
 */
Hyperbola.Test.TestBlogPostBlurb.BlogPostBlurbTestCase.methods(
    /**
     * L{Hyperbola.BlogPostBlurbController} should, in its constructor,
     * transform all urls inside the blog post body into links.
     */
    function test_replaceAtInitialization(self) {
        var node = Nevow.Test.WidgetUtil.makeWidgetNode();
        var fnbaNode = document.createElement('div');
        fnbaNode.appendChild(document.createTextNode('http://u.rl'));
        var widget = Hyperbola.Test.TestBlogPostBlurb.TestableBlogPostBlurbController(
            node, fnbaNode);
        Nevow.Test.WidgetUtil.registerWidget(widget);
        var unmockRDM = Nevow.Test.WidgetUtil.mockTheRDM();

        try {
            self.assertIdentical(widget._fnbaCalls.length, 1);
            self.assertIdentical(widget._fnbaCalls[0][0], 'class');
            self.assertIdentical(widget._fnbaCalls[0][1], 'hyperbola-blurb-body');

            self.assertIdentical(fnbaNode.childNodes.length, 1);
            self.assertIdentical(fnbaNode.childNodes[0].tagName, 'A');
        } finally {
            unmockRDM();
        }
    });

