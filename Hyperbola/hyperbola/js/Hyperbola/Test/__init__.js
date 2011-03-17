// import Nevow.Athena.Test

// import Hyperbola

Hyperbola.Test.BlurbTestCase = Nevow.Athena.Test.TestCase.subclass('Hyperbola.Test.BlurbTestCase');
/**
 * Tests for blurb rendering/behaviour
 */
Hyperbola.Test.BlurbTestCase.methods(
    function _getWidget(self, remoteMethod/*, ...*/) {
        var args = [];
        for (var i = 2; i < arguments.length; ++i) {
            args.push(arguments[i]);
        }
        var result = self.callRemote.apply(self, [remoteMethod].concat(args));
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                self.node.appendChild(widget.node);
                return widget;
            });
        return result;
    },

    /**
     * Ask for a blog post blurb, add it as a child widget and return it
     *
     * @param tags: tags to apply to the blog post
     * @type tags: C{Array} of C{String}
     *
     * @rtype: L{Divmod.Defer.Deferred} firing with
     * L{Hyperbola.BlogPostBlurbController}
     */
    function getBlogPost(self, tags) {
        return self._getWidget('getBlogPost', tags);
    },

    /**
     * Ask for a blog blurb, add it as a child widget and return it
     *
     * @param tags: tags to store
     * @type tags: C{Array} of C{String}
     *
     * @rtype: L{Divmod.Defer.Deferred} firing with
     * L{Hyperbola.BlogBlurbController}
     */
    function getBlog(self, tags) {
        return self._getWidget('getBlog', tags);
    },

    function _collectTags(self, parentNode) {
        var tagNodes = Nevow.Athena.NodesByAttribute(
            parentNode, 'class', 'tag'),
            tags = [];
        for(var i = 0 ; i < tagNodes.length; i++) {
            tags.push(tagNodes[i].firstChild.nodeValue);
        }
        return tags;
    },

    /**
     * Test that the tags of a blog post blurb appear in its markup
     */
    function test_blogPostTagsRendered(self) {
        var result = self.getBlogPost(['tag1', 'tag2']);
        result.addCallback(
            function(widget) {
                var parent = widget.firstNodeByAttribute(
                    'class', 'hyperbola-blog-post-links');
                self.assertArraysEqual(
                    self._collectTags(parent), ['tag1', 'tag2']);
            });
        return result;
    },

    /**
     * Test that all tags are rendered along with a blog
     */
    function test_allTagsRendereredForBlog(self) {
        var result = self.getBlog(['footag', 'bartag']);
        result.addCallback(
            function(widget) {
                var parent = widget.firstNodeByAttribute(
                    'class', 'hyperbola-section-column');
                self.assertArraysEqual(
                    self._collectTags(parent), ['footag', 'bartag']);
            });
        return result;
    });
