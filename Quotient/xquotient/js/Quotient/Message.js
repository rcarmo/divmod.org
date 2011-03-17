
// import MochiKit.DOM

// import Nevow.Athena

Quotient.Message.ActionsModel = Divmod.Class.subclass('Quotient.Message.ActionsModel');
/**
 * Model class for message actions.  Maintains a list of all actions, and
 * dispatches action notifications to the listener.
 *
 * @param actions: sequence of string action names.
 * @type actions: C{Array}
 */
Quotient.Message.ActionsModel.methods(
    /**
     * @param actions: sequence of string action names.
     * @type actions: C{Array}
     */
    function __init__(self, actions) {
        self.actions = actions;
        self._enabledActions = {};
        self._actionListener = null;
    },

    /**
     * Figure out if the action called C{name} is enabled
     *
     * @param name: action name
     * @type name: C{String}
     *
     * @rtype: boolean
     */
    function isActionEnabled(self, name) {
        return (name in self._enabledActions);
    },

    /**
     * Disable the action called C{name}
     *
     * @param name: action name
     * @type name: C{String}
     *
     * @rtype: C{undefined}
     */
    function disableAction(self, name) {
        delete self._enabledActions[name];
    },

    /**
     * Enable the action called C{name}
     *
     * @param name: action name
     * @type name: C{String}
     *
     * @rtype: C{undefined}
     */
    function enableAction(self, name) {
        self._enabledActions[name] = 1;
    },

    /**
     * Enable only the actions listed in C{actions}
     *
     * @param actions: the actions to enable
     * @type actions: C{Array}
     *
     * @rtype: undefined
     */
    function enableOnlyActions(self, actions) {
        for(var action in self._enabledActions) {
            self.disableAction(action);
        }
        for(var i = 0; i < actions.length; i++) {
            self.enableAction(actions[i]);
        }
    },

    /**
     * Find out which actions are enabled
     *
     * @return: sequence of string action names, one name for each enabled
     * action
     * @rtype: C{Array}
     */
    function getEnabledActions(self) {
        return Divmod.dir(self._enabledActions);
    },

    /**
     * Set the object which will be notified about actions as they happen.
     *
     * @param obj: An object with a method (prefixed by 'messageAction_') for
     * each message action (e.g. 'messageAction_archive', etc)
     * @return: undefined
     */
    function setActionListener(self, obj) {
        self._actionListener = obj;
    },

    /**
     * Tell our action listener that an action needs to happen, by calling with
     * the supplied arguments the method on the listener that corresponds to
     * the action C{name}.  To handle the action, a method on the current
     * action listener (as set by C{setActionListener} will be called.  The
     * method called is C{messageAction_<action name>}.
     *
     * @param name: the name of the action
     * @type name: C{String}
     *
     * @param args: (optional) arguments to pass to the action method
     * @type args: C{Array}
     *
     * @return: the return value of the action method on the listener
     */
    function dispatchAction(self, name, args/*=[]*/) {
        if(args == undefined) {
            args = [];
        }
        if(self._actionListener == null) {
            throw new Error(
                'action ' + name + ' needs to happen, ' +
                'but there is no listener');
        }
        var meth = self._actionListener['messageAction_' + name];
        if(meth == undefined) {
            throw new Error(
                self._actionListener + ' has no method for action ' + name);
        }
        return meth.apply(self._actionListener, args);
    });

Quotient.Message.ActionsView = Divmod.Class.subclass('Quotient.Message.ActionsView');
/**
 * Class responsible for manipulating message actions DOM
 *
 * @ivar model: the model
 * @type model: L{Quotient.Message.ActionsModel}
 *
 * @ivar node: the top-most node of the actions DOM
 * @type node: node
 */
Quotient.Message.ActionsView.methods(
    /**
    * @param model: the model
    * @type model: L{Quotient.Message.ActionsModel}
    *
    * @param node: the top-most node of the actions DOM
    * @type node: node
    */
    function __init__(self, model, node) {
        self.model = model;
        self.node = node;
        self._buttonNodes = self._getButtonNodes();

        self.deferForm = Nevow.Athena.NodeByAttribute(
            node, "class", "defer-form");
        self.deferSelect = Nevow.Athena.NodeByAttribute(
            node, "class", "defer");
    },

    /**
     * Fetch the node for each button that the model knows about.
     *
     * Buttons are retrieved from the document based on class attributes.  For
     * each action, a node which a class of C{<action name>-button} should
     * exist.  For example, for an action named C{archive}, a node with a class
     * of C{archive-button} should exist.
     *
     * @rtype: object mapping button names to button nodes
     */
    function _getButtonNodes(self) {
        var nodes = {};
        for(var i = 0; i < self.model.actions.length; i++) {
            nodes[self.model.actions[i]] = Nevow.Athena.FirstNodeByAttribute(
                self.node, 'class', self.model.actions[i] + '-button');
        }
        return nodes;
    },

    /**
     * Get the button node for the action called C{name}
     *
     * @param name: action name
     * @type name: C{String}
     *
     * @return: button node
     * @rtype: node
     */
    function getButtonNode(self, name) {
        return self._buttonNodes[name];
    },

    /**
     * Figure out if the button for the action called C{name} is visible
     *
     * @param name: action name
     * @type name: C{String}
     *
     * @rtype: boolean
     */
    function isButtonVisible(self, name) {
        return self._buttonNodes[name].style.display == "";
    },

    /**
     * Hide the button for the action with name C{name}
     *
     * @param name: action name
     * @type name: C{String}
     *
     * @rtype: undefined
     */
    function _hideButton(self, name) {
        self._buttonNodes[name].style.display = "none";
    },

    /**
     * Show the button for the action with name C{name}
     *
     * @param name: action name
     * @type name: C{String}
     *
     * @rtype: undefined
     */
    function _showButton(self, name) {
        self._buttonNodes[name].style.display = "";
    },

    /**
     * Show only the buttons for the actions listed in C{actions}
     *
     * @param actions: the actions to show
     * @type actions: C{Array}
     * @rtype: undefined
     */
    function showOnlyButtons(self, actions) {
        for(var i = 0; i < self.model.actions.length; i++) {
            self._hideButton(self.model.actions[i]);
        }
        for(i = 0; i < actions.length; i++) {
            self._showButton(actions[i]);
        }
    },

    /**
     * Disable all action buttons until C{deferred} fires
     *
     * @type deferred: L{Divmod.Defer.Deferred}
     * @return: C{deferred}
     */
    function disableAllUntilFires(self, deferred) {
        for(var i = 0; i < self.model.actions.length; i++) {
            var button = self._buttonNodes[self.model.actions[i]],
                inner = Nevow.Athena.NodesByAttribute(
                    button, 'class', 'button');
            if(inner.length == 1) {
                Quotient.Common.ButtonToggler(inner[0]).disableUntilFires(
                    deferred);
            }
        }
    },

    /**
     * Find out the name of the selected option in C{selectNode}
     *
     * @param selectNode: the select node
     * @type selectNode: <select> node
     *
     * @return: the selected option name
     * @rtype: C{String} or C{null}
     */
    function _selectedOptionName(self, selectNode) {
        var opts = selectNode.getElementsByTagName("option"),
            opt = opts[selectNode.selectedIndex];
        if(opt.value == "") {
            return null;
        }
        return opt.value;
    },

    /**
     * Dispatch an action notification, extracting the action name from the
     * value of the currently selected <option> of the <select> node
     * C{selectNode} and returning the result of the selected method.  The
     * first option in the <select> is selected after the method returns.
     *
     * @type selectNode: a <select> node
     * @return: the return value of the action method, or null if the
     * currently selected <option> doesn't have a "value" attribute
     *
     */
    function dispatchActionFromSelect(self, selectNode) {
        var action = self._selectedOptionName(selectNode);
        if(action == null) {
            return null;
        }
        try {
            var result = self.model.dispatchAction(action);
        } catch(e) {
            selectNode.selectedIndex = 0;
            throw e;
        }
        selectNode.selectedIndex = 0;
        if(result instanceof Divmod.Defer.Deferred) {
            return self.disableAllUntilFires(result);
        }
        return result;
    },

    /**
     * Show the form which is used to select the deferral period
     *
     * @return: C{undefined}
     */
    function showDeferForm(self) {
        return self.deferForm.style.display = "";
    },

    /**
     * Hide the form which is used to select the deferral period
     *
     * @return: C{undefined}
     */
    function hideDeferForm(self) {
        self.deferForm.style.display = "none";
    },

    /**
     * Return an object with three properties giving the current state of the
     * defer period form.
     */
    function _getDeferralPeriod(self) {
        var form = self.deferForm;
        return {'days': parseInt(form.days.value),
                'hours': parseInt(form.hours.value),
                'minutes': parseInt(form.minutes.value)};
    },

    function _deferralStringToPeriod(self, value) {
        if (value == "other...") {
            self.showDeferForm();
            return null;
        }
        if (value == "Defer") {
            return null;
        }
        var args;
        if (value == "1 day") {
            return {"days": 1,
                    "hours": 0,
                    "minutes": 0};
        } else if (value == "1 hour") {
            return {"days": 0,
                    "hours": 1,
                    "minutes": 0};
        } else if (value == "12 hours") {
            return {"days": 0,
                    "hours": 12,
                    "minutes": 0};
        } else if (value == "1 week") {
            return {"days": 7,
                    "hours": 0,
                    "minutes": 0};
        } else {
            throw new Error("Invalid Deferral state:" + value);
        }
    },

    /**
     * Return an object describing the deferral period represented by the given
     * node, or null if it indicates no deferral should be performed or
     * something else if we should show the defer form.
     */
    function _getDeferralSelection(self, node) {
        var options = self.deferSelect.getElementsByTagName("option");
        var value = options[self.deferSelect.selectedIndex].firstChild.nodeValue;
        return self._deferralStringToPeriod(value);
    },

    /**
     * Dispatch a defer action based on the period entered in the defer form
     *
     * @rtype: C{Divmod.Defer.Deferred}
     */
    function formDefer(self) {
        var period = self._getDeferralPeriod();
        self.hideDeferForm();
        return self.model.dispatchAction('defer', [period]);
    },

    /**
     * Dispatch a defer action based on the selected period in the defer
     * <select> node
     *
     * @param selectNnode: <select> node
     * @type selectNode: node
     *
     * @rtype: C{Divmod.Defer.Deferred}
     */
    function selectDefer(self, selectNode) {
        try {
            var period = self._getDeferralSelection();
        } catch(err) {
            selectNode.selectedIndex = 0;
            throw err;
        }
        selectNode.selectedIndex = 0;
        if (period === null) {
            return;
        }
        return self.model.dispatchAction('defer', [period]);
    });

Quotient.Message.ActionsController = Nevow.Athena.Widget.subclass('Quotient.Message.ActionsController');
/**
 * Widget which forwards message actions events to the model or the view
 *
 * @ivar model: the actions model
 * @type model L{Quotient.Message.ActionsModel}
 *
 * @ivar view: the actions view
 * @type view: L{Quotient.Message.ActionsView}
 */
Quotient.Message.ActionsController.methods(
    /**
     * @param actions: sequence of string action names.
     * @type actions: C{Array}
     */
    function __init__(self, node, actions) {
        Quotient.Message.ActionsController.upcall(self, '__init__', node);
        self.model = Quotient.Message.ActionsModel(actions);
        self.view = Quotient.Message.ActionsView(self.model, node);
        self._setUpHandlers();
    },

    /**
     * Set the object which will be notified about actions as they happen.
     *
     * @param obj: An object with a method (prefixed by 'messageAction_') for
     * each message action (e.g. 'messageAction_archive', etc)
     * @return: undefined
     */
    function setActionListener(self, obj) {
        return self.model.setActionListener(obj);
    },

    /**
     * Override default implementation to set ourself as the actions
     * controller of our parent widget as soon as possible
     */
    function setWidgetParent(self, widgetParent) {
        Quotient.Message.ActionsController.upcall(
            self, 'setWidgetParent', widgetParent);
        if(widgetParent.setActionsController != undefined) {
            widgetParent.setActionsController(self);
        }
    },

    /**
     * Set up a DOM event handler for each action the model knows about.
     *
     * This creates a number of methods with the C{dom_} prefix in order to
     * handle actions from the user-interface.  One such method is created for
     * each action which C{self.model} knows about.
     */
    function _setUpHandlers(self) {
        function makeHandler(actionName) {
            return function() {
                var result = self.model.dispatchAction(actionName);
                if(result instanceof Divmod.Defer.Deferred) {
                    self.view.disableAllUntilFires(result);
                }
                return false;
            }
        }
        for(var i = 0; i < self.model.actions.length; i++) {
            self['dom_' + self.model.actions[i]] = makeHandler(
                self.model.actions[i]);
        }
    },

    /**
     * Enable the actions listed in C{actions}, and show their buttons
     *
     * @param actions: the actions to show
     * @type actions: C{Array}
     * @rtype: undefined
     */
    function enableOnlyActions(self, actions) {
        self.model.enableOnlyActions(actions);
        self.view.showOnlyButtons(actions);
    },

    /**
     * Dispatch an action notification, extracting the action name from the
     * value of the currently selected <option> of the <select> node
     * C{selectNode} and returning the result of the selected method.  The
     * first option in the <select> is selected after the method returns.
     *
     * @type selectNode: a <select> node
     * @return: C{false}
     *
     */
    function dom_dispatchActionFromSelect(self, selectNode) {
        self.view.dispatchActionFromSelect(selectNode);
        return false;
    },

    /**
     * Hide the form which is used to select the deferral period
     *
     * @return: C{false}
     */
    function dom_hideDeferForm(self) {
        self.view.hideDeferForm();
        return false;
    },

    /* special-case the two defer actions, because they require additional
     * pre-processing before action dispatch as the UI for defer is more
     * complex than the other actions */

    /**
     * Dispatch a defer action based on the selected period in the defer
     * <select> node
     *
     * @param selectNode: <select> node
     * @type selectNode: node
     *
     * @return: C{false}
     */
    function dom_selectDefer(self, selectNode) {
        self.view.selectDefer(selectNode);
        return false;
    },

    /**
     * Dispatch a defer action based on the period entered in the defer form
     *
     * @return: C{false}
     */
    function dom_formDefer(self) {
        self.view.formDefer();
        return false;
    });

Quotient.Message.MessageDetail = Nevow.Athena.Widget.subclass("Quotient.Message.MessageDetail");
Quotient.Message.MessageDetail.methods(
    function __init__(self, node, tags, showMoreDetail, enabledActions) {
        Quotient.Message.MessageDetail.upcall(self, "__init__", node);

        var tagsContainer = self.firstNodeByAttribute(
            "class", "tags-container");
        self.tagsDisplayContainer = Nevow.Athena.FirstNodeByAttribute(
            tagsContainer, "class", "tags-display-container");
        self.tagsDisplay = self.tagsDisplayContainer.firstChild;
        self.editTagsContainer = Nevow.Athena.FirstNodeByAttribute(
            tagsContainer, "class", "edit-tags-container");


        if(showMoreDetail) {
            self.toggleMoreDetail();
        }

        self.enabledActions = enabledActions;
        self.tags = tags;
    },

    /**
     * Register the actions controller for this widget.
     *
     * @param controller: actions controller
     * @type controller: L{Quotient.Message.ActionsController}
     */
    function setActionsController(self, controller) {
        self.actions = controller;
        self.actions.setActionListener(self);
        self.actions.enableOnlyActions(self.enabledActions);
    },

    /**
     * Find the L{Quotient.Message.ActionsController} widget below our node,
     * if one exists.
     *
     * @rtype: L{Quotient.Message.ActionsController} or C{null}
     */
    function _getActionsController(self) {
        try {
            var actions = self.firstNodeByAttribute(
                "athena:class",
                "Quotient.Message.ActionsController");
        } catch(e) {
            return null;
        }
        return Quotient.Message.ActionsController.get(actions);
    },

    function _getMoreDetailNode(self) {
        if(!self.moreDetailNode) {
            self.moreDetailNode = self.firstNodeByAttribute("class", "detail-toggle");
        }
        return self.moreDetailNode;
    },

    /**
     * Show the body of our message
     */
    function showMessageBody(self) {
        var mbody = self.firstNodeByAttribute("class", "message-body");
        mbody.style.display = "";
    },

    /**
     * Toggle the visibility of the "more detail" panel, which contains
     * some extra headers, or more precise values for headers that are
     * summarized or approximated elsewhere.
     *
     * @param node: the toggle link node (if undefined, will locate in DOM)
     * @return: undefined
     */
    function toggleMoreDetail(self, node) {
        if(node == undefined) {
            node = self._getMoreDetailNode();
        }

        node.blur();

        if(node.firstChild.nodeValue == "More Detail") {
            node.firstChild.nodeValue = "Less Detail";
        } else {
            node.firstChild.nodeValue = "More Detail";
        }

        if(!self.headerTable) {
            self.headerTable = self.firstNodeByAttribute("class", "msg-header-table");
        }

        var visible;
        var rows = self.headerTable.getElementsByTagName("tr");
        for(var i = 0; i < rows.length; i++) {
            if(rows[i].className == "detailed-row") {
                if(rows[i].style.display == "none") {
                    rows[i].style.display = "";
                } else {
                    rows[i].style.display = "none";
                }
                if(visible == undefined) {
                    visible = rows[i].style.display != "none";
                }
            }
        }
        return self.callRemote("persistMoreDetailSetting", visible);
    },

    /**
     * Show the original, unscrubbed HTML for this message
     */
    function showOriginalHTML(self) {
        var mbody = self.firstNodeByAttribute("class", "message-body"),
            iframe = mbody.getElementsByTagName("iframe")[0];

        if(iframe.src.match(/\?/)) {
            iframe.src += "&noscrub=1";
        } else {
            iframe.src += "?noscrub=1";
        }

        var sdialog = self.firstNodeByAttribute("class", "scrubbed-dialog");
        sdialog.parentNode.removeChild(sdialog);
    },

    /**
     * Make the necessary DOM changes to allow editing of the tags of this
     * message.  This involves showing, populating and focusing the tag text
     * entry widget
     */
    function editTags(self) {
        var input = self.editTagsContainer.tags;
        if(self.tagsDisplay.firstChild.nodeValue != "No Tags") {
            input.value = self.tags.join(', ');
        }
        self.tagsDisplayContainer.style.display = "none";
        self.editTagsContainer.style.display = "";

        /* IE throws an exception if an invisible element receives focus */
        input.focus();
    },

    function hideTagEditor(self) {
        self.editTagsContainer.style.display = "none";
        self.tagsDisplayContainer.style.display = "";
    },

    /**
     * Event-handler for tag saving.
     *
     * @return: C{false}
     */
    function dom_saveTags(self) {
        var tags = self.editTagsContainer.tags.value.split(/,\s*/),
            nonEmptyTags = [];
        for(var i = 0; i < tags.length; i++) {
            if(0 < tags[i].length) {
                nonEmptyTags.push(tags[i]);
            }
        }
        self.saveTags(nonEmptyTags).addCallback(
            function(ignored) {
                self._updateTagList();
                self.hideTagEditor();
            });
        return false;
    },

    /**
     * Tell our parent widget to select the tag C{tag}
     *
     * @param tag: the name of the tag to select
     * @type tag: C{String}
     */
    function chooseTag(self, tag) {
        if(self.widgetParent != undefined
            && self.widgetParent.chooseTag != undefined) {
            return self.widgetParent.chooseTag(tag);
        }
    },

    /**
     * Event-handler for tag choosing
     *
     * @param node: the tag link node
     * @type node: node
     *
     * @return: C{false}
     */
    function dom_chooseTag(self, node) {
        self.chooseTag(node.firstChild.nodeValue);
        return false;
    },

    /**
     * Update the tag list of our message
     */
    function _updateTagList(self) {
        while(self.tagsDisplay.firstChild) {
            self.tagsDisplay.removeChild(
                self.tagsDisplay.firstChild);
        }
        function makeOnclick(node) {
            return function() {
                return self.dom_chooseTag(node);
            }
        }
        for(var i = 0; i < self.tags.length; i++) {
            /* XXX template */
            var node = document.createElement("a");
            node.href = "#";
            node.className = "tag";
            node.onclick = makeOnclick(node);
            node.appendChild(document.createTextNode(self.tags[i]));
            self.tagsDisplay.appendChild(node);
        }
        if(i == 0) {
            self.tagsDisplay.appendChild(
                document.createTextNode("No Tags"));
        }
    },

    /**
     * Modify the tags for this message.
     *
     * @param tags: all of the tags for this message
     * @type tags: C{Array} of C{String}
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function saveTags(self, tags) {
        tags = Quotient.Common.Util.uniq(tags);
        var tagsToDelete = Quotient.Common.Util.difference(self.tags, tags),
            tagsToAdd = Quotient.Common.Util.difference(tags, self.tags),
            D;

        if(0 < tagsToAdd.length || 0 < tagsToDelete.length) {
            D = self.callRemote("modifyTags", tagsToAdd, tagsToDelete);
            D.addCallback(
                function(tags) {
                    self.tags = tags;
                });
        } else {
            D = Divmod.Defer.succeed(null);
        }
        D.addCallback(
            function(ignored) {
                if(0 < tagsToAdd.length
                    && self.widgetParent != undefined
                    && self.widgetParent.addTagsToViewSelector != undefined) {
                    self.widgetParent.addTagsToViewSelector(tagsToAdd);
                }
            });
        return D;
    },

    /**
     * Replace this message detail with a compose widget.  This message will
     * be re-displayed after the compose widget has been dismissed.
     *
     * @param composeInfo: widget info for a L{Quotient.Compose.Controller}
     *
     * @param reloadMessage: if true, the currently selected message will be
     * reloaded and displayed after the compose widget has been dismissed
     *
     * @return: deferred firing after this message has been reloaded
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function _splatComposeWidget(self, composeInfo, reloadMessage/*=true*/) {
        if(reloadMessage == undefined) {
            reloadMessage = true;
        }
        var result = self.addChildWidgetFromWidgetInfo(composeInfo);
        result.addCallback(
            function(composer) {
                if (self.composer) {
                    self.composer.node.parentNode.removeChild(self.composer.node);
                    self.composer.detach();
                }
                self.composer = composer;
                var parentNode = self.node.parentNode;
                parentNode.insertBefore(composer.node, self.node);
                composer.fitInsideNode(parentNode);
                self.node.style.display = "none";
                return composer;
            });
        if(reloadMessage) {
            result.addCallback(
                function(composer) {
                    return composer.completionDeferred;
                });
            result.addCallback(
                function(ignore) {
                    self.composer = null;
                    self.node.style.display = "";
                });
        }
        return result;
    },

    /**
     * Call the remote method C{remoteMethodName}, which is expected to return
     * a compose widget, and splat it on top of the DOM for this widget (see
     * L{_splatComposeWidget}
     *
     * @param remoteMethodName: name of the composer-returning remote method
     * @type remoteMethodName: C{String}
     *
     * @param reloadMessage: if true, the currently selected message will be
     * reloaded and displayed after the compose widget has been dismissed
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function _doComposeAction(self, remoteMethodName, reloadMessage) {
        var result = self.callRemote(remoteMethodName);
        result.addCallback(
            function(composeInfo) {
                return self._splatComposeWidget(composeInfo, reloadMessage);
            });
        return result;
    },

    /**
     * 'Printable' message action.  Open a window that contains a printable
     * version of the current message
     */
    function messageAction_printable(self) {
        window.open(
            self.firstNodeByAttribute("class", "printable-link").href);
    },

    /**
     * 'Message Source' message action.  Show the source of our message
     *
     * @return: deferred firing with L{Quotient.Message.Source}
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_messageSource(self) {
        var d = self.callRemote("getMessageSource");
        d.addCallback(
            function(widget_info) {
                return self.addChildWidgetFromWidgetInfo(widget_info);
            });
        d.addCallback(
            function(widget) {
                var mbody = self.firstNodeByAttribute("class", "message-body");
                mbody.parentNode.insertBefore(widget.node, mbody);
                mbody.style.display = "none";
                return widget;
            });
        return d;
    },

    /**
     * 'Archive' message action
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_archive(self) {
        return self.callRemote('archive');
    },

    /**
     * 'Unarchive' message action
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_unarchive(self) {
        return self.callRemote('unarchive');
    },

    /**
     * 'Delete' message action
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_delete(self) {
        return self.callRemote('delete');
    },

    /**
     * 'Undelete' message action
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_undelete(self) {
        return self.callRemote('undelete');
    },

    /**
     * 'Defer' message action
     *
     * Defer the currently selected rows and update the display to indicate
     * that this has been done.
     *
     * @param period: The period of time to defer the selected rows.
     * @return: A L{Divmod.Base.Deferred} that is passed through from
     * L{touch}.
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_defer(self, period) {
        return self.callRemote(
            'defer', period.days, period.hours, period.minutes);
    },

    /**
     * Retrieve and show a widget to assist in composing a reply to this
     * message
     *
     * @param reloadMessage: if true, the currently selected message will be
     * reloaded and displayed after the compose widget has been dismissed
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_reply(self, reloadMessage) {
        return self._doComposeAction('reply', reloadMessage);
    },

    /**
     * Retrieve and show a widget to assist in composing a forwarded version
     * of this message
     *
     * @param reloadMessage: if true, the currently selected message will be
     * reloaded and displayed after the compose widget has been dismissed
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_forward(self, reloadMessage) {
        return self._doComposeAction('forward', reloadMessage);
    },

    /**
     * Retrieve and show a widget to assist in composing a reply to everyone
     * involved in this message
     *
     * @param reloadMessage: if true, the currently selected message will be
     * reloaded and displayed after the compose widget has been dismissed
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_replyAll(self, reloadMessage) {
        return self._doComposeAction('replyAll', reloadMessage);
    },

    /**
     * Retrieve and show a widget to assist in composing a redirected version
     * of this message
     *
     * @param reloadMessage: if true, the currently selected message will be
     * reloaded and displayed after the compose widget has been dismissed
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function messageAction_redirect(self, reloadMessage) {
        return self._doComposeAction('redirect', reloadMessage);
    },

    /**
     * Open a compose window to use to edit the currently selected
     * draft message.
     */
    function messageAction_editDraft(self) {
        return self._doComposeAction("editDraft", false);
    });


/**
 * Message body control code which interacts with the DOM
 */
Quotient.Message.BodyView = Divmod.Class.subclass('Quotient.Message.BodyView');
Quotient.Message.BodyView.methods(
    function __init__(self, node) {
        self.node = node;
    },

    /**
     * Figure out the alternate MIME type linked to by node C{node}
     *
     * @param node: the alternate MIME type link
     * @type node: <a> node
     *
     * @return: the MIME type
     * @rtype: C{String}
     */
    function getMIMETypeFromNode(self, node) {
        return node.firstChild.nodeValue;
    },

    /**
     * Replace our node with another node
     *
     * @type node: node
     *
     * @rtype: C{undefined}
     */
    function replaceNode(self, node) {
        self.node.parentNode.insertBefore(node, self.node);
        self.node.parentNode.removeChild(self.node);
    });

/**
 * Message body control code which responds to events
 */
Quotient.Message.BodyController = Nevow.Athena.Widget.subclass('Quotient.Message.BodyController');
Quotient.Message.BodyController.methods(
    function __init__(self, node) {
        self.view = Quotient.Message.BodyView(node);
        Quotient.Message.BodyController.upcall(self, '__init__', node);
    },

    /**
     * Retrieve and display the component of this message with MIME type
     * C{type}
     *
     * @param type: MIME type
     * @type type: C{String}
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function chooseDisplayMIMEType(self, type) {
        var D = self.callRemote('getAlternatePartBody', type);

        D.addCallback(
            function(widget_info) {
                return self.addChildWidgetFromWidgetInfo(widget_info);
            });
        D.addCallback(
            function(widget) {
                self.view.replaceNode(widget.node);
                return widget;
            });
        return D;
    },

    /**
     * DOM event handler which wraps L{chooseDisplayMIMEType}
     */
    function dom_chooseDisplayMIMEType(self, node) {
        var type = self.view.getMIMETypeFromNode(node);
        self.chooseDisplayMIMEType(type);
        return false;
    });

Quotient.Message.Source = Nevow.Athena.Widget.subclass('Quotient.Message.Source');
/**
 * Responds to events originating from message source DOM.  Assumes a widget
 * parent with a L{showMessageBody} method
 */
Quotient.Message.Source.methods(
    /**
     * Called when the user decides they don't want to look at the message
     * source anymore.  Removes our node from the DOM, and calls
     * L{showMessageBody} on our widget parent
     */
    function cancel(self) {
        self.node.parentNode.removeChild(self.node);
        self.widgetParent.showMessageBody();
        return false;
    });
