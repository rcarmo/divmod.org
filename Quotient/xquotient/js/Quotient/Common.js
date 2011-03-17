/* this javascript file should be included by all quotient pages */
// import Quotient
// import Mantissa.People
// import MochiKit.DOM

Quotient.Common.ButtonToggler = Divmod.Class.subclass('Quotient.Compose.ButtonToggler');
/**
 * Class which helps enable/disable Quotient UI buttons
 *
 * XXX The buttons themselves should really be widgets
 */
Quotient.Common.ButtonToggler.methods(
    /**
     * @param buttonNode: A button node, or any node which contains a node
     * with the class name "button-content" which in turn contains a link
     * @type buttonNode: node
     *
     * @param reducedOpacity: the opacity to set on the button node while it
     * is disabled (defaults to 0.4)
     * @type reducedOpacity: float between 0 (transparent) and 1 (opaque)
     */
    function __init__(self, buttonNode, reducedOpacity/*=0.4*/) {
        if(reducedOpacity == undefined) {
            reducedOpacity = 0.4;
        }
        self.buttonNode = buttonNode;
        self._reducedOpacity = reducedOpacity;
        self._onclickHandler = null;
        self._setUpNodes();
    },

    function _setUpNodes(self) {
        var buttonContent = Nevow.Athena.NodeByAttribute(
                                self.buttonNode, "class", "button-content");
        self.buttonLink = buttonContent.getElementsByTagName("a")[0];
    },

    /**
     * Disable the button.  Remove the onclick handler and increase
     * transparency of the button node
     */
    function disable(self) {
        var onclickHandler = self.buttonLink.onclick;
        if(onclickHandler == null) {
            throw new Error("button doesn't have an onclick handler");
        }
        self._onclickHandler = onclickHandler;
        self.buttonLink.onclick = function() {
            return false;
        }
        self.buttonNode.style.opacity = self._reducedOpacity;
    },

    /**
     * Enable the button.  Restore the onclick handler and make the button
     * node opaque
     */
    function enable(self) {
        if(!self._onclickHandler) {
            throw new Error("button isn't disabled");
        }
        self.buttonLink.onclick = self._onclickHandler;
        self._onclickHandler = null;
        self.buttonNode.style.opacity = 1;
    },

    /**
     * Disable the button until C{deferred} fires
     *
     * @type deferred: L{Divmod.Defer.Deferred}
     */
    function disableUntilFires(self, deferred) {
        self.disable();
        deferred.addBoth(
            function(passthrough) {
                self.enable();
                return passthrough;
            });
    });

Quotient.Common.Util = Nevow.Athena.Widget.subclass('Quotient.Common.Util');

/**
 * Show C{node} as a dialog - center it vertically and horizontally, grey
 * out the rest of the document, and hide it when the user clicks outside
 * of the dialog.
 *
 * @param parent: the node to display the dialog inside.  defaults to
 * document.body
 *
 * @return: pair of [dialog node, hide function]
 */
Quotient.Common.Util.showNodeAsDialog = function(node, parent/*=document.body*/) {
    /* clone the node so we can add it to the document in the different place */
    node = node.cloneNode(true);

    /* if the parent is supposed to be the <body>, then we use the <html> tag
     * for any kind of size calculation.  in standards-compliance mode,
     * firefox sets the height of <html> to be the height of the viewport -
     * and the height of <body> to be the height of its content, unless it is
     * told otherwise (and there are a different set of implications if it is)
     */
    if(parent == undefined) {
        parent = document.body;
    }

    var sizeParent;
    if(parent.tagName.toLowerCase() == 'body') {
        sizeParent = document.documentElement;
    } else {
        sizeParent = parent;
    }

    var pageSize = Divmod.Runtime.theRuntime.getElementSize(sizeParent);

    /* make an overlay element */
    var blurOverlay = MochiKit.DOM.DIV({"class": "blur-overlay"}, "&#160;");
    blurOverlay.style.height = sizeParent.scrollHeight + "px";

    /* add it to the document */
    parent.appendChild(blurOverlay);
    /* add our cloned node after it */
    parent.appendChild(node);

    node.style.position = "absolute";
    node.style.display = "";
    var elemSize = Divmod.Runtime.theRuntime.getElementSize(node);


    var left = Math.floor((pageSize.w / 2) - (elemSize.w / 2));
    node.style.left = (left + sizeParent.scrollLeft) + "px";

    var top = Math.floor((pageSize.h / 2) - (elemSize.h / 2));
    node.style.top = (top + sizeParent.scrollTop) + "px";


    var hidden = false;

    var hide = function() {
        if(hidden) {
            return;
        }
        hidden = true;
        parent.removeChild(blurOverlay);
        parent.removeChild(node);
        blurOverlay.onclick = null;
    }

    /* we use setTimeout(... 0) so the handler gets added after the current
     * onclick event (if any) is done
     */
    setTimeout(
        function() {
            blurOverlay.onclick = hide;
        }, 0);

    return {node: node, hide: hide};
}

/**
 * Show a simple warning dialog with the text C{text}
 *
 * @return: same as L{Quotient.Common.Util.showNodeAsDialog}
 */
Quotient.Common.Util.showSimpleWarningDialog = function(text) {
    var node = document.createElement("div");
    node.setAttribute("class", "simple-warning-dialog");
    node.setAttribute("style", "display: none");
    var title = document.createElement("div");
    title.setAttribute("class", "simple-warning-dialog-title");
    title.appendChild(document.createTextNode("Warning"));
    node.appendChild(title);
    var textWrapper = document.createElement("span");
    textWrapper.setAttribute("class", "simple-warning-dialog-text");
    textWrapper.appendChild(document.createTextNode(text));
    node.appendChild(textWrapper);
    document.body.appendChild(node);
    return Quotient.Common.Util.showNodeAsDialog(node);
}

/**
 * @return: array of values that appear in a1 and not a2
 * @param a1: array with no duplicate elements
 * @param a2: array
 *
 * difference([1,2,3], [1,4,6]) => [2,3]
 */
Quotient.Common.Util.difference = function(a1, a2) {
    var j, seen;
    var diff = [];
    for(var i = 0; i < a1.length; i++) {
        seen = false;
        for(j = 0; j < a2.length; j++) {
            if(a1[i] == a2[j]) {
                seen = true;
                break;
            }
        }
        if(!seen) {
            diff.push(a1[i]);
        }
    }
    return diff;
}

/**
 * Remove duplicate elements from the array C{array}, maintaining the element
 * ordering
 *
 * @type array: C{Array}
 * @rtype: C{Array}
 */
Quotient.Common.Util.uniq = function(array) {
    /* looks like we need a 'set' type */
    var uniq = [], seen = {};
    for(var i = 0; i < array.length; i++) {
        if(!(array[i] in seen)) {
            seen[array[i]] = 1;
            uniq.push(array[i]);
        }
    }
    return uniq;
}

Quotient.Common.Util.stripLeadingTrailingWS = function(str) {
    return str.replace(/^\s+/, "").replace(/\s+$/, "");
}

Quotient.Common.Util.startswith = function(needle, haystack) {
    return haystack.toLowerCase().slice(0, needle.length) == needle.toLowerCase();
}

Quotient.Common.Util.normalizeTag = function(tag) {
    return Quotient.Common.Util.stripLeadingTrailingWS(tag).replace(/\s{2,}/, " ").toLowerCase();
}

Quotient.Common.Util.resizeIFrame = function(frame) {
    // Code is from http://www.ozoneasylum.com/9671&latestPost=true
    try {
        var innerDoc = (frame.contentDocument) ? frame.contentDocument : frame.contentWindow.document;
        var objToResize = (frame.style) ? frame.style : frame;
        objToResize.height = innerDoc.body.scrollHeight + 20 + 'px';
    }
    catch (e) {}
}

/**
 * L{Mantissa.LiveForm.FormWidget} for adding people to an address book.
 */
Quotient.Common.AddPerson = Mantissa.LiveForm.FormWidget.subclass('Quotient.Common.AddPerson');
Quotient.Common.AddPerson.methods(
    function __init__(self, node, formName) {
        Quotient.Common.AddPerson.upcall(
            self, '__init__', node, formName);
        self.submitDeferred = Divmod.Defer.Deferred();
    },

    /**
     * Replace the Add Person UI with the newly created person widget.
     *
     * @type identifier: C{String}
     * @param identifier: Something identifying a person.
     *
     * @type personHTML: C{String}
     * @param personHTML: Some markup describing a person.
     */
    function replaceWithPersonHTML(self, identifier, personHTML) {
        var personIdentifiers = Nevow.Athena.NodesByAttribute(
            document.documentElement, 'class', 'person-identifier');
        var e;
        for(var i = 0; i < personIdentifiers.length; i++) {
            e = personIdentifiers[i];
            if(e.childNodes[0].nodeValue == identifier) {
                e.parentNode.innerHTML = personHTML;
            }
        }
    },

    /**
     * Override L{Mantissa.LiveForm.FormWidget} and replace the Add Person UI
     * with the newly created person widget.
     */
    function submitSuccess(self, result) {
        self.replaceWithPersonHTML(
            self.gatherInputs().email[0], result);
        self.submitDeferred.callback(null);
        self.submitDeferred = Divmod.Defer.Deferred();
    });


Quotient.Common.SenderPerson = Nevow.Athena.Widget.subclass("Quotient.Common.SenderPerson");
Quotient.Common.SenderPerson.methods(
    /**
     * Pre-fill the add person form with the information we know about this
     * sender
     */
    function _preFillForm(self) {
        var email = self.firstNodeByAttribute(
            'class', 'person-identifier').firstChild.nodeValue;
        self.addPersonFormWidget.setInputValues(
            {email: [email], nickname: [''] // shouldn't we actually default this
        });
    },

    /**
     * Show an "Add Person" dialog, with the form fields pre-filled with the
     * information we know about the sender (first name, last name, email
     * address)
     */
    function showAddPerson(self) {
        var addPersonDialogNode = Nevow.Athena.FirstNodeByAttribute(
            self.widgetParent.node, "class", "add-person-fragment");

        var dialog = Quotient.Common.Util.showNodeAsDialog(addPersonDialogNode);
        var form = dialog.node.getElementsByTagName("form")[0];
        self.addPersonFormWidget = Nevow.Athena.Widget.get(form);
        self.addPersonFormWidget.submitDeferred.addCallback(
            function() {
                dialog.hide();
            });
        self._preFillForm();
        return false;
    });

Quotient.Common.CollapsiblePane = {};

/**
 * Toggle the visibility of the collapsible pane whose expose arrow is
 * C{element}.  If C{prefix} is provided, it will be prepended to the
 * image filenames "outline-expanded.png" and "outline-collapsed.png"
 * which are used to source the expose arrow image for the expanded
 * and collapsed states.  C{parent} points to the closest element that
 * contains both the expose arrow and the contents of the pane
 */
Quotient.Common.CollapsiblePane.toggle = function(element,
                                                  prefix/*=''*/,
                                                  parent/*=element.parentNode*/) {

    var body = Nevow.Athena.FirstNodeByAttribute(
                    parent || element.parentNode,
                    'class',
                    'pane-body');
    var img = null;
    if(typeof(prefix) == 'undefined') {
        prefix = '';
    }

    if(body.style.position == "absolute") {
        body.style.position = "static";
        img = "/static/Quotient/images/" + prefix + "outline-expanded.png";
    } else {
        body.style.position = "absolute";
        img = "/static/Quotient/images/" + prefix + "outline-collapsed.png";
    }

    Nevow.Athena.NodeByAttribute(element, "class", "collapse-arrow").src = img;
}
