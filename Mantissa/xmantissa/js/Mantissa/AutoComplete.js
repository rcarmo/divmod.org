// Copyright (c) 2006 Divmod.
// See LICENSE for details.

/**
 * This class contains the autocomplete logic
 *
 * L{appendCompletion} and L{complete} expect commas to be a meaningful
 * delimiter in the text that is being autocompleted, and L{complete} only
 * tries to complete the text after the last comma in the string it gets.  If
 * there is a use case for another kind of autocomplete, maybe the delimiter
 * specific stuff should go in a subclass of something
 */
Mantissa.AutoComplete.Model = Divmod.Class.subclass('Mantissa.AutoComplete.Model');
Mantissa.AutoComplete.Model.methods(
    /**
     * @param possibilities: sequence of possible completions.  The default
     * implementations of L{isCompletion} and L{complete} expect the
     * completions to be of type C{String}
     */
    function __init__(self, possibilities) {
        self.possibilities = possibilities;
    },

    /**
     * Figure out whether C{haystack} is a completion of C{needle}
     *
     * @type needle: C{String}
     * @type haystack: C{String}
     * @rtype: C{Boolean}
     */
    function isCompletion(self, needle, haystack) {
        return (0 < needle.length
                    && (haystack.toLowerCase().slice(0, needle.length)
                            == needle.toLowerCase()));
    },

    /**
     * @param s: comma-delimited string
     * @type s: C{String}

     * @return: last datum in C{s}, stripped of any leading or trailing
     * whitespace
     * @rtype: C{String}
     */
    function _getLastItemStripped(self, s) {
        var values = s.split(/,/),
            last = values[values.length - 1];
        return last.replace(/^\s+/, '').replace(/\s+$/, '');
    },

    /**
     * Find all the possible completions of C{s}
     *
     * @type s: C{String}
     *
     * @return: all of the strings in C{self.possibilities} which
     * L{isCompletion} thinks are completions of C{text}
     * @rtype: C{Array} of C{String}
     *
     * XXX We could be a lot smarter here if performance becomes a problem
     */
    function complete(self, s) {
        var text = self._getLastItemStripped(s),
            completions = [];

        for(var i = 0; i < self.possibilities.length; i++) {
            if(self.isCompletion(text, self.possibilities[i])) {
                completions.push(self.possibilities[i]);
            }
        }

        return completions;
    },

    /**
     * Append the completion C{completionText} to the text C{text}, stripping
     * off the prefix which is already present at the end of C{text}.
     * e.g. appendCompletion('x, y, z', 'zyz') => 'x, y, zyz, '
     *
     * @type text: C{String}
     * @type completionText: C{String}
     * @rtype: C{String}
     */
    function appendCompletion(self, text, completionText) {
        var last = self._getLastItemStripped(text);
        text = text.slice(0, text.length - last.length);
        return text + completionText + ", ";
    });

/**
 * I contain the portions of autocomplete functionality which need to
 * communicate with the DOM.
 *
 * FIXME: Maybe the model should know what the selection is
 */
Mantissa.AutoComplete.View = Divmod.Class.subclass('Mantissa.AutoComplete.View');
Mantissa.AutoComplete.View.methods(
    /**
     * @param textbox: The node that will be monitored for keypresses, and
     * below which the list of completions will be displayed
     * @type textbox: A textbox, or anything that might be a source of
     * keypress events
     *
     * @param completionsNode: the node which is to contain any user-visible
     * completions of the value of C{textbox} at any given time
     * @type completionsNode: block element
     */
    function __init__(self, textbox, completionsNode) {
        self.textbox = textbox;
        self.completionsNode = completionsNode;
    },

    /**
     * Attach function C{f} as a listener of keypress events originating from
     * our textbox node
     */
    function hookupKeypressListener(self, f) {
        self.textbox.onkeypress = f;
    },

    /**
     * Figure out if we are currently displaying any completions to the user
     *
     * @rtype: C{Boolean}
     */
    function displayingCompletions(self) {
        return self.completionsNode.style.display != "none";
    },

    /**
     * Figure out what the selected completion is.  See also
     * L{_selectCompletion}, L{moveSelectionUp} and L{moveSelectionDown}
     *
     * @rtype: C{null} or a C{Object} with C{offset} and C{value} members,
     * where C{offset} is the position of the selected completion in the
     * completions list, and C{value} is the value of the completion, i.e. the
     * actual text
     */
    function selectedCompletion(self) {
        var children = self.completionsNode.childNodes;
        for(var i = 0; i < children.length; i++) {
            if(children[i].className == "selected-completion") {
                return {offset: i, value: children[i].firstChild.nodeValue};
            }
        }
        return null;
    },

    /**
     * Select the completion at offset C{offset} in the completions list, and
     * deselect whatever completion was previously selected
     *
     * @type offset: C{Number}
     */
    function _selectCompletion(self, offset) {
        var children = self.completionsNode.childNodes,
            node = children[offset];
            selected = self.selectedCompletion();
        if(selected != null) {
            children[selected.offset].className = "completion";
        }
        node.className = "selected-completion";
    },

    /**
     * Figure out the number of completions we are currently displaying
     *
     * @type: C{Number}
     */
    function completionCount(self) {
        return self.completionsNode.childNodes.length;
    },

    /**
     * Select the completion below the currently selected completion, or the
     * first completion if the currently selected completion is the last
     */
    function moveSelectionDown(self) {
        var seloffset = self.selectedCompletion().offset;
        seloffset++;
        if(self.completionCount() == seloffset) {
            seloffset = 0;
        }
        self._selectCompletion(seloffset);
    },

    /**
     * Select the completion above the currently selected completion, or the
     * last if the currently selected completion is the first
     */
    function moveSelectionUp(self) {
        var seloffset = self.selectedCompletion().offset;
        seloffset--;
        if(seloffset == -1) {
            seloffset = self.completionCount()-1;
        }
        self._selectCompletion(seloffset);
    },

    /**
     * Get the value of the textbox
     *
     * @rtype: C{String}
     */
    function getValue(self) {
        return self.textbox.value;
    },

    /**
     * Set the value of the textbox
     *
     * @param value: the new value
     * @type value: C{String}
     */
    function setValue(self, value) {
        self.textbox.value = value;
    },

    /**
     * Remove all completions from the completions list
     */
    function emptyCompletions(self) {
        while(self.completionsNode.firstChild) {
            self.completionsNode.removeChild(
                self.completionsNode.firstChild);
        }
    },

    /**
     * Remove all completions from the completions list, and hide the
     * completions list
     */
    function emptyAndHideCompletions(self) {
        self.emptyCompletions();
        self.completionsNode.style.display = "none";
    },

    /**
     * Display C{completions} as the completions of the current value of our
     * textbox, removing any completions that were previously visible
     *
     * @type completions: C{Array} of C{String}
     */
    function showCompletions(self, completions) {
        self.emptyCompletions();
        for(var i = 0; i < completions.length; i++) {
            self.completionsNode.appendChild(
                self.makeCompletionNode(completions[i]));
        }
        self._selectCompletion(0);
        self.completionsNode.style.top = Divmod.Runtime.theRuntime.findPosY(self.textbox) +
                                         Divmod.Runtime.theRuntime.getElementSize(self.textbox).h + "px";
        self.completionsNode.style.left = Divmod.Runtime.theRuntime.findPosX(self.textbox) + "px";
        self.completionsNode.style.display = "";
    },

    /**
     * Make a node suitable for displaying C{completion}
     *
     * @type completion: C{String}
     * @rtype: node
     */
    function makeCompletionNode(self, completion) {
        var node = document.createElement("div");
        node.appendChild(document.createTextNode(completion));
        return node;
    });


/**
 * I coordinate L{Mantissa.AutoComplete.Model} and
 * L{Mantissa.AutoComplete.View}, and respond to events
 */
Mantissa.AutoComplete.Controller = Divmod.Class.subclass('Mantissa.AutoComplete.Controller');
Mantissa.AutoComplete.Controller.methods(
    /**
     * @type model: L{Mantissa.AutoComplete.Model}
     * @type view: L{Mantissa.AutoComplete.View}
     * @param scheduler: function which takes a function and a number of
     * milliseconds, and executes the function in that many milliseconds.  If
     * undefined, defaults to C{setTimeout}
     */
    function __init__(self, model, view, scheduler/*=setTimeout*/) {
        view.hookupKeypressListener(
            function(event) {
                return self.onkeypress(event);
            });
        self.model = model;
        self.view = view;
        if(scheduler == undefined) {
            scheduler = function(f, ms) {
                setTimeout(f, ms);
            }
        }
        self.scheduler = scheduler;
    },

    /**
     * Respond to a keypress event.
     *
     * @type event: Something with a C{keyCode} member
     */
    function onkeypress(self, event) {
        /* non alnum key pressed */
        if(0 < event.keyCode) {
            /* we only care if the completions are visible, because we want to
             * help the user navigate the list with the keyboard */
            if(!self.view.displayingCompletions()) {
                return true;
            }
            var TAB = 9, ENTER = 13, UP = 38, DOWN = 40;
            /* tab & enter mean "pick this one" */
            if(event.keyCode == ENTER || event.keyCode == TAB) {
                self.selectedCompletionChosen();
                return false;
            } else if(event.keyCode == DOWN) {
                self.view.moveSelectionDown();
            } else if(event.keyCode == UP) {
                self.view.moveSelectionUp();
            /* it was delete or something */
            } else {
                self.scheduleCompletion();
            }
        /* otherwise an alnum key, and we should try to complete what has been typed */
        } else {
            self.scheduleCompletion();
        }
        return true;
    },

    /**
     * Schedule a re-evaluation of the currently completions.  Called when the
     * keypress event handled by L{onkeypress} is suspected to have changed
     * the value of the view's input node
     *
     * XXX: Since we're usually responding to DOM events, the value of the
     * textbox hasn't actually been updated until all of the handlers for the
     * last keypress event have been called, so we hack it with the scheduler
     */
    function scheduleCompletion(self) {
        self.scheduler(
            function() {
                self.complete(self.view.getValue());
            }, 0);
    },

    /**
     * Ask the model what the completions for string C{s} are, and ask the
     * view to display them, or ask the view to display nothing if there are
     * no completions
     *
     * @type s: C{String}
     */
    function complete(self, s) {
        var completions = self.model.complete(s);
        if(0 < completions.length) {
            self.view.showCompletions(completions);
        } else {
            self.view.emptyAndHideCompletions();
        }
    },

    /**
     * Called when the last keypress event handled by L{onkeypress} indicates
     * that the currently selected completion is the one we want.
     */
    function selectedCompletionChosen(self) {
        var value = self.model.appendCompletion(
                        self.view.getValue(),
                        self.view.selectedCompletion().value);

        self.view.setValue(value);
        self.view.emptyAndHideCompletions();
    });
