// import Nevow.Athena
// import Mantissa.LiveForm
// import Mantissa.AutoComplete
// import Mantissa.ScrollTable
// import Mantissa.DOMReplace



Hyperbola.ScrollTable = Mantissa.ScrollTable.ScrollTable.subclass('Hyperbola.ScrollTable');
/**
 * L{Mantissa.ScrollTable.ScrollTable} subclass for rendering lists of blurbs.
 */
Hyperbola.ScrollTable.methods(
    /**
     * Overide the default implementation to skip the timestamp column.
     */
    function skipColumn(self, name) {
        if(name == "dateCreated") {
            return true;
        }
        return false;
    },

    /**
     * Trying to actually determine a sensible pagesize is pointless here,
     * because post heights vary wildly.  This is as reasonable a guess as the
     * framework is likely to make, but doesn't fall into the trap of being
     * pathologically small if a really big post happens to get involved in
     * estimation.
     */
    function _detectPageSize(self) {
        self.model._pagesize = 10;
    },

    /**
     * Override the default implementation to avoid wrapping the cell in a
     * link tag.
     */
    function makeCellElement(self, colName, rowData) {
        var columnObject = self.columns[colName];
        var columnValue = columnObject.extractValue(rowData);
        return MochiKit.DOM.DIV(
            {"class": "scroll-cell",
                    // Blog posts _need_ to wrap, but scroll rows in
                    // scrolltables are told not to; let's make it explicit.
                    "style": "white-space: normal"},
            columnObject.valueToDOM(columnValue, self));
    });

Hyperbola._ReloadingFormWidget = Mantissa.LiveForm.FormWidget.subclass('Hyperbola._ReloadingFormWidget');
Hyperbola._ReloadingFormWidget.methods(
    function submitSuccess(self, result) {
        var D = Hyperbola._ReloadingFormWidget.upcall(
            self, 'submitSuccess', result);
        D.addCallback(
            function(ignored) {
                self._submittedSuccessfully();
            });
        return D;
    },

    function _submittedSuccessfully(self) {
        document.location.reload();
    });

Hyperbola.AddBlog = Hyperbola._ReloadingFormWidget.subclass('Hyperbola.AddBlog');
Hyperbola.AddComment = Hyperbola._ReloadingFormWidget.subclass('Hyperbola.AddComment');

Hyperbola.BlogPostBlurbController = Nevow.Athena.Widget.subclass('Hyperbola.BlogPostBlurbController');
/**
 * Controller class for blurbs of the BLOG_POST flavor.
 */
Hyperbola.BlogPostBlurbController.methods(
    function __init__(self, node) {
        Hyperbola.BlogPostBlurbController.upcall(self, '__init__', node);
        self._highlightURLs();
    },

    /**
     * Highlight any URLs that appear in the body of this blog post.
     */
    function _highlightURLs(self) {
        var bodyContainerNode = self.firstNodeByAttribute(
            'class', 'hyperbola-blurb-body');
        Mantissa.DOMReplace.urlsToLinks(bodyContainerNode);
    },

    function togglePostComments(self) {
        var node = self.firstNodeByAttribute(
            'class', 'hyperbola-blog-post-comments');
        if(node.style.display == '') {
            node.style.display = 'none';
        } else {
            node.style.display = '';
        }
        return false;
    },

    /**
     * Toggle the visibility of the 'edit post' form
     */
    function toggleEditForm(self) {
        var node = self.firstNodeByAttribute(
            'athena:class', 'Hyperbola.BlogPostBlurbEditorController');
        if(node.style.display == '') {
            node.style.display = 'none';
        } else {
            node.style.display = '';
        }
        return false;
    },

    /**
     * Show the delete confirmation DOM node
     */
    function showDeleteConfirmation(self, node) {
        self.firstNodeByAttribute(
            'class', 'confirm-delete').style.display = '';
        node.style.display = 'none';
        return false;
    },

    /**
     * Hide the delete confirmation DOM node
     */
    function hideDeleteConfirmation(self, node) {
        node.parentNode.style.display = 'none';
        self.firstNodeByAttribute(
            'class', 'delete-link').style.display = '';
    },

    /**
     * Tell the server to do delete this post, and reload the page
     */
    function deletePost(self) {
        var result = self.callRemote('delete');
        result.addCallback(
            function(ignored) {
                document.location.reload();
            });
        return false;
    });

Hyperbola.BlogBlurbController = Nevow.Athena.Widget.subclass('Hyperbola.BlogBlurbController');
Hyperbola.BlogBlurbController.methods(
    function chooseTag(self, node) {
        var tag = node.firstChild.nodeValue,
            form = self.firstNodeByAttribute(
                'name', 'tag-form');
        form.tag.value = tag;
        form.submit();
        return false;
    },

    function unchooseTag(self) {
        var form = self.firstNodeByAttribute('name', 'tag-form');
        form.tag.value = '';
        form.submit();
        return false;
    });

Hyperbola.AddBlogPost = Hyperbola._ReloadingFormWidget.subclass('Hyperbola.AddBlogPost');
Hyperbola.AddBlogPost.methods(
    function __init__(self, node, allTags) {
        Hyperbola.AddBlogPost.upcall(self, '__init__', node);
        self.autoComplete = Mantissa.AutoComplete.Controller(
            Mantissa.AutoComplete.Model(allTags),
            Mantissa.AutoComplete.View(
                self.firstNodeByAttribute('name', 'tags'),
                self.firstNodeByAttribute(
                    'class', 'hyperbola-tag-completions')));
    },

    function togglePostForm(self) {
        var node = self.firstNodeByAttribute(
            'class', 'hyperbola-add-post-form');
        if(node.style.display == '') {
            node.style.display = 'none';
        } else {
            node.style.display = '';
            document.documentElement.scrollTop = document.documentElement.scrollHeight;
        }
        return false;
    });

Hyperbola.AddBlogPostDialog = Hyperbola.AddBlogPost.subclass('Hyperbola.AddBlogPostDialog');
Hyperbola.AddBlogPostDialog.methods(
    function submit(self) {
        Hyperbola.AddBlogPostDialog.upcall(self, 'submit');
        window.close();
    });

Hyperbola.BlogPostBlurbEditorController = Hyperbola._ReloadingFormWidget.subclass('Hyperbola.BlogPostBlurbEditorController');
/**
 * Code for responding to events related to editing of blog post blurbs
 */
Hyperbola.BlogPostBlurbEditorController.methods(
    /**
     * Hide the 'edit blog post' form
     */
    function hideEditForm(self) {
        self.node.style.display = 'none';
        return false;
    });
