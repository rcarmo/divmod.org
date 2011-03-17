// import Quotient
// import Nevow.Athena
// import Mantissa.LiveForm
// import Mantissa.TDB
// import Mantissa.ScrollTable

Quotient.Grabber.EditAction = Mantissa.ScrollTable.Action.subclass(
                                'Quotient.Grabber.EditAction');

Quotient.Grabber.EditAction.methods(
    function enact(self, scrollingWidget, row) {
        return scrollingWidget.widgetParent.loadEditForm(row.__id__);
    });

Quotient.Grabber.RefillingAction = Mantissa.ScrollTable.Action.subclass(
                                    'Quotient.Grabber.RefillingAction');

/**
 * Trivial L{Mantissa.ScrollTable.Action} subclass with a handler that refills
 * the scrolltable after the server-side action completes successfully.
 * XXX: we should really just mutate the row node in place, e.g. to change
 *      paused="true" to "false"
 */
Quotient.Grabber.RefillingAction.methods(
    function __init__(self, name, displayName, icon) {
        Quotient.Grabber.RefillingAction.upcall(
            self, "__init__", name, displayName,
            function(scrollingWidget, row, result) {
                return scrollingWidget.emptyAndRefill();
            },
            icon);
    });

Quotient.Grabber.ScrollingWidget = Mantissa.ScrollTable.FlexHeightScrollingWidget.subclass(
                                        'Quotient.Grabber.ScrollingWidget');

Quotient.Grabber.ScrollingWidget.methods(
    function __init__(self, node, metadata) {
        self.columnWidths = {"status": "50%"};

        self.actions = [Quotient.Grabber.RefillingAction(
                            "delete", "Delete",
                            "/Mantissa/images/delete.png"),

                        Quotient.Grabber.EditAction(
                            "edit", "Edit", null,
                            "/static/Quotient/images/action-edit.png"),

                        Quotient.Grabber.RefillingAction(
                            "pause", "Pause",
                            "/static/Quotient/images/action-pause.png"),

                        Quotient.Grabber.RefillingAction(
                            "resume", "Resume",
                            "/static/Quotient/images/action-resume.png")];

        Quotient.Grabber.ScrollingWidget.upcall(self, "__init__", node, metadata, 5);
        self._scrollViewport.style.height = '100px';
        self.node.style.display = "none";
        self.initializationDeferred.addCallback(
            function() {
                self.reevaluateVisibility();
            });
    },

    /**
     * Change the visibility of our node depending on our row count.
     *  If 0 < row count, then show, otherwise hide
     */
    function reevaluateVisibility(self) {
        if(0 < self.model.rowCount()) {
            self.node.style.display = "";
        } else {
            self.node.style.display = "none";
        }
    },

    /**
     * Override Mantissa.ScrollTable.ScrollingWidget.emptyAndRefill and add a
     * callback that fiddles our visibility depending on how many rows were
     * fetched
     */
    function emptyAndRefill(self) {
        var D = Quotient.Grabber.ScrollingWidget.upcall(self, "emptyAndRefill");
        return D.addCallback(
            function() {
                self.reevaluateVisibility();
            });
    },

    /**
     * This is unfortunate in the extreme.  The actions icons that we use
     * stretch the height of the row, which needs to exact.  Even if
     * we did "return self._createRow(0, {...})", the images wouldn't
     * have time to load in the microsecond that they are in the DOM,
     * so their heights wouldn't be factored in.  So we include an <img>
     * with a bum "src" attribute and set its height to be that of the
     * icons we'll be using.  Probably better than hacking our Action
     * subclasses to set the height on the <img> elements they make
     */
    function _getRowGuineaPig(self) {
        return MochiKit.DOM.TR(
                {"class": "scroll-row"},
                MochiKit.DOM.TD({"class": "scroll-cell"},
                    MochiKit.DOM.A({"style": "display: block"},
                        ["HI", MochiKit.DOM.IMG(
                                {"style": "height: 16px", "src": "#"})])));
    });

Quotient.Grabber.Controller = Nevow.Athena.Widget.subclass('Quotient.Grabber.Controller');
Quotient.Grabber.Controller.methods(
    function loadEditForm(self, targetID) {
        var D = self.callRemote("getEditGrabberForm", targetID);
        D.addCallback(
            function(html) {
                var node = null;
                try {
                    node = self.nodeByAttribute("class", "edit-grabber-form");
                } catch(e) {}

                if(!node) {
                    node = MochiKit.DOM.DIV({"class": "edit-grabber-form"});
                    var cont = self.nodeByAttribute("class", "edit-grabber-form-container");
                    cont.appendChild(node);
                }
                Divmod.Runtime.theRuntime.setNodeContent(node,
                    '<div xmlns="http://www.w3.org/1999/xhtml">' + html + '</div>');
            });
    },
    function hideEditForm(self) {
        var form = self.nodeByAttribute("class", "edit-grabber-form");
        while(form.childNodes) {
            form.removeChild(form.firstChild);
        }
    });

Quotient.Grabber.StatusWidget = Nevow.Athena.Widget.subclass('Grabber.StatusWidget');
Quotient.Grabber.StatusWidget.method(
    function __init__(self, node) {
        Quotient.Grabber.StatusWidget.upcall(self, '__init__', node);
        self._pendingStatusUpdate = null;
        var d = self.callRemote('startObserving');
        d.addCallback(function(newStatus) { self.setStatus(newStatus); });
        d.addErrback(function(err) { self.setStatus(err.message); });
    });

Quotient.Grabber.StatusWidget.method(
    function setStatus(self, newStatus) {
        self._pendingStatus = newStatus;
        if (self._pendingStatusUpdate == null) {
            self._pendingStatusUpdate = setTimeout(function() {
                var pendingStatus = self._pendingStatus;
                self._pendingStatus = self._pendingStatusUpdate = null;
                self.node.innerHTML = pendingStatus;
            }, 5);
        }
    });

Quotient.Grabber.AddGrabberFormWidget = Mantissa.LiveForm.FormWidget.subclass(
                                                    'Quotient.Grabber.AddGrabberFormWidget');

Quotient.Grabber.AddGrabberFormWidget.methods(
    function submitSuccess(self, result) {
        self.emptyErrorNode();
        var sf = Nevow.Athena.NodeByAttribute(self.widgetParent.node,
                                              'athena:class',
                                              'Quotient.Grabber.ScrollingWidget');

        Quotient.Grabber.ScrollingWidget.get(sf).emptyAndRefill();
        return Quotient.Grabber.AddGrabberFormWidget.upcall(self, "submitSuccess", result);
    },

    /**
     * Empty the node that contains error messages
     */
    function emptyErrorNode(self) {
        if(self.errorNode && 0 < self.errorNode.childNodes.length) {
            self.errorNode.removeChild(self.errorNode.firstChild);
        }
    },

    /**
     * Show an error message for Error C{err}
     */
    function submitFailure(self, err) {
        if(!self.errorNode) {
            self.errorNode = MochiKit.DOM.DIV({"class": "add-grabber-error"});
            self.node.appendChild(self.errorNode);
        }
        self.emptyErrorNode();
        self.errorNode.appendChild(
            document.createTextNode("Error submitting form: " + err.error.message));
    });
