/**
 *
 * Mailbox specific view logic for displaying a scrolltable of messages.
 *
 */

// import Mantissa.People
// import Mantissa.ScrollTable
// import Mantissa.LiveForm
// import Mantissa.DOMReplace

// import Quotient
// import Quotient.Common
// import Quotient.Throbber
// import Quotient.Message

Quotient.Mailbox.Status = Divmod.Class.subclass("Quotient.Mailbox.Status");
/**
 * Object which controls the display of status messages to the user
 */
Quotient.Mailbox.Status.methods(
    /**
     * @param node: The node which contains the throbber and status nodes
     * @type node: node
     */
    function __init__(self, node) {
        self.throbber = Quotient.Throbber.Throbber(
                            Nevow.Athena.FirstNodeByAttribute(
                                node, "class", "throbber"));

        self.statusNode = Nevow.Athena.FirstNodeByAttribute(
                            node, "class", "mailbox-status");

        self._waitingOn = null;
    },

    /**
     * Set the user-visible status to the message C{message}
     *
     * @type message: C{String}
     */
    function _setStatus(self, message) {
        self.statusNode.appendChild(
            document.createTextNode(message));
    },

    /**
     * Clear the user-visible status
     */
    function _clearStatus(self) {
        while(self.statusNode.firstChild) {
            self.statusNode.removeChild(
                self.statusNode.firstChild);
        }
    },

    /**
     * @return: the status message currently being displayed
     * @rtype: C{String}
     */
    function getCurrentStatus(self) {
        if(1 == self.statusNode.childNodes.length) {
            return self.statusNode.firstChild.nodeValue;
        }
        return null;
    },

    /**
     * Show C{message} to the user until C{deferred} fires
     *
     * @type deferred: C{Divmod.Defer.Deferred}
     * @param message: user-facing text describing what is being waited on
     * @type message: C{String}
     */
    function showStatusUntilFires(self, deferred, message) {
        /* XXX to be useful in any kind of general way, there should be a way
         * to show the status of a short task (e.g. "Message deleted") while
         * the status of a long-running task is being displayed, and a way to
         * show the status of concurrent long-running tasks
         */
        if(self._waitingOn != null) {
            throw new Error("already waiting on a deferred");
        }
        self._waitingOn = deferred;

        self.throbber.startThrobbing();

        self._setStatus(message);

        deferred.addBoth(
            function(passthrough) {
                self._waitingOn = null;

                self._clearStatus();
                self.throbber.stopThrobbing();

                return passthrough;
            });
    });

/**
 * Enhanced scrolling widget which suports the notion of one or more selected
 * rows.
 *
 * In order to keep the view up to date with the model, this widget requires
 * its parent widget to implement four methods: updateMessageDetail,
 * clearMessageDetail, updateMessagePreview, and decrementActiveMailViewCount.
 *
 * @ivar viewSelection
 *
 */
Quotient.Mailbox.ScrollingWidget = Mantissa.ScrollTable.ScrollingWidget.subclass(
    "Quotient.Mailbox.ScrollingWidget");

Quotient.Mailbox.ScrollingWidget.methods(
    function __init__(self, node, metadata) {
        /*
         * XXX TODO - viewSelection should be a parameter to __init__
         */
        self.viewSelection = {
            "view": "inbox",
            "tag": null,
            "person": null,
            "account": null};
        self.columnAliases = {"receivedWhen": "Date", "senderDisplay": "Sender"};

        self._messageDetailUpdatedDeferred = Divmod.Defer.Deferred();

        Quotient.Mailbox.ScrollingWidget.upcall(self, "__init__", node, metadata);

        /*
         * Make sure we get row selection/unselection notification so we can
         * update the checkbox images.
         */
        self.model.addObserver(self);

        self._scrollViewport.style.maxHeight = "";
        self.ypos = Divmod.Runtime.theRuntime.findPosY(self._scrollViewport.parentNode);
        try {
            self.throbberNode = Nevow.Athena.FirstNodeByAttribute(self.node.parentNode, "class", "throbber");
        } catch (err) {
            self.throbberNode = document.createElement('span');
        }
        self.throbber = Quotient.Throbber.Throbber(self.throbberNode);
    },

    /**
     * Override the base implementation to pass along our current view
     * selection.
     */
    function getTableMetadata(self) {
        return self.callRemote("getTableMetadata", self.viewSelection);
    },

    /**
     * Override the base implementation to pass along our current view
     * selection.
     */
    function getRows(self, firstRow, lastRow) {
        return self.callRemote("requestRowRange", self.viewSelection, firstRow, lastRow);
    },

    /**
     * Override the base implementation to pass along our current view
     * selection.
     */
     function getSize(self) {
        return self.callRemote("requestCurrentSize", self.viewSelection);
    },

    /**
     * Override default row to add some divs with particular classes, since
     * they will most likely change the height of our rows.
     */
    function _getRowGuineaPig(self) {
        /* unset row height so the guinea pig row doesn't have its height
         * constrained in any way, as we are using it to try and figure out
         * what the height should be!  (see code in L{makeRowElement})
         */
        self._rowHeight = undefined;
        return self._createRow(
        /* all of these keys won't necessarily be used, as some only
         * contribute to the row content only if we're in some particular
         * view, e.g. 'recipient' will be used in the 'sent' view, and
         * 'sender' will be used otherwise, etc. */
                    0, {"sender": "FOO@BAR",
                        "senderDisplay": "FOO",
                        "recipient": "FOO@BAR",
                        "subject": "A NORMAL SUBJECT",
                        "receivedWhen": "1985-01-26",
                        "read": false,
                        "sentWhen": "1985-01-26",
                        "attachments": 6,
                        "everDeferred": true,
                        "__id__": 6});
    },

    /**
     * Change the view being viewed.  Return a Deferred which fires with the
     * number of messages in the new view.
     */
    function changeViewSelection(self, viewType, value) {
        self.throbber.startThrobbing();
        self.viewSelection[viewType] = value;
        self.resetColumns();
        var result = self.emptyAndRefill();
        result.addCallback(
            function(info) {
                var messageCount = info[0];
                return self.activateFirstRow().addCallback(
                    function(ignored) {
                        return messageCount;
                    });
            });
        result.addBoth(
            function(passthrough) {
                self.throbber.stopThrobbing();
                return passthrough;
            });
        return result;
    },

    /**
     * Override this to return an empty Array because the Inbox has no row
     * headers.
     */
    function _createRowHeaders(self, columnNames) {
        return [];
    },

    /**
     * Handle row activation in several ways:
     *
     * - mark the row as read
     * - decrement the active mail view count, if the row was "bold"
     * - Change the font weight and background color to make it visually
     *   apparent it is focused.
     */
    function rowActivated(self, row) {
        var node = row.__node__;
        row["read"] = true;

        if (node.style.fontWeight == "bold") {
            self.decrementActiveMailViewCount();
        }

        node.style.fontWeight = "";
        node.style.backgroundColor = '#FFFFFF';

        return self.updateMessageDetail(row.__id__);
    },

    /**
     * Handle row de-activation to re-set the background color to normal.
     */
    function rowDeactivated(self, row) {
        row.__node__.style.backgroundColor = '';
        self.clearMessageDetail();
        if (self.model.rowCount() == 0) {
            self.updateMessagePreview(null);
        }
    },

    function updateMessageDetail(self, webID) {
        var result = self.widgetParent.updateMessageDetail(webID);
        result.addCallback(
            function(result) {
                self._messageDetailUpdatedDeferred.callback(result);
            });
        result.addErrback(
            function(result) {
                self._messageDetailUpdatedDeferred.errback(result);
            });
        result.addBoth(
            function(passThrough) {
                self._messageDetailUpdatedDeferred = Divmod.Defer.Deferred();
                return passThrough;
            });
        return result;
    },

    function updateMessagePreview(self, previewData) {
        return self.widgetParent.updateMessagePreview(previewData);
    },

    function clearMessageDetail(self) {
        return self.widgetParent.clearMessageDetail();
    },

    function decrementActiveMailViewCount(self) {
        return self.widgetParent.decrementActiveMailViewCount();
    },


    /**
     * Return the 'cell element' of a scroll widget row. That is, find the
     * bit in the DOM that was made by L{makeCellElement} and return that.
     */
    function findCellElement(self, rowData) {
        var node = rowData.__node__;
        return node.firstChild.firstChild.firstChild;
    },


    /**
     * Return a DOM element which is an image of a boomerang.
     */
    function _makeBoomerang(self) {
        return MochiKit.DOM.IMG(
            {"src": "/static/Quotient/images/boomerang.gif",
             "border": "0",
             "height": "13px"});
    },


    /**
     * Set the given row as having been deferred at some point.
     *
     * @param index: The index of the row which has become deferred.
     */
    function setAsDeferred(self, data) {
        if (!data['everDeferred']) {
            data['everDeferred'] = true;
            var dom = self.findCellElement(data);
            dom.appendChild(self._makeBoomerang());
        }
    },

    /**
     * Return the row data for the currently selected row.  Return null if
     * there is no row selected.
     */
    function getActiveRow(self) {
        return self.model.activeRow();
    },

    /**
     * Activate the first row, if one exists.
     *
     * If there are no rows, no action will be taken.
     */
    function activateFirstRow(self) {
        if (self.model.rowCount()) {
            self.model.activateRow(self.model.getRowData(0)['__id__']);
            return self._messageDetailUpdatedDeferred;
        } 
        return Divmod.Defer.succeed(null);
    },


    /**
     * Override row creation to provide a different style.
     *
     * XXX - should be template changes.
     */
    function makeRowElement(self, rowOffset, rowData, cells) {
        var height;
        if(self._rowHeight != undefined) {
            /* box model includes padding mumble and we don't need to */
            height = "height: " + (self._rowHeight - 11) + "px";
        } else {
            height = "";
        }
        var style = "";
        if(!rowData["read"]) {
            style += ";font-weight: bold";
        }
        var data = [MochiKit.Base.filter(null, cells)];
        if(0 < rowData["attachments"]) {
            data.push(MochiKit.DOM.IMG({"src": "/static/Quotient/images/paperclip.png",
                                        "class": "paperclip-icon"}));
        }
        return MochiKit.DOM.TR(
            {"class": "q-scroll-row",
             "onclick": function(event) {
                    var webID = rowData["__id__"];
                    return Nevow.Athena.Widget.dispatchEvent(
                        self, "onclick", "<row clicked>",
                        function() {
                            /* don't select based on rowOffset because it'll
                             * change as rows are removed
                             */
                            self.model.activateRow(webID);
                            return false;
                        });
                },
             "style": style,
            }, MochiKit.DOM.TD(null,
                /* height doesn't work as expected on a <td> */
                MochiKit.DOM.DIV({"style": height}, data)));
    },

    /**
     * Extend base behavior to recognize the subject column and replace empty
     * subjects with a special string.
     *
     * XXX - Dynamic dispatch for column names or templates or something.
     */
    function massageColumnValue(self, name, type, value) {
        var res = Quotient.Mailbox.ScrollingWidget.upcall(
                        self, "massageColumnValue", name, type, value);

        var ALL_WHITESPACE = /^\s*$/;
        if(name == "subject" && ALL_WHITESPACE.test(res)) {
            res = "<no subject>";
        }
        return res;
    },

    /**
     * Override the base behavior to add a million and one special cases for
     * things like the "ever deferred" boomerang or to change the name of the
     * "receivedWhen" column to something totally unrelated like "sentWhen".
     *
     * XXX - Should just be template crap.
     */
    function makeCellElement(self, colName, rowData) {
        if(colName == "receivedWhen") {
            colName = "sentWhen";
        }
        var massage = function(colName) {
            return self.massageColumnValue(
                colName, self.columnTypes[colName][0], rowData[colName]);
            },
            attrs = {},
            content = [massage(colName)];

        if(colName == "senderDisplay") {
            attrs["class"] = "sender";

            if (rowData["everDeferred"]) {
                content.push(self._makeBoomerang());
            }
        } else if(colName == "subject") {
            attrs["class"] = "subject";
        } else if(colName == "sentWhen") {
            attrs["class"] = "date";
        } else if(colName == "recipient") {
            attrs["class"] = "recipient";
        } else {
            attrs["class"] = "unknown-inbox-column-"+colName;
            /* It _SHOULD_ be the following, but that makes certain test
             * fixtures break.
             */
            // throw new Error("invalid column name: " + colName);
        }
        if(colName == "senderDisplay" || colName == "recipient") {
            content.unshift(
                MochiKit.DOM.IMG({
                    "src": "/static/Quotient/images/checkbox-off.gif",
                    "class": "checkbox-image",
                    "height": "12px",
                    "border": 0,
                    "onclick": function senderDisplayClicked(event) {
                        self.groupSelectRow(rowData["__id__"]);

                        this.blur();

                        if (!event) {
                            event = window.event;
                        }
                        event.cancelBubble = true;
                        if(event.stopPropagation) {
                            event.stopPropagation();
                        }

                        return false;
                    }}));
        }

        return MochiKit.DOM.DIV(attrs, content);
    },

    /**
     * Toggle the membership of a row in the group selection set.
     */
    function groupSelectRow(self, webID) {
        if (self.model.isSelected(webID)) {
            self.model.unselectRow(webID);
        } else {
            self.model.selectRow(webID);
        }
    },

    /**
     * Listen for row selection events to add the checkbox image to the display
     * for selected rows.
     */
    function rowSelected(self, row) {
        var checkboxImage = self._getCheckbox(row.__node__);
        var segs = checkboxImage.src.split("/");
        segs[segs.length - 1] = "checkbox-on.gif";
        checkboxImage.src = segs.join("/");
    },

    /**
     * Listen for row unselection events to remove the checkbox image from the
     * display for unselected rows.
     */
    function rowUnselected(self, row) {
        var checkboxImage = self._getCheckbox(row.__node__);
        var segs = checkboxImage.src.split("/");
        segs[segs.length - 1] = "checkbox-off.gif";
        checkboxImage.src = segs.join("/");
    },

    /**
     * Return the checkbox image node for the given row.
     */
    function _getCheckbox(self, node) {
        return Divmod.Runtime.theRuntime.firstNodeByAttribute(
            node, 'class', 'checkbox-image');
    },

    /**
     * Add, or remove all *already requested* rows to the group selection
     * @param selectRows: if true, select matching rows, otherwise deselect
     * @param predicate: function that accepts a mapping of column names to
     *                   column values & returns a boolean indicating whether
     *                   the row should be included in the selection
     * @return: the number of matching rows
     */
    function massSelectOrNot(self,
                             selectRows/*=true*/,
                             predicate/*=null*/) {

        if(selectRows == undefined) {
            selectRows = true;
        }
        if(predicate == undefined) {
            predicate = function(r) {
                return true
            }
        }

        var selected, row, webID, count = 0;
        var indices = self.model.getRowIndices();
        for (var i = 0; i < indices.length; ++i) {
            row = self.model.getRowData(i);
            webID = row.__id__;
            selected = self.model.isSelected(webID);
            /* if we like this row */
            if(predicate(row)) {
                /* and it's selection status isn't the desired one */
                if(selected != selectRows) {
                    /* then change it */
                    self.groupSelectRow(webID);
                    count++;
                }
                /* if we don't like it, but it's in the target state */
            } else if(selected == selectRows) {
                /* then change it */
                self.groupSelectRow(webID);
            }
        }
        return count;
    },

    /**
     * Override the base implementation to optionally use the specified second
     * Date instance as a point of reference.
     *
     * XXX - Why isn't this just the base implementation?
     */
    function formatDate(self, when, /* optional */ now) {
        if (now == undefined) {
            now = new Date();
        }
        function to12Hour(HH, MM) {
            var meridian;
            if(HH == 0) {
                HH += 12;
                meridian = "AM";
            } else if(0 < HH && HH < 12) {
                meridian = "AM";
            } else if(HH == 12) {
                meridian = "PM";
            } else {
                HH -= 12;
                meridian = "PM";
            }
            return HH + ":" + pad(MM) + " " + meridian;
        }
        function pad(n) {
            return (n < 10) ? "0" + n : n;
        }
        function explode(d) {
            return [d.getFullYear(), d.getMonth(), d.getDate()];
        }
        function arraysEqual(a, b) {
            if (a.length != b.length) {
                return false;
            }
            for (var i = 0; i < a.length; ++i) {
                if (a[i] != b[i]) {
                    return false;
                }
            }
            return true;
        }
        var parts = explode(when);
        var todayParts = explode(now);
        if (arraysEqual(parts, todayParts)) {
            /* it's today! Format it like "12:15 PM"
             */
            return to12Hour(when.getHours(), when.getMinutes());
        }
        if (parts[0] == todayParts[0]) {
            /* it's this year - format it like "Jan 12"
             *
             * XXX - Localization or whatever.
             */
            var monthNames = [
                "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
            return monthNames[parts[1]] + " " + parts[2];
        }
        return [pad(when.getFullYear()),
                pad(when.getMonth() + 1),
                pad(when.getDate())].join("-");
    },

    /**
     * Override to hide any of the columns from which we're extracting row
     * metadata.
     */
    function skipColumn(self, name) {
        if (name == "read" || name == "sentWhen" ||
            name == "attachments" || name == "everDeferred" ||
            name == "sender") {
            return true;
        }

        if (self.viewSelection.view == "sent") {
            if (name == "senderDisplay") {
                return true;
            }
        }

        if (self.viewSelection.view != "sent") {
            if (name == "recipient") {
                return true;
            }
        }
        return false;
    },

    /**
     * Override to update counts and do something else.
     *
     * XXX - This should be a callback on .scrolled()
     * XXX - And counts should be managed in some completely different way
     */
    function cbRowsFetched(self, count) {
        self.widgetParent.rowsFetched(count);
    });


/**
 * Run interference for a ScrollTable.
 *
 * @ivar contentTableGrid: An Array of the major components of an inbox
 * view.  The first element is an array with three elements: the td element for
 * the view selection area, the td element for the scrolltable, and the td
 * element for the message detail area.  The second element is also an array
 * with three elements: the footer td elements which correspond to the three td
 * elements in the first array.
 *
 * @ivar _batchSelection
 *
 */
Quotient.Mailbox.Controller = Nevow.Athena.Widget.subclass('Quotient.Mailbox.Controller');
Quotient.Mailbox.Controller.methods(
    function __init__(self, node, complexityLevel) {
        Quotient.Mailbox.Controller.upcall(self, '__init__', node);

        self.complexityLevel = complexityLevel;
        self._batchSelection = null;
        self._longRunningActionDeferred = null;

        self.viewToActions = {
            "all": ["defer", "delete", "forward",
                    "reply", "trainSpam", "unarchive"],
            "inbox": ["archive", "defer", "delete",
                      "forward", "reply", "trainSpam"],
            "focus": ["archive", "defer", "delete",
                      "forward", "reply", "trainSpam"],
            "archive": ["unarchive", "delete", "forward",
                        "reply", "trainSpam"],
            "draft": ["delete", "editDraft"],
            "spam": ["delete", "trainHam"],
            "deferred": ["forward", "reply"],
            "bounce": ['delete', 'forward'],
            "outbox": [],
            "sent": ["delete", "forward", "reply"],
            "trash": ["forward" ,"reply", "undelete"]};

        /*
         * Fired when the initial load has finished.
         */
        self.initializationDeferred = Divmod.Defer.Deferred();

        /*
         * Used to delay initializationDeferred until the second _getSomeRows
         * has finished.  Hopefully we can delete this someday, along with the
         * second _getSomeRows call.
         */
        self._secondGetSomeRows = Divmod.Defer.Deferred();

        self.initializationDeferred.addCallback(
            function(ignored) {
                return self._secondGetSomeRows;
            });
    },

    /**
     * Do a bunch of initialization, like finding useful nodes and child
     * widgets and filling up the scrolltable.
     */
    function loaded(self) {
        self.lastPageSize = Divmod.Runtime.theRuntime.getPageSize();

        /*
         * Hide the footer for some reason I can't guess.
         */
        var footer = document.getElementById("mantissa-footer");
        if (footer) {
            footer.style.display = "none";
        }

        MochiKit.DOM.addToCallStack(window, "onload",
            function() {
                MochiKit.DOM.addToCallStack(window, "onresize",
                    function() {
                        var pageSize = Divmod.Runtime.theRuntime.getPageSize();
                        if(pageSize.w != self.lastPageSize.w || pageSize.h != self.lastPageSize.h) {
                            self.lastPageSize = pageSize;
                            self.resized(false);
                        }
                    }, false);
            }, false);

        var search = document.getElementById("search-button");
        if(search) {
            /* if there aren't any search providers available,
             * then there won't be a search button */
            var width = Divmod.Runtime.theRuntime.getElementSize(search.parentNode).w;
            var contentTableContainer = self.firstNodeByAttribute("class", "content-table-container");
            contentTableContainer.style.paddingRight = width + "px";
        }

        self._batchSelectionPredicates = {read:   function(r) { return  r["read"] },
                                          unread: function(r) { return !r["read"] }}

        var contentTableNodes = self._getContentTableGrid();
        self.contentTable = contentTableNodes.table;
        self.contentTableGrid = contentTableNodes.grid;

        self.setupMailViewNodes();

        self.messageDetail = self.firstWithClass(self.contentTableGrid[0][2], "message-detail");


        self.progressBar = self.firstWithClass(
            self.contentTableGrid[1][2], "progress-bar");

        self.messageActionsNode = self.firstNodeByAttribute(
            "class", "message-actions");

        self.ypos = Divmod.Runtime.theRuntime.findPosY(self.messageDetail);
        self.messageBlockYPos = Divmod.Runtime.theRuntime.findPosY(self.messageDetail.parentNode);

        self.viewPaneCell = self.firstWithClass(self.contentTableGrid[0][0], "view-pane-cell");
        self.viewShortcutSelect = self.firstWithClass(self.node, "view-shortcut-container");

        var scrollNode = self.firstNodeByAttribute("athena:class", "Quotient.Mailbox.ScrollingWidget");

        self.scrollWidget = Nevow.Athena.Widget.get(scrollNode);

        /*
         * When the scroll widget is fully initialized, select the first row in
         * it.
         */
        self.scrollWidget.initializationDeferred.addCallback(
            function(passthrough) {
                return self.scrollWidget.activateFirstRow().addCallback(
                    function(ignored) {
                        self.initializationDeferred.callback(null);
                        if (self.scrollWidget.model.rowCount() == 0) {
                            self.updateMessagePreview(null);
                        };
                        return passthrough;
                    });
            });

        self.scrolltableContainer = self.scrollWidget.node.parentNode;

        self.nextMessagePreview = self.firstWithClass(
            self.contentTableGrid[1][2],
            "next-message-preview");

        self.status = Quotient.Mailbox.Status(
                        self.firstNodeByAttribute(
                            "class", "mailbox-status-container"));

        self.delayedLoad(self.complexityLevel);
    },

    /**
     * Register the actions controller for this widget.
     *
     * @param controller: actions controller
     * @type controller: L{Quotient.Message.ActionsController}
     */
    function setActionsController(self, controller) {
        self.messageActions = controller;
        self.messageActions.setActionListener(self);
        self.initializationDeferred.addCallback(
            function(passThrough) {
                self._setupActionButtonsForView(
                    self.scrollWidget.viewSelection['view']);
            });
    },

    /**
     * Replace the message detail with a compose widget.
     *
     * @param reloadMessage: if true, the currently selected message will be
     * reloaded and displayed after the compose widget has been dismissed
     *
     * @return: L{Divmod.Defer.Deferred} which fires when the compose widget
     * has been loaded, or after it has been dismissed if C{reloadMessage} is
     * true
     */
    function compose(self, reloadMessage/*=true*/) {
        if(reloadMessage == undefined) {
            reloadMessage = true;
        }
        var result = self.callRemote("getComposer");

        result.addCallback(
            function(composeInfo) {
                return self.addChildWidgetFromWidgetInfo(composeInfo);
            });
        result.addCallback(
            function(composer) {
                self.setMessageDetail(composer.node);
                composer.fitInsideNode(self.messageDetail);
                return composer;
            });
        if(reloadMessage) {
            result.addCallback(
                function(composer) {
                    return self.reloadMessageAfterComposeCompleted(composer);
                });
        }
        return result;
    },

    /**
     * DOM event handler for compose.  Call L{compose} and return C{false}
     *
     * @return C{false}
     */
    function dom_compose(self) {
        self.compose();
        return false;
    },
    /**
     * Reload the currently selected message after C{composer} has completed
     * (either been dismissed or sent a message)
     *
     * @type composer: L{Quotient.Compose.Controller}
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function reloadMessageAfterComposeCompleted(self, composer) {
        composer.completionDeferred.addCallback(function (x) {
                /* If there aren't any messages, don't try to get a message detail.
                 */
                if (self.scrollWidget.model.rowCount()) {
                    return self._getMessageDetail(x);
                }
            });
        return composer.completionDeferred;
    },

    /**
     * level = integer between 1 and 3
     * node = the image that represents this complexity level
     * report = boolean - should we persist this change
     */
    function setComplexity(self, level, node, report) {
        if (node.className == "selected-complexity-icon") {
            return;
        }

        self._setComplexityVisibility(level);
        self.complexityLevel = level;

        if (report) {
            self.callRemote("setComplexity", level);
        }

        var gparent = node.parentNode.parentNode;
        var selected = Nevow.Athena.FirstNodeByAttribute(gparent, "class", "selected-complexity-icon");

        selected.className = "complexity-icon";
        self.complexityHover(selected);
        if (!report) {
            self.complexityHover(node);
        }
        node.className = "selected-complexity-icon";
        self.recalculateMsgDetailWidth(false);
    },

    function _getViewCountNode(self, view) {
        var viewNode = self.mailViewNodes[view];
        if (viewNode === undefined || viewNode === null) {
            throw new Error("Request for invalid view: " + view);
        }
        var count = Divmod.Runtime.theRuntime.firstNodeByAttribute(
            viewNode.parentNode, 'class', 'count').firstChild;
        return count;
    },

    /**
     * Return the count of unread messages in the given view.
     *
     * @param view: One of "all", "inbox", "spam" or "sent".
     */
    function getUnreadCountForView(self, view) {
        return parseInt(self._getViewCountNode(view).nodeValue);
    },

    function setUnreadCountForView(self, view, count) {
        var countNode = self._getViewCountNode(view);
        countNode.nodeValue = String(count);
    },

    /**
     * @return: an array of objects with C{name} and C{key} properties bound to
     * the name and unique server-side identifier for each person being
     * displayed in the view selection chooser.
     */
    function getPeople(self) {
        var people = [];
        var personChooser = Divmod.Runtime.theRuntime.firstNodeByAttribute(
            self.contentTableGrid[0][0], 'class', 'person-chooser');
        var personChoices = Divmod.Runtime.theRuntime.nodesByAttribute(
            personChooser, 'class', 'list-option');
        var nameNode, keyNode;
        var name, key;
        for (var i = 0; i < personChoices.length; ++i) {
            nameNode = Divmod.Runtime.theRuntime.firstNodeByAttribute(
                personChoices[i], 'class', 'opt-name');
            keyNode = Divmod.Runtime.theRuntime.firstNodeByAttribute(
                personChoices[i], 'class', 'person-key');
            name = nameNode.firstChild.nodeValue;
            key = keyNode.firstChild.nodeValue;
            people.push({name: name, key: key});
        }
        return people;
    },

    function _getContentTableGrid(self) {
        self.inboxContent = self.firstNodeByAttribute("class", "inbox-content");
        var firstByTagName = function(container, tagName) {
            return self.getFirstElementByTagNameShallow(container, tagName);
        }
        var contentTableContainer = Divmod.Runtime.theRuntime.getElementsByTagNameShallow(
                                        self.inboxContent, "div")[1];
        var contentTable = firstByTagName(contentTableContainer, "table");
        var contentTableRows = Divmod.Runtime.theRuntime.getElementsByTagNameShallow(
                                    firstByTagName(contentTable, "tbody"), "tr");
        var contentTableGrid = [];

        for(var i = 0; i < contentTableRows.length; i++) {
            contentTableGrid.push(
                Divmod.Runtime.theRuntime.getElementsByTagNameShallow(
                    contentTableRows[i], "td"));
        }
        return {table: contentTable, grid: contentTableGrid};
    },

    function _getContentTableColumn(self, offset) {
        return MochiKit.Base.map(
            function(r) {
                if(offset+1 <= r.length) {
                    return r[offset];
                }
            }, self.contentTableGrid);
    },

    function rowsFetched(self, count) {
        if(0 < count && self._batchSelection) {
            var pred = self._batchSelectionPredicates[self._batchSelection];
            self.scrollWidget.massSelectOrNot(true, pred);
        }
    },

    /**
     * XXX
     */
    function changeBatchSelectionByNode(self, buttonNode) {
        /*
         * This doesn't actually use the button node, since it has essentially
         * nothing to do with the state of the batch selection nodes in the
         * DOM.
         */
        var selectNode = Divmod.Runtime.theRuntime.firstNodeByAttribute(
            self.node, 'name', 'batch-type');
        return self.changeBatchSelection(selectNode.value);
    },

    /**
     * XXX
     */
    function changeBatchSelection(self, to) {
        var anySelected = (to != "none");
        var selectionPredicate = self._batchSelectionPredicates[to];

        self.scrollWidget.massSelectOrNot(anySelected, selectionPredicate);

        if (anySelected) {
            self._batchSelection = to;
        } else {
            self._batchSelection = null;
        }
    },

    /**
     * Return a two element list.  The first element will be a sequence
     * of web IDs for currently selected messages who do not fit the batch
     * selection criteria, and the second element will be a sequence of
     * web IDs for messages who fit the batch selection criteria but are
     * not currently selected.  Both lists may be empty
     */
    function getBatchExceptions(self) {
        var row, webID,
            sw = self.scrollWidget,
            sel = self._batchSelection,
            pred = self._batchSelectionPredicates[sel],
            include = [],
            exclude = [];

        if(!pred) {
            pred = function(r) {
                /* always true for "all", always false for "none" */
                return sel == "all";
            }
        }

        var indices = sw.model.getRowIndices();
        for(var i = 0; i < indices.length; ++i) {
            row = sw.model.getRowData(i);
            webID = row["__id__"];
            /* if it's selected */
            if (row.__selected__) {
                /* and it doesn't fulfill the predicate */
                if (!pred(row)) {
                    /* then mark it for explicit inclusion */
                    include.push(webID);
                }
                /* or it's not selected and does fulfill the predicate */
            } else if (pred(row)) {
                /* then mark it for explicit exclusion */
                exclude.push(webID);
            }
        }
        return [include, exclude];
    },

    function _removeRows(self, rows) {
        /*
         * This action is removing rows from visibility.  Drop them
         * from the model.  Change the currently selected row, if
         * necessary.
         */
        var index;

        for (var i = rows.length - 1; i > -1; --i) {
            index = self.scrollWidget.model.findIndex(rows[i]);
            self.scrollWidget.removeRow(index);
        }

        return self.scrollWidget.scrolled().addCallback(
            function(ignored) {
                /*
                 * XXX - Selecting the first row is wrong - we should select a
                 * row very near to the previously selected row, instead.
                 */
                if (self.scrollWidget.getActiveRow() == null) {
                    return self.scrollWidget.activateFirstRow();
                }
            });
    },

    /**
     * Call the given function after setting the message detail area's opacity
     * to 0.2.  Set the message detail area's opacity back to 1.0 after the
     * Deferred the given function returns has fired.
     */
    function withReducedMessageDetailOpacity(self, callable) {
        self.messageDetail.style.opacity = 0.2;
        var result = callable();
        result.addBoth(
            function(passthrough) {
                self.messageDetail.style.opacity = 1.0;
                return passthrough;
            });
        return result;
    },

    /**
     * Show a dialog alerting the user that we are currently performing a
     * long-running action, and so can't start another one
     */
    function _showBusyActionDialog(self) {
        Quotient.Common.Util.showSimpleWarningDialog(
            "Cannot perform a long running action as one is currently in progress");
    },

    /**
     * Construct the scaffolding necessary to perform a long running action
     *
     * @param f: thunk returning a deferred firing when the action is
     * complete.  Will only be called if another long running action is not
     * underway at the time this method is called
     *
     * @param message: user-facing message describing the action
     *
     * @return: the deferred returned from C{f} if the action is performed,
     * otherwise null
     */
    function _wrapLongRunningAction(self, f, message) {
        if(self._longRunningActionDeferred != null) {
            self._showBusyActionDialog();
            return null;
        }
        var result = self.withReducedMessageDetailOpacity(f);
        self._longRunningActionDeferred = result;
        result.addCallback(
            function(passthrough) {
                self._longRunningActionDeferred = null;
                return passthrough;
            });

        self.status.showStatusUntilFires(result, message);

        return result;
    },

    function touchBatch(self, action, isDestructive, extraArguments) {
        return self._wrapLongRunningAction(
            function() {
                var exceptions = self.getBatchExceptions();
                var include = exceptions[0];
                var exclude = exceptions[1];

                var acted = self.callRemote(
                    "actOnMessageBatch", action, self.scrollWidget.viewSelection,
                    self._batchSelection, include, exclude, extraArguments);

                acted.addCallback(
                    function(counts) {
                        var readTouchedCount = counts[0];
                        var unreadTouchedCount = counts[1];

                        if (isDestructive) {
                            return self.scrollWidget.emptyAndRefill().addCallback(
                                function(ignored) {
                                    return self.scrollWidget.activateFirstRow();
                                });
                        }
                        return null;
                    });

                return acted;
            }, "Performing a batch action");
    },

    /**
     * similar to C{getElementsByTagNameShallow}, but returns the
     * first matching element
     */
    function getFirstElementByTagNameShallow(self, node, tagName) {
        var child;
        for(var i = 0; i < node.childNodes.length; i++) {
            child = node.childNodes[i];
            if(child.tagName && child.tagName.toLowerCase() == tagName) {
                return child;
            }
        }
    },

    /**
     * Decrement the unread message count that is displayed next
     * to the name of the view called C{viewName} C{byHowMuch}
     *
     * @param viewName: string
     * @param byHowMuch: number
     * @return: undefined
     */
    function decrementMailViewCount(self, viewName, byHowMuch) {
        self.setUnreadCountForView(
            viewName,
            self.getUnreadCountForView(viewName) - byHowMuch);
    },

    /**
     * Decrement the unread message count that is displayed next to
     * the name of the currently active view in the view selector.
     *
     * (e.g. "Inbox (31)" -> "Inbox (30)")
     */
    function decrementActiveMailViewCount(self, byHowMuch/*=1*/) {
        if(byHowMuch == undefined) {
            byHowMuch = 1;
        }

        self.decrementMailViewCount(
            self.scrollWidget.viewSelection["view"], byHowMuch);
    },

    /**
     * Update the counts that are displayed next
     * to the names of mailbox views in the view selector
     *
     * @param counts: mapping of view names to unread
     *                message counts
     */
    function updateMailViewCounts(self, counts) {
        var cnode;
        for(var k in counts) {
            cnode = self.firstWithClass(self.mailViewNodes[k], "count");
            cnode.firstChild.nodeValue = counts[k];
        }
    },

    function delayedLoad(self, complexityLevel) {
        setTimeout(function() {
            self.setScrollTablePosition("absolute");
            self.highlightExtracts();
            self.setInitialComplexity(complexityLevel).addCallback(
                function() {
                    self.finishedLoading();
                    self.resized(true);
                    /*
                     * Since we probably just made the scrolling widget
                     * bigger, it is quite likely that we exposed some rows
                     * without data.  Ask it to check on that and deal with
                     * it, if necessary.  This is a kind of gross hack
                     * necessitated by the lack of a general mechanism for
                     * cooperation between the view and the model. -exarkun
                     */
                    self.scrollWidget._getSomeRows(true).addBoth(
                        function(result) {
                            self._secondGetSomeRows.callback(result);
                        });
                });
        }, 0);
    },

    function setInitialComplexity(self, complexityLevel) {
        var cc = self.firstWithClass(self.node, "complexity-icons");
        self.setComplexity(complexityLevel,
                            cc.getElementsByTagName("img")[3-complexityLevel],
                            false);
        /* firefox goofs the table layout unless we make it
            factor all three columns into it.  the user won't
            actually see anything strange */
        if(complexityLevel == 1) {
            var D = Divmod.Defer.Deferred();
            self._setComplexityVisibility(3);
            /* two vanilla calls aren't enough, firefox won't
                update the viewport */
            setTimeout(function() {
                self._setComplexityVisibility(1);
                D.callback(null);
            }, 1);
            return D;
        }
        return Divmod.Defer.succeed(null);
    },


    function getHeight(self) {
        /* This is the cumulative padding/margin for all elements whose
         * heights we factor into the height calculation below.  clientHeight
         * includes border but not padding or margin.
         * FIXME: change all this code to use offsetHeight, not clientHeight
         */
        var basePadding = 14;
        return (Divmod.Runtime.theRuntime.getPageSize().h -
                self.messageBlockYPos -
                self.totalFooterHeight -
                basePadding);

    },


    /**
     * resize the inbox table and contents.
     * @param initialResize: is this the first/initial resize?
     *                       (if so, then our layout constraint jiggery-pokery
     *                        is not necessary)
     */
    function resized(self, initialResize) {
        var getHeight = function(node) {
            return Divmod.Runtime.theRuntime.getElementSize(node).h;
        }
        var setHeight = function(node, height) {
            if(0 < height) {
                node.style.height = height + "px";
            }
        }

        if(!self.totalFooterHeight) {
            var blockFooter = self.firstNodeByAttribute("class", "right-block-footer");
            self.blockFooterHeight = getHeight(blockFooter);
            self.totalFooterHeight = self.blockFooterHeight + 5;
        }

        var swHeight = self.getHeight();
        setHeight(self.contentTableGrid[0][1], swHeight);
        setHeight(self.scrollWidget._scrollViewport, swHeight);

        setHeight(self.messageDetail, (Divmod.Runtime.theRuntime.getPageSize().h -
                                       self.ypos - 14 -
                                       self.totalFooterHeight));

        setTimeout(
            function() {
                self.recalculateMsgDetailWidth(initialResize);
            }, 0);
    },

    function recalculateMsgDetailWidth(self, initialResize) {
        if(!self.initialResize) {
            self.messageDetail.style.width = "100%";
        }

        document.body.style.overflow = "hidden";
        self.messageDetail.style.overflow = "hidden";

        self.messageDetail.style.width = Divmod.Runtime.theRuntime.getElementSize(
                                            self.messageDetail).w + "px";

        self.messageDetail.style.overflow = "auto";
        document.body.style.overflow = "auto";
    },

    function finishedLoading(self) {
        self.node.removeChild(self.firstWithClass(self.node, "loading"));
    },

    function firstWithClass(self, n, cls) {
        return Nevow.Athena.FirstNodeByAttribute(n, "class", cls);
    },

    function complexityHover(self, img) {
        if(img.className == "selected-complexity-icon") {
            return;
        }
        if(-1 < img.src.search("unselected")) {
            img.src = img.src.replace("unselected", "selected");
        } else {
            img.src = img.src.replace("selected", "unselected");
        }
    },

    function _groupSetDisplay(self, nodes, display) {
        for(var i = 0; i < nodes.length; i++) {
            if(nodes[i]) {
                nodes[i].style.display = display;
            }
        }
    },

    function hideAll(self, nodes) {
        self._groupSetDisplay(nodes, "none");
    },

    function showAll(self, nodes) {
        self._groupSetDisplay(nodes, "");
    },

    function _setComplexityVisibility(self, c) {
        var messageBody;

        if (c == 1) {
            self.contentTableGrid[0][0].style.display = "none";
            self.contentTableGrid[1][0].style.display = "none";
            self.hideAll(self._getContentTableColumn(1));
            self.setScrollTablePosition("absolute");
            self.viewShortcutSelect.style.display = "";
            /* use the default font-size, because complexity 1 is the default
             * complexity.
             */
        } else if (c == 2) {
            self.contentTableGrid[0][0].style.display = "none";
            self.contentTableGrid[1][0].style.display = "none";
            self.showAll(self._getContentTableColumn(1));
            self.setScrollTablePosition("static");
            self.viewShortcutSelect.style.display = "";
        } else if (c == 3) {
            self.contentTableGrid[0][0].style.display = "";
            self.contentTableGrid[1][0].style.display = "";
            self.showAll(self._getContentTableColumn(1));
            self.setScrollTablePosition("static");
            self.viewShortcutSelect.style.display = "none";
        }

        try {
            messageBody = self.firstWithClass(self.messageDetail, "message-body");
            messageBody.style.fontSize = fontSize;
        } catch (e) {
            0;
        }
        self.node.className = "complexity-" + c + "-inbox";
    },

    function setScrollTablePosition(self, p) {
        self.scrolltableContainer.style.position = p;
        var d;
        if(p == "absolute") {
            d = "none";
        } else {
            d = "";
        }
    },

    function fastForward(self, toMessageID) {
        return self.withReducedMessageDetailOpacity(
            function() {
                return self.callRemote("fastForward", self.scrollWidget.viewSelection, toMessageID).addCallback(
                    function(newCurrentMessage) {
                        var rowData = null;
                        try {
                            rowData = self.scrollWidget.model.findRowData(toMessageID);
                        } catch (err) {
                            if (err instanceof Mantissa.ScrollTable.NoSuchWebID) {
                                /*
                                 * Someone removed the row we were going to display.  Oh well, do nothing, instead.
                                 */

                            } else {
                                throw err;
                            }
                        }
                        if (rowData != null) {
                            rowData.read = true;
                            return self.setMessageContent(toMessageID,
                                                          newCurrentMessage);
                        }
                    });
            });
    },

    /**
     * Change the view being viewed.
     *
     * @param key: The parameter of the view to change.  One of C{"view"},
     * C{"tag"}, C{"person"}, or C{"account"}.
     *
     * @param value: The new value of the given view parameter.
     *
     * @return: A Deferred which fires when the view selection has been changed
     * and a new set of messages is being displayed.
     */
    function changeViewSelection(self, key, value) {
        return self.scrollWidget.changeViewSelection(key, value).addCallback(
            function(messageCount) {
                if (messageCount) {
                    self.messageActionsNode.style.visibility = "";
                } else {
                    self.messageActionsNode.style.visibility = "hidden";
                }
                self.changeBatchSelection('none');
            });
    },

    /**
     * Change the class of the given node to C{"selected-list-option"}, change
     * the class of any existing selected nodes in the same select group to
     * C{"list-option"}, and change the C{onclick} handler of those nodes to
     * be the same as the C{onclick} handler for the given node.
     */
    function _selectListOption(self, n) {
        var sibs = n.parentNode.childNodes;
        for(var i = 0; i < sibs.length; i++) {
            if(sibs[i].className == "selected-list-option") {
                sibs[i].className = "list-option";
                if(!sibs[i].onclick) {
                    sibs[i].onclick = n.onclick;
                }
            }
        }
        n.className = "selected-list-option";
    },

    /**
     * Select a tag by its DOM node.
     */
    function chooseTagByNode(self, tagNode) {
        var tagName = Divmod.Runtime.theRuntime.firstNodeByAttribute(
            tagNode, 'class', 'opt-name');
        return self.chooseTag(tagName.firstChild.nodeValue);
    },

    /**
     * Locate the node for a particular choice within a particular category in
     * the view filter, and make it appear selected.
     *
     * @param filterType: The filter type the choice belongs to.  Possible
     * choices include "view", "tag", "person"
     * @type filterType: C{String}
     *
     * @param choice: The name of the choice.  For a filter type of "tag",
     * this would be the tag name that appears in the tag list, etc.
     * @type choice: C{String}
     *
     * @rtype: C{undefined}
     */
    function selectFilterChoiceNode(self, filterType, choice) {
        /* XXX each of these filter panes should be a widget */
        var filterNode = self.firstNodeByAttribute(
            "class", filterType + "-chooser"),
            optionNode, optionNameNode;
        for(var i = 0; i < filterNode.childNodes.length; i++) {
            optionNode = filterNode.childNodes[i];
            if(optionNode.className == "list-option" ||
               optionNode.className == "selected-list-option") {
                optionNameNode = Nevow.Athena.FirstNodeByAttribute(
                    optionNode, "class", "opt-name");
                if(optionNameNode.firstChild.nodeValue == choice) {
                    self._selectListOption(optionNode);
                    return;
                }
            }
        }
        throw new Error("no choice " + choice + " in filter " + filterType);
    },

    /**
     * Select a new tag from which to display messages.  Adjust local state to
     * indicate which tag is being viewed and, if necessary, ask the server
     * for the messages to display.
     *
     * @type tagName: string
     * @param tagName: The tag to select.
     */
    function chooseTag(self, tagName) {
        self.selectFilterChoiceNode("tag", tagName);
        if (tagName.toLowerCase() == 'all') {
            tagName = null;
        }
        return self.changeViewSelection("tag", tagName);
    },

    /**
     * Add the given tags as options inside the "View By Tag" element
     */
    function addTagsToViewSelector(self, taglist) {
        var tc = self.firstWithClass(self.contentTableGrid[0][0], "tag-chooser");
        var choices = tc.getElementsByTagName("span");
        var currentTags = [];
        for(var i = 0; i < choices.length; i++) {
            currentTags.push(choices[i].firstChild.nodeValue);
        }
        var needToAdd = Quotient.Common.Util.difference(taglist, currentTags);
        /* the tags are unordered at the moment, probably not ideal */
        for(i = 0; i < needToAdd.length; i++) {
            tc.appendChild(
                MochiKit.DOM.DIV({"class": "list-option",
                                  "onclick": function() {
                                      self.chooseTagByNode(this);
                                    }}, MochiKit.DOM.SPAN({"class": "opt-name"}, needToAdd[i])));
        }
    },

    /**
     * Call chooseMailView with the view name contained in the child node of
     * C{viewNode} with class "opt-name".
     */
    function chooseMailViewByNode(self, viewNode) {
        var view = Divmod.Runtime.theRuntime.firstNodeByAttribute(
            viewNode, 'class', 'opt-name');
        return self.chooseMailView(view.firstChild.nodeValue.toLowerCase());
    },

    /**
     * Call chooseMailView with the view contained in the value of attribute
     * of the view shortcut <select> C{shortcutNode}
     */
    function chooseMailViewByShortcutNode(self, shortcutNode) {
        return self.chooseMailView(shortcutNode.value);
    },

    /**
     * Select a new, semantically random set of messages to display.  Adjust
     * local state to indicate which random crap is being viewed and, if
     * necessary, ask the server for the messages to display.
     *
     * @param viewName: the name of the view to switch to
     * @return: L{Deferred}, which will fire after view change is complete
     */
    function chooseMailView(self, viewName) {
        self._selectViewShortcut(viewName);
        self._selectListOption(self.mailViewNodes[viewName].parentNode);
        self._setupActionButtonsForView(viewName);

        return self.changeViewSelection("view", viewName);
    },

    function _setupActionButtonsForView(self, viewName) {
        var actions = self.viewToActions[viewName];
        if (actions === undefined) {
            throw new Error("Unknown view: " + viewName);
        }
        self.messageActions.enableOnlyActions(actions);
    },

    /**
     * Select the view shortcut link that corresponds to the
     * current mail view, if any.
     */
    function _selectViewShortcut(self, viewName) {
        var current = viewName;
        var options = self.viewShortcutSelect.getElementsByTagName("option");
        for(var i = 0; i < options.length; i++) {
            if(options[i].value == current) {
                self.viewShortcutSelect.selectedIndex = i;
                break;
            }
        }
    },

    /**
     * Select a new account by DOM node.
     */
    function chooseAccountByNode(self, accountNode) {
        var accountName = Divmod.Runtime.theRuntime.firstNodeByAttribute(
            accountNode, 'class', 'opt-name');
        self._selectListOption(accountNode);
        return self.chooseAccount(accountName.firstChild.nodeValue);
    },

    /**
     * Select a new account, the messages from which to display.  Adjust local
     * state to indicate which account's messages are being viewed and, if
     * necessary, ask the server for the messages to display.
     *
     * @param accountName: The name of the account to view messages from.
     * @return: C{undefined}
     */
    function chooseAccount(self, accountName) {
        if (accountName == 'all') {
            accountName = null;
        }

        return self.changeViewSelection("account", accountName);
    },

    /**
     * Select a new person by DOM node.
     */
    function choosePersonByNode(self, personNode) {
        var personKey = Divmod.Runtime.theRuntime.firstNodeByAttribute(
            personNode, 'class', 'person-key');
        self._selectListOption(personNode);
        return self.choosePerson(personKey.firstChild.nodeValue);
    },

    /**
     * Select a new person, the messages from which to display.  Adjust local
     * state to indicate which person's messages are being viewed and, if
     * necessary, ask the server for the messages to display.
     *
     * @param n: The node which this input handler is attached to.
     * @return: C{undefined}
     */
    function choosePerson(self, personKey) {
        if(personKey == 'all') {
            personKey = null;
        }
        return self.changeViewSelection("person", personKey);
    },

    function setupMailViewNodes(self) {
        if (!self.mailViewBody) {
            var mailViewPane = self.firstWithClass(self.contentTableGrid[0][0], "view-pane-content");
            var mailViewBody = self.firstWithClass(mailViewPane, "pane-body");
            self.mailViewBody = self.getFirstElementByTagNameShallow(mailViewBody, "div");
        }

        var nodes = {};
        for (var view in self.viewToActions) {
            nodes[view] = null;
        }
        var e, nameNode, name;

        for(var i = 0; i < self.mailViewBody.childNodes.length; i++) {
            e = self.mailViewBody.childNodes[i];
            try {
                nameNode = Divmod.Runtime.theRuntime.firstNodeByAttribute(
                    e, 'class', 'opt-name');
            } catch (err) {
                if (err instanceof Divmod.Runtime.NodeAttributeError) {
                    continue;
                }
                throw err;
            }
            name = nameNode.firstChild.nodeValue.toLowerCase();
            nodes[name] = e.firstChild.nextSibling;
        }
        self.mailViewNodes = nodes;
    },


    /**
     * Perform the specified action.
     *
     * If the batch selection is set, perform it on that batch of messages.
     *
     * Otherwise if there is a selected group of messages, performed it on that
     * set of messages.
     *
     * Otherwise perform it on the currently displayed message.
     */
    function touch(self, action, isProgress, /* optional */ extraArguments) {
        if (extraArguments === undefined) {
            extraArguments = null;
        }

        if (self._batchSelection != null) {
            return self.touchBatch(action, isProgress, extraArguments);
        } else {
            return self.touchSelectedGroup(action, isProgress, extraArguments);
        }
    },

    /**
     * Like L{touch}, but acts upon the set of currently selected
     * messages in the scrolltable.
     *
     * @param isDestructive: does this action remove messages from the current
     *                       view?  this is subtly different to touchSelectedGroup's
     *                       "isProgress", because even for destructive message
     *                       actions, we might not need to request a new message
     *                       if the currently selected one is not a member of the
     *                       group being acted upon.
     */
    function touchSelectedGroup(self, action, isDestructive, extraArguments) {
        return self._wrapLongRunningAction(
            function() {
                var rows = [];
                function accumulate(row) {
                    rows.push(row.__id__);
                };

                self.scrollWidget.model.visitSelectedRows(accumulate);
                if (rows.length == 0) {
                    return Divmod.Defer.succeed(null);
                }

                var acted = self.callRemote(
                    "actOnMessageIdentifierList", action,
                    rows,
                    extraArguments);

                acted.addCallback(
                    function(counts) {
                        var readTouchedCount = counts[0];
                        var unreadTouchedCount = counts[1];

                        if (isDestructive) {
                            var result = self._removeRows(rows);
                            return result;
                        } else {
                            return null;
                        }

                    });

                return acted;
            }, "Performing a group action");
    },

    /**
     * Adjust the unread message counts.  Typically called after
     * performing a destructive action.  Takes into account the
     * destination of a set of messages by looking at the current
     * view and the action that was performed.
     *
     * @param args: array of arguments passed to callRemote() to
     *              initiate the action server-side.  typically
     *              something like ["archiveCurrentMessage"] or
     *              ["trainMessageGroup", true]
     * @param affectedUnreadCount: number of unread messages
     *                             affected by the action.
     * @return: undefined
     */
    function adjustCounts(self, args, affectedUnreadCount) {
        if(affectedUnreadCount == 0) {
            return;
        }

        var suffixes = ["CurrentMessage", "MessageGroup", "MessageBatch"];
        var action = args[0];
        for(var i = 0; i < suffixes.length; i++) {
            if(action.substr(action.length-suffixes[i].length) == suffixes[i]) {
                action = action.substr(0, action.length-suffixes[i].length);
                break;
            }
        }
        self.decrementActiveMailViewCount(affectedUnreadCount);

        var addTo;

        if(action == "archive") {
            addTo = "all";
        } else if(action == "train") {
            if(args[args.length-1]) {
                addTo = "spam";
            } else {
                addTo = "inbox";
            }
        } else {
            return;
        }

        self.decrementMailViewCount(addTo, -affectedUnreadCount);
    },

    /**
     * 'Printable' message action.  Delegate to
     * L{Quotient.Message.MessageDetail}
     */
    function messageAction_printable(self) {
        return self._getMessageDetail().addCallback(
            function (msg) {return msg.messageAction_printable()});
    },

    /**
     * 'Message source' message action. Delegate to
     * L{Quotient.Message.MessageDetail}
     */
    function messageAction_messageSource(self) {
        return self._getMessageDetail().addCallback(
            function (msg) {return msg.messageAction_messageSource()});
    },

    /**
     * 'Archive' message action
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_archive(self) {
        /*
         * Archived messages show up in the "all" view.  So, if we are in any
         * view other than that, this action should make the message
         * disappear.
         */
        return self.touch(
            "archive",
            self.scrollWidget.viewSelection["view"] != "archive");
    },

    /**
     * 'Unarchive' message action
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_unarchive(self) {
        return self.touch(
            "unarchive",
            self.scrollWidget.viewSelection["view"] == "archive");
    },

    /**
     * 'Delete' message action
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_delete(self) {
        return self.touch(
            "delete",
            self.scrollWidget.viewSelection["view"] != "trash");
    },

    /**
     * 'Undelete' message action
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_undelete(self) {
        return self.touch(
            "undelete",
            self.scrollWidget.viewSelection["view"] == "trash");
    },


    /**
     * 'Reply' message action
     *
     * @param reloadMessage: if true, the currently selected message will be
     * reloaded and displayed after the compose widget has been dismissed
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_reply(self, reloadMessage) {
        /*
         * This brings up a composey widget thing.  When you *send* that
         * message (or save it as a draft or whatever, I suppose), *then* this
         * action is considered to have been taken, and the message should be
         * archived and possibly removed from the view.  But nothing happens
         * *here*.
         *
         * Forward this action to the message detail, since reply only works
         * on one message at a time.
         */
        return self._getMessageDetail().addCallback(
            function (msg) {return msg.messageAction_reply(reloadMessage)});
    },

    /**
     * 'Forward' message action
     *
     * @param reloadMessage: if true, the currently selected message will be
     * reloaded and displayed after the compose widget has been dismissed
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_forward(self, reloadMessage) {
        /*
         * See messageAction_reply
         */
        return self._getMessageDetail().addCallback(
            function (msg) {return msg.messageAction_forward(reloadMessage)});
    },

    /**
     * 'Reply All' message action
     *
     * Load a compose widget with the "To" field set to all of the addresses
     * in the "From", "To", "CC" and "BCC" headers of the message we're
     * looking at
     *
     * @param reloadMessage: if true, the currently selected message will be
     * reloaded and displayed after the compose widget has been dismissed
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_replyAll(self, reloadMessage) {
        return self._getMessageDetail().addCallback(
            function (msg) {return msg.messageAction_replyAll(reloadMessage)});
    },

    /**
     * 'Redirect' message action
     *
     * @param reloadMessage: if true, the currently selected message will be
     * reloaded and displayed after the compose widget has been dismissed
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_redirect(self, reloadMessage) {
        return self._getMessageDetail().addCallback(
            function (msg) {return msg.messageAction_redirect(reloadMessage)});
    },


    /**
     * 'Edit' message action, allow user to edit a message as a draft.
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_editDraft(self) {
        return self._getMessageDetail().addCallback(
            function (msg) {return msg.messageAction_editDraft()});
    },

    /**
     * 'Train Spam' message action
     *
     * Instruct the server to train the spam filter using the current message
     * as an example of spam.  Remove the message from the message list if
     * appropriate.
     *
     * @return: A Deferred which fires when the training action has been
     * completed.
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_trainSpam(self) {
        return self.touch(
            "trainSpam",
            (self.scrollWidget.viewSelection["view"] != "spam"));
    },

    /**
     * 'Train Ham' message action
     *
     * Instruct the server to train the spam filter using the current message
     * as an example of ham.  Remove the message from the message list if
     * appropriate.
     *
     * @return: A Deferred which fires when the training action has been
     * completed.
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_trainHam(self) {
        return self.touch(
            "trainHam",
            (self.scrollWidget.viewSelection["view"] == "spam"));
    },

    /**
     * 'Defer' message action
     *
     * Defer the currently selected rows and update the display to indicate
     * that this has been done.
     *
     * This method added to avoid special-casing the touch* methods to know
     * about the defer operation.
     *
     * @param period: The period of time to defer the selected rows.
     * @return: A L{Divmod.Base.Deferred} that is passed through from
     * L{touch}.
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_defer(self, period) {
        var widget = self.scrollWidget;
        var batchAction = self._batchSelection != null;
        var destructive = widget.viewSelection["view"] != 'all';
        destructive = destructive || batchAction;
        var d = self.touch("defer", destructive, period);
        d.addCallback(
            function(passThrough) {
                if (!destructive) {
                    self._deferSelectedRows();
                }
                return passThrough;
            });
        return d;
    },

    /**
     * Set each of the rows in the selection as deferred.
     */
    function _deferSelectedRows(self) {
        self.scrollWidget.model.visitSelectedRows(
            function(row) {
                self.scrollWidget.setAsDeferred(row);
            });
    },

    /**
     * Remove all content from the message detail area and add the given node.
     */
    function setMessageDetail(self, node) {
        var innerNode;
        var widget;
        while ((innerNode = self.messageDetail.firstChild)) {
            /*
             * Find any widget which might own the node about to be removed and
             * detach it.
             */
            try {
                widget = Nevow.Athena.Widget.get(innerNode);
            } catch (err) {
                /*
                 * Nothing here, fine.
                 */
                widget = null;
            }
            if (widget && widget.node === innerNode) {
                widget.detach();
            }
            self.messageDetail.removeChild(innerNode);
        }
        self.messageDetail.appendChild(node);
    },

    function highlightExtracts(self) {
        /* We have to fetch the message body node each time because it gets
         * removed from the document each time a message is loaded.  We wrap it
         * in a try/catch because there are some cases where it's not going
         * to be available, like the "out of messages" case.  it's easier to
         * determine this here than with logic someplace else */
        try {
            var messageBody = self.firstWithClass(self.messageDetail, "message-body");
        } catch(e) {
            return;
        }

        Mantissa.DOMReplace.urlsToLinks(messageBody);
    },

    /**
     * Return a Defered which will fire the L{Quotient.Message.MessageDetail}
     * instance for the message currently loaded into the inbox.
     */
    function _getMessageDetail(self) {
        var active = self.scrollWidget.getActiveRow();
        if (active === null) {
            active = self.scrollWidget.model.getRowData(0);
            // XXX undefined behavior when there's no message - this should
            // *probably* be accounted for, but I guess nobody actually calls
            // it in this state?
        }
        return self.fastForward(active.__id__);
    },

    /**
     * Empty the message detail view area of content.
     */
    function clearMessageDetail(self) {
        self.messageDetail.scrollTop = 0;
        self.messageDetail.scrollLeft = 0;

        while (self.messageDetail.firstChild) {
            self.messageDetail.removeChild(self.messageDetail.firstChild);
        }
    },

    /**
     * Update the message detail area to display the specified message.  Return
     * a Deferred which fires when this has finished.
     */
    function updateMessageDetail(self, webID) {
        return self.fastForward(webID);
    },

    function onePattern(self, name) {
        if (name == "next-message") {
            return {
                'fillSlots': function(key, value) {
                    var result = value.replace(new RegExp('&', 'g'), '&amp;');
                    result = result.replace(new RegExp('<', 'g'), '&lt;');
                    result = result.replace(new RegExp('>', 'g'), '&gt;');
                    return (
                        '<div xmlns="http://www.w3.org/1999/xhtml">Next: ' +
                        result + '</div>');
                }
            };
        } else if (name == "no-more-messages") {
            return '<span xmlns="http://www.w3.org/1999/xhtml">No more messages.</span>';
        } else {
            throw new Error("No such pattern: " + name);
        }
    },

    /**
     * @param nextMessagePreview: An object with a subject property giving the
     * subject of the next message. See L{setMessageContent}. null if there is
     * no next message.
     */
    function updateMessagePreview(self, nextMessagePreview) {
        var pattern;
        if (nextMessagePreview != null) {
            /* so this is a message, not a compose fragment
             */
            pattern = self.onePattern('next-message');
            pattern = pattern.fillSlots('subject',
                                        nextMessagePreview['subject']);
        } else {
            pattern = self.onePattern('no-more-messages');
        }
        Divmod.Runtime.theRuntime.setNodeContent(self.nextMessagePreview,
                                                 pattern);
    },


    /**
     * Return the row data which should be used for the preview display, if the
     * given webID is currently being displayed.
     */
    function _findPreviewRow(self, webID) {
        var previewData = undefined;
        var messageIndex = self.scrollWidget.model.findIndex(webID);
        /*
         * Look after it
         */
        try {
            previewData = self.scrollWidget.model.getRowData(messageIndex + 1);
        } catch (err) {
            if (!(err instanceof Divmod.IndexError)) {
                throw err;
            }
            try {
                /*
                 * Look before it
                 */
                previewData = self.scrollWidget.model.getRowData(messageIndex - 1);
            } catch (err) {
                if (!(err instanceof Divmod.IndexError)) {
                    throw err;
                }
                /*
                 * No preview data for you.
                 */
            }
        }

        if (previewData === undefined) {
            return null;
        } else {
            return previewData;
        }
    },

    /**
     * Extract the data relevant for a message preview from the given data row.
     */
    function _getPreviewData(self, row) {
        return {"subject": row["subject"]};
    },

    /**
     * @param nextMessagePreview: An object with a subject property giving
     * the subject of the next message.  This value is not necessarily HTML;
     * HTML entities should not be escaped and markup will not be
     * interpreted (XXX - is this right?).
     *
     * @param currentMessageDisplay: Components of a MessageDetail widget,
     * to be displayed in the message detail area of this controller.
     *
     * @return: The MessageDetail widget displayed.
     */
    function setMessageContent(self, toMessageID, currentMessageDisplay) {
        self.messageDetail.scrollTop = 0;
        self.messageDetail.scrollLeft = 0;

        return self.addChildWidgetFromWidgetInfo(currentMessageDisplay).addCallback(
            function(widget) {
                self.setMessageDetail(widget.node);

                /* highlight the extracts here; the next message preview will
                 * be null for the last message, but we still want to
                 * highlight the extracts in that case.  it won't do any harm
                 * if there isn't actually a message body, as
                 * highlightExtracts() knows how to handle that */
                self.highlightExtracts();

                var preview = self._findPreviewRow(toMessageID);
                if (preview !== null) {
                    self.updateMessagePreview(self._getPreviewData(preview));
                } else {
                    self.updateMessagePreview(null);
                }

                /* if this is the "no more messages" pseudo-message,
                   then there won't be any message body */
                try {
                    var messageBody = self.firstWithClass(
                        self.messageDetail,
                        "message-body");
                } catch(e) {
                    return widget;
                }
                /* set the font size to the last value used in
                   _setComplexityVisibility() */
                messageBody.style.fontSize = self.fontSize;
                return widget;
            });
    });
