
// import Divmod.Runtime

// import Mantissa.ScrollTable
// import Mantissa.LiveForm

Mantissa.Admin = {};

/**
 * Trivial L{Mantissa.ScrollTable.Action} subclass which sets a handler that
 * calls L{Mantissa.Admin.LocalUserBrowser.updateUserDetail} on the instance
 * that the action was activated in.
 */
Mantissa.Admin.EndowDepriveAction = Mantissa.ScrollTable.Action.subclass(
                                        'Mantissa.Admin.EndowDepriveAction');
Mantissa.Admin.EndowDepriveAction.methods(
    function __init__(self, name, displayName) {
        Mantissa.Admin.EndowDepriveAction.upcall(
            self, "__init__", name, displayName,
            function(localUserBrowser, row, result) {
                return localUserBrowser.updateUserDetail(result);
            });
    });


/**
 * Action for removing ports.  In addition to deleting them from the database
 * the server, delete them from the local view.
 *
 * XXX - In poor form, I have not written automated tests for this code.  The
 * only excuse I can muster is that the thought of adding to the twenty minutes
 * it takes to run nit for this meagre amount of code turns my stomach.  May my
 * ancestors forgive me for the shame I do to their name. -exarkun
 */
Mantissa.Admin.DeleteAction = Mantissa.ScrollTable.Action.subclass('Mantissa.Admin.DeleteAction');
Mantissa.Admin.DeleteAction.methods(
    function __init__(self, name, displayName) {
        Mantissa.Admin.DeleteAction.upcall(
            self, "__init__", name, displayName,
            function deleteSuccessful(scrollingWidget, row, result) {
                var index = scrollingWidget.model.findIndex(row.__id__);
                scrollingWidget.removeRow(index);
            });
    });


/**
 * Scrolling widget with a delete action.
 *
 * XXX See XXX for DeleteAction.
 */
Mantissa.Admin.PortBrowser = Mantissa.ScrollTable.FlexHeightScrollingWidget.subclass('Mantissa.Admin.PortBrowser');
Mantissa.Admin.PortBrowser.methods(
    function __init__(self, node, metadata) {
        self.actions = [Mantissa.Admin.DeleteAction("delete", "Delete")];
        Mantissa.Admin.PortBrowser.upcall(self, "__init__", node, metadata, 10);
    });


/**
 * Scrolltable with support for retrieving additional detailed information
 * about particular users from the server and displaying it on the page
 * someplace.
 */
Mantissa.Admin.LocalUserBrowser = Mantissa.ScrollTable.FlexHeightScrollingWidget.subclass('Mantissa.Admin.LocalUserBrowser');
Mantissa.Admin.LocalUserBrowser.methods(
    function __init__(self, node, metadata) {
        self.actions = [Mantissa.Admin.EndowDepriveAction("installOn", "Endow"),
                        Mantissa.Admin.EndowDepriveAction("uninstallFrom", " Deprive"),
                        Mantissa.Admin.EndowDepriveAction("suspend", " Suspend"),
                        Mantissa.Admin.EndowDepriveAction("unsuspend", " Unsuspend")
                        ];

        Mantissa.Admin.LocalUserBrowser.upcall(self, "__init__", node, metadata, 10);
    },

    function _getUserDetailElement(self) {
        if (self._userDetailElement == undefined) {
            var n = document.createElement('div');
            n.setAttribute('class', 'user-detail');
            self.node.appendChild(n);
            self._userDetailElement = n;
        }
        return self._userDetailElement;
    },

    /**
     * Called by L{Mantissa.Admin.EndowDepriveAction}.  Retrieves information
     * about the clicked user from the server and dumps it into a node
     * (created for this purpose, on demand).  Removes the existing content of
     * that node if there is any.
     */
    function updateUserDetail(self, result) {
        var D = self.addChildWidgetFromWidgetInfo(result);
        return D.addCallback(
            function(widget) {
                var n = self._getUserDetailElement();
                while(0 < n.childNodes.length) {
                    n.removeChild(n.firstChild);
                }
                n.appendChild(widget.node);
            });
    });
