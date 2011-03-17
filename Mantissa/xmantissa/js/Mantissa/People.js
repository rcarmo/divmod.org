// import Nevow.TagLibrary.TabbedPane
// import Mantissa.LiveForm
// import Mantissa.ScrollTable

Mantissa.People.OrganizerView = Divmod.Class.subclass(
    'Mantissa.People.OrganizerView');
/**
 * View abstraction for L{Mantissa.People.Organizer}.
 *
 * @ivar nodeById: Callable which takes a node ID and returns a node.
 * @type nodeById: C{Function}
 */
Mantissa.People.OrganizerView.methods(
    function __init__(self, nodeById) {
        self.nodeById = nodeById;
        self.selectedFilterNode = nodeById('default-filter');
    },

    /**
     * Set the "top" style property of the I{organizer} node, positioning it
     * within its parent.
     */
    function setOrganizerPosition(self) {
        var organizerNode = self.nodeById('organizer');
        var organizerTop = Divmod.Runtime.theRuntime.findPosY(
            organizerNode.parentNode);
        organizerNode.style.top = organizerTop + 'px';
    },

    /**
     * Display the node with the id I{filter-throbber}.
     */
    function showFilterThrobber(self) {
        self.nodeById('filter-throbber').style.display = '';
    },

    /**
     * Hide the node with the id I{filter-throbber}.
     */
    function hideFilterThrobber(self) {
        self.nodeById('filter-throbber').style.display = 'none';
    },

    /**
     * Apply the I{people-table-selected-filter} class to the given node, and
     * remove it from the previously selected filter node, if any.
     *
     * @type filterNode: DOM node.
     */
    function filterSelected(self, filterNode) {
        filterNode.setAttribute('class', 'people-table-selected-filter');
        if(self.selectedFilterNode !== null) {
            self.selectedFilterNode.setAttribute('class', 'people-table-filter');
        }
        self.selectedFilterNode = filterNode;
    },

    /**
     * Remove the existing detail node and insert the specified one in its
     * place.
     *
     * @type nodes: A DOM node.
     */
    function setDetailNode(self, node) {
        self.clearDetailNodes();
        self.nodeById('detail').appendChild(node);
    },

    /**
     * Show the node with the id I{person-widget-throbber}.
     */
    function showPersonWidgetThrobber(self) {
        self.nodeById('person-widget-throbber').style.display = '';
    },

    /**
     * Hide the node with the id I{person-widget-throbber}.
     */
    function hidePersonWidgetThrobber(self) {
        self.nodeById('person-widget-throbber').style.display = 'none';
    },

    /**
     * Move the scrollbar in the I{person-cell} node to the top.
     */
    function unscrollPersonCell(self) {
        self.nodeById('person-cell').scrollTop = 0;
    },

    /**
     * Remove any existing detail nodes.
     */
    function clearDetailNodes(self) {
        var detailNode = self.nodeById('detail');
        while(0 < detailNode.childNodes.length) {
            detailNode.removeChild(detailNode.childNodes[0]);
        }
    },

    /**
     * Show the edit link.
     */
    function showEditLink(self) {
        self.nodeById('edit-link').style.display = '';
    },

    /**
     * Hide the edit link.
     */
    function hideEditLink(self) {
        self.nodeById('edit-link').style.display = 'none';
    },

    /**
     * Show the delete link.
     */
    function showDeleteLink(self) {
        self.nodeById('delete-link').style.display = '';
    },

    /**
     * Hide the delete link.
     */
    function hideDeleteLink(self) {
        self.nodeById('delete-link').style.display = 'none';
    },

    /**
     * Show the "cancel form" link.
     */
    function showCancelFormLink(self) {
        self.nodeById('cancel-form-link').style.display = '';
    },

    /**
     * Hide the "cancel form" link.
     */
    function hideCancelFormLink(self) {
        self.nodeById('cancel-form-link').style.display = 'none';
    });


/**
 * Container for person interaction user interface elements.
 *
 * This also provides APIs for different parts of the UI to interact with each
 * other so they they don't directly depend on each other.
 *
 * @ivar existingDetailWidget: The current widget displayed in the detail area,
 *     or C{null} if there is none.
 *
 * @ivar storeOwnerPersonName: The name of the "store owner person" (this
 * person can't be deleted).
 * @type storeOwnerPersonName: C{String}
 *
 * @ivar initialPersonName: The name of the person to load at
 * initialization time.  Defaults to C{undefined}.
 * @type initialPersonName: C{String} or C{undefined}
 *
 * @ivar initialState: The name for the state the person-detail area of the
 * view should be in after initialization.  Acceptable values are:
 * C{undefined} (blank view) or C{"edit"} (load the edit form for
 * L{initialPersonName}).  Defaults to C{undefined}.
 * @type initialState: C{String} or C{undefined}
 *
 * @ivar currentlyViewingName: The name of the person currently being viewed.
 * @type currentlyViewingName: C{String} or C{null}
 *
 * @type view: L{Mantissa.People.OrganizerView}
 */
Mantissa.People.Organizer = Nevow.Athena.Widget.subclass(
    'Mantissa.People.Organizer');
Mantissa.People.Organizer.methods(
    function __init__(self, node, storeOwnerPersonName, initialPersonName, initialState) {
        Mantissa.People.Organizer.upcall(self, '__init__', node);
        self.existingDetailWidget = null;
        self.storeOwnerPersonName = storeOwnerPersonName;
        self.view = self._makeView();
        self.view.setOrganizerPosition();
        self.initialPersonName = initialPersonName;
        if(initialPersonName === undefined) {
            self.currentlyViewingName = null;
        } else {
            self.currentlyViewingName = initialPersonName;
        }
        if(initialState === 'edit') {
            self.displayEditPerson();
        }
    },

    /**
     * Construct a L{Mantissa.People.OrganizerView}.
     *
     * @rtype: L{Mantissa.People.OrganizerView}
     */
    function _makeView(self) {
        return Mantissa.People.OrganizerView(
            function nodeById(id) {
                return self.nodeById(id);
            });
    },

    /**
     * Called by our child L{Mantissa.People.PersonScroller} when it has
     * finished initializing.  We take this opportunity to call
     * L{selectInPersonList} with L{initialPersonName}, if it's not
     * C{undefined}.
     */
    function personScrollerInitialized(self) {
        if(self.initialPersonName !== undefined) {
            self.selectInPersonList(self.initialPersonName);
        }
    },

    /**
     * Detach the existing detail widget, if there is one, and replace the
     * existing detail nodes with the node for the given widget.
     */
    function setDetailWidget(self, widget) {
        self.view.setDetailNode(widget.node);
        if (self.existingDetailWidget !== null) {
            self.existingDetailWidget.detach();
        }
        self.existingDetailWidget = widget;
    },

    /**
     * Detach the current detail widget, if any.
     */
    function clearDetailWidget(self) {
        self.view.clearDetailNodes();
        if (self.existingDetailWidget !== null) {
            self.existingDetailWidget.detach();
            self.existingDetailWidget = null;
        }
    },

    /**
     * Get an add person widget from the server and put it in the detail area.
     */
    function displayAddPerson(self) {
        self.view.hideEditLink();
        self.view.hideDeleteLink();
        self.view.hideCancelFormLink();
        var result = self.callRemote('getAddPerson');
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                self.view.showCancelFormLink();
                widget.observeSubmission(
                    function(name) {
                        self._cbPersonAdded(name);
                    });
                self.setDetailWidget(widget);
            });
        return false;
    },

    /**
     * Get an import widget from the server and put it in the detail area.
     */
    function displayImportPeople(self) {
        self.view.hideEditLink();
        self.view.hideDeleteLink();
        self.view.hideCancelFormLink();
        var result = self.callRemote('getImportPeople');
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                self.view.showCancelFormLink();
                widget.organizer = self;
                self.setDetailWidget(widget);
            });
        return false;
    },

    /**
     * Called when a person has been modified, with their name.  Updates the
     * person list, and selects the person involved.
     */
    function _cbPersonModified(self, name) {
        self.displayPersonInfo(name);
        var result = self.refreshPersonList();
        result.addCallback(
            function(ignore) {
                self.selectInPersonList(name);
            });
        return result;
    },

    /**
     * Called when a person has been added.
     *
     * @type name: C{String}
     * @param name: The new person's name.
     */
    function _cbPersonAdded(self, name) {
        self.currentlyViewingName = name;
        self.displayEditPerson();
        var result = self.refreshPersonList();
        result.addCallback(
            function(ignore) {
                self.selectInPersonList(name);
            });
        return result;
    },

    /**
     * Get our child L{Mantissa.People.PersonScroller}.
     *
     * @rtype: L{Mantissa.People.PersonScroller}
     */
    function getPersonScroller(self) {
        return self.childWidgets[0];
    },

    /**
     * Call C{emptyAndRefill} on our child L{Mantissa.People.PersonScroller}.
     */
    function refreshPersonList(self) {
        return self.getPersonScroller().emptyAndRefill();
    },

    /**
     * Call C{selectNamedPerson} on our child
     * L{Mantissa.People.PersonScroller}.
     */
    function selectInPersonList(self, name) {
        return self.getPersonScroller().selectNamedPerson(name);
    },

    /**
     * Shows a form for editing the person with L{currentlyViewingName}.
     */
    function displayEditPerson(self) {
        var result = self.callRemote(
            'getEditPerson', self.currentlyViewingName);
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                self.view.hideEditLink();
                self.view.hideDeleteLink();
                self.view.showCancelFormLink();
                self.setDetailWidget(widget);
                widget.observeSubmission(
                    function(name) {
                        if(self.currentlyViewingName === self.storeOwnerPersonName) {
                            self.storeOwnerPersonNameChanged(name);
                        }
                        self._cbPersonModified(name);
                    });
            });
        return result;
    },

    /**
     * Update L{storeOwnerPersonName}, and notify our person scroller of the
     * change.
     *
     * @param name: The new name of the store-owner person.
     * @type name: C{String}
     */
    function storeOwnerPersonNameChanged(self, name) {
        self.storeOwnerPersonName = name;
        var personScroller = self.getPersonScroller();
        personScroller.storeOwnerPersonNameChanged(name);
    },

    /**
     * DOM event handler which calls L{displayEditPerson}.
     */
    function dom_displayEditPerson(self) {
        self.displayEditPerson();
        return false;
    },

    /**
     * Tell our L{Mantissa.People.PersonScroller} to filter on the named
     * filter, and adjust our view state accordingly.
     *
     * @type filterName: C{String}
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function filterByFilter(self, filterName) {
        self.view.showFilterThrobber();
        var result = self.getPersonScroller().filterByFilter(filterName);
        result.addCallback(
            function(passThrough) {
                self.view.clearDetailNodes();
                self.view.hideEditLink();
                self.view.hideDeleteLink();
                self.view.hideFilterThrobber();
                return passThrough;
            });
        return result;
    },

    /**
     * DOM event handler which calls L{filterByFilter}.
     */
    function dom_filterByFilter(self, node) {
        if(self.view.selectedFilterNode !== node) {
            self.filterByFilter(node.childNodes[0].nodeValue);
            self.view.filterSelected(node);
        }
        return false;
    },

    /**
     * Delete the person currently being viewed by calling the remote
     * C{deletePerson} method.
     */
    function deletePerson(self) {
        var result = self.callRemote(
            'deletePerson', self.currentlyViewingName);
        result.addCallback(
            function(passThrough) {
                self.view.clearDetailNodes();
                self.view.hideEditLink();
                self.view.hideDeleteLink();
                self.refreshPersonList();
                return passThrough;
            });
        return result;
    },

    /**
     * DOM event handler which calls L{deletePerson}.
     */
    function dom_deletePerson(self) {
        self.deletePerson();
        return false;
    },

    /**
     * "Cancel" the currently displayed form by loading the last-viewed
     * person.
     */
    function cancelForm(self) {
        self.view.clearDetailNodes();
        if(self.currentlyViewingName !== null) {
            self.displayPersonInfo(self.currentlyViewingName);
        }
        self.view.hideCancelFormLink();
    },

    /**
     * DOM event handler which calls L{cancelForm}.
     */
    function dom_cancelForm(self) {
        self.cancelForm();
        return false;
    },

    /**
     * Get a person info widget for the person with the specified name and put
     * it in the detail area.
     *
     * @type name: String
     * @param name: The I{name} of the L{xmantissa.people.Person} for
     *     which to load an info widget.
     */
    function displayPersonInfo(self, name) {
        self.view.hideEditLink();
        self.view.hideDeleteLink();
        self.view.hideCancelFormLink();
        self.view.clearDetailNodes();
        self.view.showPersonWidgetThrobber();
        self.currentlyViewingName = name;
        var result = self.callRemote('getPersonPluginWidget', name);
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                self.view.hidePersonWidgetThrobber();
                self.view.setDetailNode(widget.node);
                self.view.showEditLink();
                if(name !== self.storeOwnerPersonName) {
                    self.view.showDeleteLink();
                }
                self.view.unscrollPersonCell();
            });
    });


Mantissa.People.PersonScroller = Mantissa.ScrollTable.ScrollTable.subclass(
    'Mantissa.People.PersonScroller');
/**
 * A flexible-height scrolling widget which allows contact information for
 * people to be edited.
 *
 * @ivar storeOwnerPersonName: The name of the "store owner" person.
 * @type storeOwnerPersonName: C{String}
 *
 * @ivar _nameToRow: A mapping of person names to DOM row nodes.
 */
Mantissa.People.PersonScroller.methods(
    function __init__(self, node, currentSortColumn, columnList,
        defaultSortAscending, storeOwnerPersonName) {
        Mantissa.People.PersonScroller.upcall(
            self, '__init__', node, currentSortColumn, columnList,
            defaultSortAscending);
        self.storeOwnerPersonName = storeOwnerPersonName;
        self._nameToRow = {};
    },

    /**
     * Call the remote I{filterByFilter} method with C{filterName}.
     *
     * @type filterName: C{String}
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function filterByFilter(self, filterName) {
        var result = self.callRemote('filterByFilter', filterName);
        result.addCallback(
            function(ign) {
                return self.emptyAndRefill();
            });
        return result;
    },

    /**
     * Update L{storeOwnerPersonName}.
     *
     * @param name: The new name of the store-owner person.
     * @type name: C{String}
     */
    function storeOwnerPersonNameChanged(self, name) {
        self.storeOwnerPersonName = name;
    },

    /**
     * Extend the base implementation with parent-widget load notification.
     */
    function loaded(self) {
        var initDeferred = Mantissa.People.PersonScroller.upcall(
            self, 'loaded');
        initDeferred.addCallback(
            function(passThrough) {
                self.widgetParent.personScrollerInitialized();
                return passThrough;
            });
        return initDeferred;
    },

    /**
     * Override the base implementation to not show any feedback.
     */
    function startShowingFeedback(self) {
        return {stop: function() {}};
    },

    /**
     * Apply the I{person-list-selected-person-row} class to C{node}, and
     * remove it from the previously-selected row.
     */
    function _rowSelected(self, node) {
        if(self._selectedRow === node) {
            return;
        }
        node.setAttribute('class', 'person-list-selected-person-row');
        if(self._selectedRow !== undefined) {
            self._selectedRow.setAttribute('class', 'person-list-person-row');
        }
        self._selectedRow = node;
    },

    /**
     * Select the row of the person named C{name}.
     *
     * @param name: A person name.
     * @type name: C{String}
     */
    function selectNamedPerson(self, name) {
        self._rowSelected(self._nameToRow[name]);
    },

    /**
     * DOM event handler for when a cell is clicked.  Calls
     * L{Mantissa.People.Organizer.displayPersonInfo} on our parent organizer
     * with the name of the clicked person.
     *
     * @return: C{false}
     * @rtype: C{Boolean}
     */
    function dom_cellClicked(self, node) {
        self._rowSelected(node);
        self.widgetParent.displayPersonInfo(
            MochiKit.DOM.scrapeText(node));
        return false;
    },

    /**
     * Override the base implementation to make the whole row clickable.
     */
    function makeRowElement(self, rowOffset, rowData, cells) {
        var node = MochiKit.DOM.DIV(
            {"class": "person-list-person-row"},
            cells);
        self._nameToRow[rowData.name] = node;
        self.connectDOMEvent("onclick", "dom_cellClicked", node);
        return node;
    },

    /**
     * Wrap the DOM for the I{name} column, including a mugshot C{<img>}.
     *
     * @type rowData: C{Object}
     * @param rowData: Row data mapping.
     *
     * @type columnNode: DOM node
     *
     * @rtype: DOM node
     */
    function _wrapNameColumnDOM(self, rowData, columnNode) {
        var nameContainerNode = document.createElement('span');
        nameContainerNode.appendChild(columnNode);
        if(rowData.vip) {
            var imgNode = document.createElement('img');
            imgNode.setAttribute('src', '/static/mantissa-base/images/vip-flag.png');
            nameContainerNode.appendChild(imgNode);
        }
        if(rowData.name === self.storeOwnerPersonName) {
            var imgNode = document.createElement('img');
            imgNode.setAttribute('class', 'mantissa-me-icon');
            imgNode.setAttribute('src', '/static/mantissa-base/images/me-icon.png');
            nameContainerNode.appendChild(imgNode);
        }
        var wrapperNode = document.createElement('div');
        wrapperNode.setAttribute('class', 'people-table-name-cell');
        var mugshotNode = document.createElement('div');
        mugshotNode.setAttribute('class', 'people-table-mugshot');
        mugshotNode.style.backgroundImage = 'url(' + rowData.mugshotURL + ')';
        wrapperNode.appendChild(mugshotNode);
        wrapperNode.appendChild(nameContainerNode);
        var spacerNode = document.createElement('div');
        spacerNode.setAttribute('class', 'people-table-spacer');
        wrapperNode.appendChild(spacerNode);
        return wrapperNode;
    },

    /**
     * Override the base implementation to return an image node for the VIP
     * status cell, and a simpler, easier-to-style node for the person name
     * cell
     */
    function makeCellElement(self, colName, rowData) {
        if(colName === 'name') {
            var columnObject = self.columns[colName];
            var columnValue = columnObject.extractValue(rowData);
            var columnNode = columnObject.valueToDOM(columnValue, self);
            return self._wrapNameColumnDOM(rowData, columnNode);
        }
    });


Mantissa.People._SubmitNotificationForm = Mantissa.LiveForm.FormWidget.subclass(
    'Mantissa.People._SubmitNotificationForm');
/**
 * L{Mantissa.LiveForm.FormWidget} subclass which notifies registered
 * observers with the value of the form's I{nickname} input after a successful
 * submission.
 *
 * @ivar observers: An array of observer functions which have been registered.
 */
Mantissa.People._SubmitNotificationForm.methods(
    function __init__(self, node, formName) {
        Mantissa.People._SubmitNotificationForm.upcall(
            self, '__init__', node, formName);
        self.observers = [];
    },

    /**
     * Register a callable to be invoked with a nickname string after a
     * successful submission.
     *
     * @param observer: A one-argument callable.
     */
    function observeSubmission(self, observer) {
        self.observers.push(observer);
    },

    /**
     * Handle successful submission by invoking any registered observers.
     */
    function submitSuccess(self, result) {
        if(0 === self.observers.length) {
            return;
        }
        var nickname = self.gatherInputAccessors().nickname[0].get();
        for (var i = 0; i < self.observers.length; ++i) {
            self.observers[i](nickname);
        }
    });


/**
 * Specialized L{Mantissa.People._SubmitNotificationForm} which doesn't reset
 * its inputs to their default values after being submitted.
 */
Mantissa.People.EditPersonForm = Mantissa.People._SubmitNotificationForm.subclass(
    'Mantissa.People.EditPersonForm');
Mantissa.People.EditPersonForm.methods(
    /**
     * Override the parent behavior so that the newly entered values remain in
     * the form, since they are the values which are present on the server.
     */
    function reset(self) {
    });


/**
 * Trivial L{Mantissa.People._SubmitNotificationForm} subclass, used for
 * adding new people to the address book.
 */
Mantissa.People.AddPersonForm = Mantissa.People._SubmitNotificationForm.subclass(
    'Mantissa.People.AddPersonForm');


Mantissa.People._SubmitNotificationFormWrapper = Nevow.Athena.Widget.subclass(
    'Mantissa.People._SubmitNotificationFormWrapper');
/**
 * Trivial L{Nevow.Athena.Widget} subclass which forwards L{observeSubmission}
 * calls to its child form.
 */
Mantissa.People._SubmitNotificationFormWrapper.methods(
    /**
     * Notify our child widget.
     */
    function observeSubmission(self, observer) {
        self.childWidgets[0].observeSubmission(observer);
    });


/**
 * Overall representation of the interface for adding a new person.  Doesn't do
 * much except expose a method of the L{AddPersonForm} it contains to outside
 * widgets.
 */
Mantissa.People.AddPerson = Mantissa.People._SubmitNotificationFormWrapper.subclass(
    'Mantissa.People.AddPerson');
Mantissa.People.AddPerson.methods(
    /**
     * Focus the I{nickname} input.
     */
    function focusNicknameInput(self) {
        self.firstNodeByAttribute('name', 'nickname').focus();
    },

    /**
     * Implement this hook to focus the I{nickname} input.
     */
    function loaded(self) {
        /* .focus() is a no-op unless we wait, even though we can get a handle
         * on the node */
        self.callLater(
            0,
            function() {
                self.focusNicknameInput();
            });
    });


/**
 * Overall representation of the interface for editing an existing person.
 * Doesn't do much except expose a method of the L{EditPersonForm} it contains
 * to outside widgets.
 */
Mantissa.People.EditPerson = Mantissa.People._SubmitNotificationFormWrapper.subclass(
    'Mantissa.People.EditPerson');


/**
 * Client half of L{xmantissa.people.ImportPeopleWidget}.
 *
 * @ivar organizer: the L{Organizer} to refresh after importing, or C{null}
 */
Mantissa.People.ImportPeopleWidget = Nevow.Athena.Widget.subclass(
    'Mantissa.People.ImportPeopleWidget');
Mantissa.People.ImportPeopleWidget.methods(
    /**
     * Called on completion of an import.
     *
     * Displays how many people were imported, and refreshes the organizer if
     * needed.
     *
     * @param names: list of names of people imported
     */
    function imported(self, names) {
        if (0 < names.length) {
            self.resultMessage([
                names.length,
                (names.length == 1 ? 'person' : 'people'),
                'imported:',
                names.join(', ')
            ].join(' '));
            if (self.organizer) {
                return self.organizer.refreshPersonList();
            }
        } else {
            self.resultMessage('No people imported.');
        }
        return Divmod.Defer.succeed();
    },

    /**
     * Display the given message in this widget's C{import-result} node.
     */
    function resultMessage(self, message) {
        var node = self.nodeByAttribute('class', 'import-result');
        // XXX: there should be a helper for this
        while (0 < node.childNodes.length) {
            node.removeChild(node.childNodes[0]);
        }
        node.appendChild(document.createTextNode(message));

    });


/**
 * L{ImportPeopleWidget}'s form.
 */
Mantissa.People.ImportPeopleForm = Mantissa.LiveForm.FormWidget.subclass(
    'Mantissa.People.ImportPeopleForm');
Mantissa.People.ImportPeopleForm.methods(
    /**
     * Extend L{FormWidget} to notify our parent L{ImportPeopleWidget}.
     *
     * @see: L{ImportPeopleWidget.imported}
     */
    function submitSuccess(self, result) {
        Mantissa.People.ImportPeopleForm.upcall(self, 'submitSuccess', result);
        self.widgetParent.imported(result);
    });



Mantissa.People.PersonPluginView = Nevow.Athena.Widget.subclass(
    'Mantissa.People.PersonPluginView');
/**
 * Widget which controls selection of person plugin widgets.
 */
Mantissa.People.PersonPluginView.methods(
    /**
     * Get the appropriate plugin widget from the remote C{getPluginWidget}
     * method.
     *
     * @type pluginName: C{String}
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function getPluginWidget(self, pluginName) {
        var result = self.callRemote('getPluginWidget', pluginName);
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        return result;
    });

Mantissa.People.PluginTabbedPane = Nevow.TagLibrary.TabbedPane.TabbedPane.subclass(
    'Mantissa.People.PluginTabbedPane');
/**
 * L{Nevow.TagLibrary.TabbedPane.TabbedPane} subclass which fetches remote
 * plugin widgets on tab changes.
 */
Mantissa.People.PluginTabbedPane.methods(
    function __init__(self, node, selectedTabName) {
        Mantissa.People.PluginTabbedPane.upcall(
            self, '__init__', node, selectedTabName);
        self._fetchedWidgets = {};
        self._fetchedWidgets[selectedTabName] = 1;
    },

    /**
     * Implement this hook to call C{getPluginWidget} on our parent and
     * display the resulting widget's node.
     */
    function namedTabSelected(self, tabName) {
        if(self._fetchedWidgets[tabName] !== undefined) {
            return;
        }
        self._fetchedWidgets[tabName] = 1;
        var result = self.widgetParent.getPluginWidget(tabName);
        result.addCallback(
            function(widget) {
                self.view.replaceNamedPaneContent(
                    tabName, widget.node);
            });
    });
