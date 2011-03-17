// import Quotient
// import Quotient.Common
// import Mantissa.AutoComplete
// import Mantissa.LiveForm
// import Fadomatic
// import Mantissa.ScrollTable

Quotient.Compose.AddAddressFormWidget = Mantissa.LiveForm.FormWidget.subclass('Quotient.Compose.AddAddressFormWidget');
/**
 * Trivial Mantissa.LiveForm.FormWidget subclass which reloads the closest
 * sibling FromAddressScrollTable after we have successfully submitted
 */
Quotient.Compose.AddAddressFormWidget.methods(
    function submitSuccess(self, result) {
        /* get our sibling FromAddressScrollTable */
        var sf = Nevow.Athena.FirstNodeByAttribute(
                    self.widgetParent.node,
                    "athena:class",
                    "Quotient.Compose.FromAddressScrollTable");
        Nevow.Athena.Widget.get(sf).emptyAndRefill();
        return Quotient.Compose.AddAddressFormWidget.upcall(
                    self, "submitSuccess", result);
    });

Quotient.Compose.DeleteFromAddressAction = Mantissa.ScrollTable.Action.subclass("Quotient.Compose.DeleteFromAddressAction");
/**
 * Action which deletes from addresses, and prevents the system address from
 * getting deleted
 */
Quotient.Compose.DeleteFromAddressAction.methods(
    function __init__(self, systemAddrWebID) {
        Quotient.Compose.DeleteFromAddressAction.upcall(
            self, "__init__", "delete", "Delete", null,
            "/Mantissa/images/delete.png");
        self.systemAddrWebID = systemAddrWebID;
    },

    function handleSuccess(self, scrollingWidget, row, result) {
        return scrollingWidget.emptyAndRefill();
    },

    function enableForRow(self, row) {
        return !(row._default || row.__id__ == self.systemAddrWebID);
    });

Quotient.Compose.SetDefaultFromAddressAction = Mantissa.ScrollTable.Action.subclass("Quotient.Compose.SetDefaultFromAddressAction");
/**
 * Action which sets a from address as the default
 */
Quotient.Compose.SetDefaultFromAddressAction.methods(
    function __init__(self) {
        Quotient.Compose.SetDefaultFromAddressAction.upcall(
            self, "__init__", "setDefaultAddress", "Set Default");
    },

    function handleSuccess(self, scrollingWidget, row, result) {
        return scrollingWidget.emptyAndRefill();
    },

    function enableForRow(self, row) {
        return !row._default;
    });

Quotient.Compose.FromAddressScrollTable = Mantissa.ScrollTable.FlexHeightScrollingWidget.subclass('Quotient.Compose.FromAddressScrollTable');
/**
 * Mantissa.ScrollTable.ScrollingWidget subclass for displaying FromAddress
 * items
 */
Quotient.Compose.FromAddressScrollTable.methods(
    function __init__(self, node, metadata, systemAddrWebID) {
        self.columnAliases = {smtpHost: "SMTP Host",
                              smtpPort: "SMTP Port",
                              smtpUsername: "SMTP Username",
                              _address: "Address",
                              _default: "Default"};
        self.actions = [Quotient.Compose.SetDefaultFromAddressAction(),
                        Quotient.Compose.DeleteFromAddressAction(
                            systemAddrWebID)];
        self.systemAddrWebID = systemAddrWebID;
        Quotient.Compose.FromAddressScrollTable.upcall(self, "__init__", node, metadata, 5);
    },

    /**
     * Override default implementation to provide fallback column values -
     * "None" instead of the empty string.  Also mark the default row
     */
    function makeCellElement(self, colName, rowData) {
        if(rowData[colName] === null) {
            rowData[colName] = "None";
        }
        return Quotient.Compose.FromAddressScrollTable.upcall(
                    self, "makeCellElement", colName, rowData);
    });


Quotient.Compose.FileUploadController = Divmod.Class.subclass('Quotient.Compose.FileUploadController');

/**
 * I am the controller for the file upload form, which gets loaded
 * in a iframe inside the compose page
 */
Quotient.Compose.FileUploadController.methods(
    /**
     * @param iframeDocument: "document" in the namespace of the file upload iframe
     * @param form: the file upload form element
     */
    function __init__(self, iframeDocument, form) {
        self.form = form;
        self.compose = Quotient.Compose.Controller.get(
                        Nevow.Athena.NodeByAttribute(
                               document.documentElement,
                               "athena:class",
                               "Quotient.Compose.Controller"));
        self.iframeDocument = iframeDocument;
    },

    /**
     * Tell our parent - the compose widget - that we're busy uploading a file
     */
    function notifyParent(self) {
        self.compose.uploading();
        self.iframeDocument.body.style.opacity = .1;
        self.form.onsubmit = function() {
            return false;
        }
    },

    /**
     * Called when our document loads.  Checks whether the document contains
     * information about a completed upload, e.g. if the page load is the
     * result of a form POST.
     */
    function checkForFileData(self) {
        var fileData = self.iframeDocument.getElementById("file-data");
        if(fileData.childNodes.length) {
            self.compose.gotFileData(
                eval("(" + fileData.firstChild.nodeValue + ")"));
        }
    },

    /**
     * Called when the value of our <input type="file"> changes value.
     * Enables the upload button.
     */
    function fileInputChanged(self) {
        self.form.elements.upload.disabled = false;
    });



/**
 * L{Mantissa.AutoComplete.View} subclass which knows how to turn
 * [displayName, emailAddress] pairs into something a user might understand
 */
Quotient.Compose.EmailAddressAutoCompleteView = Mantissa.AutoComplete.View.subclass('Quotient.Compose.EmailAddressAutoCompleteView');
Quotient.Compose.EmailAddressAutoCompleteView.methods(
    /**
     * For a pair C{nameAddr} containing [displayName, emailAddress], return something
     * of the form '"displayName" <emailAddress>'.  If displayName is the empty
     * string, return '<emailAddress>'.
     */
    function _reconstituteAddress(self, nameAddr) {
        var addr;
        if(0 < nameAddr[0].length) {
            addr = '"' + nameAddr[0] + '" ';
        } else {
            addr = "";
        }
        return addr + '<' + nameAddr[1] + '>';
    },

    /**
     * Override default implementation to turn the [displayName, emailAddress]
     * pair into a string displayable to the user, via L{_reconstituteAddress}
     */
    function makeCompletionNode(self, completion) {
        return Quotient.Compose.EmailAddressAutoCompleteView.upcall(
            self, "makeCompletionNode", self._reconstituteAddress(completion));
    });

/**
 * L{Mantissa.AutoComplete.Model} subclass which is aware of the fact that the
 * completions list is not a sequence of strings, but a sequence of
 * [displayName, emailAddress] pairs.  We do this so the text "jo" can match
 * "Joanna Jones" <jj@jj.com> and "Morris the slob" <joan@joan.com>
 */
Quotient.Compose.EmailAddressAutoCompleteModel = Mantissa.AutoComplete.Model.subclass('Quotient.Compose.EmailAddressAutoCompleteModel');
Quotient.Compose.EmailAddressAutoCompleteModel.methods(
    /**
     * Given an email address C{addr}, and a pair containing [displayName,
     * emailAddress], return a boolean indicating whether emailAddress or
     * any of the words in displayName or emailAddress is a prefix of C{addr}
     */
    function isCompletion(self, addr, nameAddr) {
        var strings = nameAddr[0].split(/\s+/).concat(
            nameAddr).concat(nameAddr[1].split(/@/));
        for(var i = 0; i < strings.length; i++) {
            if(Quotient.Compose.EmailAddressAutoCompleteModel.upcall(
                    self, "isCompletion", addr, strings[i])) {
                return true;
            }
        }
        return false;
    });

/**
 * Base class for composery things
 */
Quotient.Compose._Controller = Mantissa.LiveForm.FormWidget.subclass('Quotient.Compose._Controller');
Quotient.Compose._Controller.methods(
    /**
     * @param inline: are we currently being displayed inline?
     * @type inline: C{Boolean}
     *
     * @param allPeople: C{Array} of 2-C{Arrays} of [name, email address] for
     * each person in the address book.  Used for autocomplete
     *
     * @ivar completionDeferred: L{Divmod.Defer.Deferred} firing when we are
     * doing working (i.e. when L{cancel} has been called)
     */
    function __init__(self, node, inline, allPeople) {
        Quotient.Compose._Controller.upcall(self, "__init__", node);

        if(inline) {
            self.firstNodeByAttribute("class", "cancel-link").style.display = "";
            self.firstNodeByAttribute("class", "compose-table").style.width = "100%";
            self.node.style.borderTop = "";
        }

        self.inline = inline;

        self.toAutoCompleteController = Mantissa.AutoComplete.Controller(
            Quotient.Compose.EmailAddressAutoCompleteModel(allPeople),
            Quotient.Compose.EmailAddressAutoCompleteView(
                self.firstNodeByAttribute("name", "toAddresses"),
                self.firstNodeByAttribute("class", "address-completions")));

        self.ccAutoCompleteController = Mantissa.AutoComplete.Controller(
            Quotient.Compose.EmailAddressAutoCompleteModel(allPeople),
            Quotient.Compose.EmailAddressAutoCompleteView(
                self.firstNodeByAttribute("name", "cc"),
                self.firstNodeByAttribute("class", "address-completions")));

        self.completionDeferred = Divmod.Defer.Deferred();
    },

    /**
     * Called when the message-sending operating has been cancelled, or when a
     * message has been sent.
     *
     * Remove our node from its parent, and callback
     * C{self.completionDeferred}
     */
    function cancel(self) {
        self.node.parentNode.removeChild(self.node);
        self.completionDeferred.callback(null);
    });

Quotient.Compose.Controller = Quotient.Compose._Controller.subclass('Quotient.Compose.Controller');
Quotient.Compose.Controller.methods(
    function __init__(self, node, inline, allPeople) {
        Quotient.Compose.Controller.upcall(self, "__init__", node, inline, allPeople);

        var cc = self.firstNodeByAttribute("name", "cc"),
            bcc = self.firstNodeByAttribute("name", "bcc");
        if(0 < cc.value.length || 0 < bcc.value.length) {
            self.toggleMoreOptions();
        }

        self.fileList = self.firstNodeByAttribute("class", "file-list");
        if(0 < self.fileList.getElementsByTagName("li").length) {
            self.toggleFilesForm();
        }

        var mbody = self.firstNodeByAttribute("class", "compose-message-body");
        /* use a separate js class and/or template if this grows any more */

        self.draftNotification = self.nodeByAttribute("class", "draft-notification");

        self.attachDialog = self.nodeByAttribute("class", "attach-dialog");
        self.autoSaveInterval = 30;
        self.inboxURL = self.nodeByAttribute("class", "inbox-link").href;

        self.startSavingDrafts();

        self.makeFileInputs();
        self._storeButtons();
    },

    /**
     * Stop the draft-saving loop when the widget is removed from the page.
     */
    function detach(self) {
        self.stopSavingDrafts();
        return Quotient.Compose.Controller.upcall(self, 'detach');
    },

    /**
     * Find the container of the send & save buttons inside our node,
     * wrap each button inside in a L{Quotient.Common.ButtonToggler} and store
     * the array in C{self._buttonTogglers}
     */
    function _storeButtons(self) {
        var container = self.firstNodeByAttribute(
                            "class", "send-save-attach-buttons");
        var buttons = Nevow.Athena.NodesByAttribute(
                            container, "class", "button");
        self._buttonTogglers = [];
        for(var i = 0; i < buttons.length; i++) {
            self._buttonTogglers.push(Quotient.Common.ButtonToggler(buttons[i]));
        }
    },

    /**
     * Disable the send & save buttons until C{deferred} fires
     *
     * @type deferred: L{Divmod.Defer.Deferred}
     */
    function _disableButtonsUntilFires(self, deferred) {
        for(var i = 0; i < self._buttonTogglers.length; i++) {
            self._buttonTogglers[i].disableUntilFires(deferred);
        }
    },

    /**
     * Arrange for the state of the message being composed to be saved as a
     * draft every C{self.autoSaveInterval} seconds.
     */
    function startSavingDrafts(self) {
        self._savingDrafts = true;

        var saveDraftLoop = function saveDraftLoop() {
            self._draftCall = null;
            var saved = self.saveDraft();
            saved.addCallback(
                function(ignored) {
                    if (self._savingDrafts) {
                        self._draftCall = self.callLater(self.autoSaveInterval, saveDraftLoop);
                    }
                });
        };

        self._draftCall = self.callLater(self.autoSaveInterval, saveDraftLoop);
    },

    /**
     * Stop periodically saving drafts.
     */
    function stopSavingDrafts(self) {
        self._savingDrafts = false;
        if (self._draftCall != null) {
            self._draftCall.cancel();
            self._draftCall = null;
        }
    },

    function cancel(self) {
        Quotient.Compose.Controller.upcall(self, "cancel");
        self.stopSavingDrafts();
    },

    function toggleFilesForm(self) {
        if(!self.filesForm) {
            self.filesForm = self.firstNodeByAttribute("class", "files-form");
        }
        if(self.filesForm.style.display == "none") {
            self.filesForm.style.display = "";
        } else {
            self.filesForm.style.display = "none";
        }
    },

    /**
     * Flip the visibility of all nodes below this widget's node which have
     * the class name "more-options", and change the label inside the node
     * with class name "more-options-disclosure" accordingly.
     */
    function toggleMoreOptions(self) {
        if(!self.moreOptions) {
            self.moreOptions = self.nodesByAttribute("class", "more-options");
        }

        for(var i = 0; i < self.moreOptions.length; i++) {
            if(self.moreOptions[i].style.display == "none") {
                self.moreOptions[i].style.display = "";
            } else {
                self.moreOptions[i].style.display = "none";
            }
        }

        if(!self.moreOptionsDisclose) {
            self.moreOptionsDisclose = self.firstNodeByAttribute(
                                        "class", "more-options-disclose");
        }
        self._toggleDisclosureLabels(self.moreOptionsDisclose);
        return false;
    },

    /**
     * Switch around the visibility of the node with class name "closed-label"
     * and node with class name "open-label" inside the node C{node}
     *
     * @type node: node
     */
    function _toggleDisclosureLabels(self, node) {
        var closed = Nevow.Athena.FirstNodeByAttribute(
                        node, "class", "closed-label"),
            open = Nevow.Athena.FirstNodeByAttribute(
                    node, "class", "open-label");

        if(closed.style.display == "none") {
            closed.style.display = "";
            open.style.display = "none";
        } else {
            closed.style.display = "none";
            open.style.display= "";
        }
        return false;
    },

    function toggleAttachDialog(self) {
        if(self.attachDialog.style.display == "none") {
            self.attachDialog.style.display = "";

            var pageSize = Divmod.Runtime.theRuntime.getPageSize();
            var bg = MochiKit.DOM.DIV({"id": "attach-dialog-bg"});
            bg.style.height = pageSize.h + "px";
            bg.style.width = pageSize.w + "px";
            self.node.parentNode.appendChild(bg);

            if(self.attachDialog.style.left == "") {
                var elemSize = Divmod.Runtime.theRuntime.getElementSize(self.attachDialog);
                self.attachDialog.style.display = "none";
                self.attachDialog.style.left = (pageSize.w/2 - elemSize.w/2) + "px";
                self.attachDialog.style.top  = (pageSize.h/2 - elemSize.h/2) + "px"
                self.attachDialog.style.display = "";
            }
        } else {
            self.attachDialog.style.display = "none";
            self.node.parentNode.removeChild(document.getElementById("attach-dialog-bg"));
        }
    },

    /**
     * Send the current message state to the server to be saved as a draft.
     * Announce when this begins and ends graphically.
     */
    function saveDraft(self) {
        var showDialog = function(text, fade) {
            var elem = MochiKit.DOM.DIV({"class": "draft-dialog"}, text);
            MochiKit.DOM.replaceChildNodes(self.draftNotification, elem);
            if(fade) {
                new Fadomatic(elem, 2).fadeOut();
            }
        }
        showDialog("Saving draft...");
        var e = self.nodeByAttribute("name", "draft");
        e.checked = true;
        var result = self.submit().addCallback(
            function(shouldLoop) {
                var time = (new Date()).toTimeString();
                showDialog("Draft saved at " + time.substr(0, time.indexOf(' ')), true);
            });
        e.checked = false;
        return result;
    },

    function submit(self) {
        if (self._submitting) {
            throw new Error("Concurrent submission rejected.");
        }
        self._submitting = true;

        self.savingADraft = self.nodeByAttribute("name", "draft").checked;
        var D = Quotient.Compose.Controller.upcall(self, "submit");
        self._disableButtonsUntilFires(D);
        D.addCallback(
            function(passthrough) {
                self._submitting = false;
                return passthrough;
            });
        if (!self.savingADraft) {
            D.addCallback(function(ign) {
                    if (self.inline) {
                        self.cancel();
                    }
                    return false;
                });
        }
        return D;
    },

    function makeFileInputs(self) {
        var uploaded = self.nodeByAttribute("class", "uploaded-files");
        var lis = self.fileList.getElementsByTagName("li");
        var span;
        for(var i = 0; i < lis.length; i++) {
            span = lis[i].getElementsByTagName("span")[0];
            uploaded.appendChild(
                MochiKit.DOM.INPUT({"type": "text",
                                    "name": "files",
                                    "value": span.firstChild.nodeValue},
                                   lis[i].firstChild.nodeValue));
        }
    },

    function uploading(self) {
        self.nodeByAttribute("class", "upload-notification").style.visibility = "";
    },

    /**
     * Called after the iframe POST completes.  C{d} is a dictionary
     * obtained from the server, containing information about the file
     * we uploaded (currently a unique identifier and the filename)
     *
     * Using this information, we add a node representing the file to the
     * user-visible attachment list, and add the unique identifier to the
     * value of the hidden form field that indicates which files to attach
     * to the message (this gets modified if the attachment is removed by
     * the user before the message is sent, etc)
     */
    function gotFileData(self, d) {
        if(self.attachDialog.style.display != "none") {
            self.toggleAttachDialog();
        }

        self.nodeByAttribute("class", "upload-notification").style.visibility = "hidden";

        var lis = self.fileList.getElementsByTagName("li");

        if(0 == lis.length) {
            self.toggleFilesForm();
        }

        self.fileList.appendChild(MochiKit.DOM.LI(null, [d["name"],
            MochiKit.DOM.A({"style": "padding-left: 4px",
                            "href": "#",
                            "onclick": function() {
                                self.removeFile(this);
                                return false
                            }},
                            "(remove)")]));
        self.nodeByAttribute("class", "uploaded-files").appendChild(
            MochiKit.DOM.INPUT({"type": "text",
                                "name": "files",
                                "value": d["id"]}, d["name"]));
    },

    function removeFile(self, node) {
        var fname = node.previousSibling.nodeValue,
            lis = self.fileList.getElementsByTagName("li"),
            uploaded = self.firstNodeByAttribute('class', 'uploaded-files');

        self.fileList.removeChild(node.parentNode);
        if(0 == lis.length) {
            self.toggleFilesForm();
        }

        for(var i = 0; i < uploaded.childNodes.length; i++) {
            if(uploaded.childNodes[i].firstChild.nodeValue == fname) {
                uploaded.removeChild(uploaded.childNodes[i]);
                break;
            }
        }
    },

    /**
     * Expand compose widget to take up all the space inside C{node}.
     * Do this by making the message body textarea taller
     */
    function fitInsideNode(self, node) {
        var e = self.nodeByAttribute("class", "compose-message-body");

        e.style.height = (Divmod.Runtime.theRuntime.getElementSize(node).h -
                          (Divmod.Runtime.theRuntime.findPosY(e) -
                           Divmod.Runtime.theRuntime.findPosY(self.node)) -
                          1)+ "px";
    },

    function setAttachment(self, input) {
        MochiKit.DOM.hideElement(input);
        MochiKit.DOM.appendChildNodes(input.parentNode,
            MochiKit.DOM.SPAN({"style":"font-weight: bold"}, input.value + " | "),
            MochiKit.DOM.A({"href":"#",
                "onclick":self._makeHandler("removeAttachment(this)")}, "remove"),
            MochiKit.DOM.BR(),
            MochiKit.DOM.A({"href":"#",
                "onclick":self._makeHandler("addAttachment(this)")}, "Attach another file"));
    },

    function _makeHandler(self, f) {
        return "Quotient.Compose.Controller.get(this)." + f + "; return false";
    },

    function removeAttachment(self, link) {
        var parent = link.parentNode;
        parent.removeChild(link.previousSibling);
        parent.removeChild(link.nextSibling);
        parent.removeChild(link);
    },

    function addAttachment(self, link) {
        var parent = link.parentNode;
        parent.removeChild(link);
        parent.appendChild(MochiKit.DOM.INPUT(
            {"type": "file",
             "style": "display: block",
             "onchange": self._makeHandler("setAttachment(this)")}));
    },

    function showProgressMessage(self) {
        if(!self.savingADraft) {
            return Quotient.Compose.Controller.upcall(self, "showProgressMessage");
        }
    },

    function submitSuccess(self, result) {
        if(!self.savingADraft) {
            return Quotient.Compose.Controller.upcall(self, "submitSuccess", result);
        }
    });

/**
 * Class for controlling the redirection of emails
 *
 * XXX: Interfaces, or something.  We need to act sort of like an
 * L{Quotient.Compose.Controller} some of the time, because
 * L{Quotient.Mailbox.Controller} thinks we are one.
 */
Quotient.Compose.RedirectingController = Quotient.Compose._Controller.subclass('Quotient.Compose.RedirectingController');
Quotient.Compose.RedirectingController.methods(
    /**
     * @param allPeople: an array of 2-arrays of [name, email address] for
     * each person in the addressbook.  This is used for autocomplete
     */
    function __init__(self, node, allPeople) {
        Quotient.Compose.RedirectingController.upcall(
            self, "__init__", node, true, allPeople);
        self.firstNodeByAttribute(
            "class", "draft-button-container").style.display = "none";
    },

    /**
     * Unlike L{Quotient.Compose.Controller}, we don't need to do any special
     * work to fit inside our parent node.
     */
    function fitInsideNode(self) {
    },

    /**
     * Override default implementation to reject concurrent submissions, and
     * to call C{cancel} when we're done
     */
    function submit(self) {
        if(self._submitting) {
            throw new Error("Concurrent submission rejected.");
        }
        self._submitting = true;

        var D = Quotient.Compose.RedirectingController.upcall(self, "submit");
        D.addCallback(
            function(passthrough) {
                self._submitting = false;
                self.cancel();
                return passthrough;
            });
        return D;
    });
