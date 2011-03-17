
// import Divmod.Runtime

// import Nevow.Athena
// import Fadomatic
// import Mantissa

Mantissa.TDB.Controller = Nevow.Athena.Widget.subclass('Mantissa.TDB.Controller');
Mantissa.TDB.Controller.methods(
    function __init__(self, node, hasPrevPage, hasNextPage, curPage, itemsPerPage, items) {
        Mantissa.TDB.Controller.upcall(self, '__init__', node);
        self.tdbElements = {};
        self._setPageState(hasPrevPage, hasNextPage, curPage, itemsPerPage, items);
    },

    function _toggleThrobberVisibility(self) {
        if(!self.node.style.opacity || self.node.style.opacity == '1') {
            self.node.style.opacity = '.3';
        } else {
            self.node.style.opacity = '1';
        }

        try {
            var t = self._getHandyNode('throbber');
        } catch(e) { return };

        if(!t) {
            return;
        }

        if(t.style.visibility == 'hidden') {
            t.style.visibility = 'visible';
        } else {
            t.style.visibility = 'hidden';
        }
    },

    function _setTableContent(self, tableContent) {
        Divmod.Runtime.theRuntime.setNodeContent(self._getHandyNode("tdb-table"),
                                '<div xmlns="http://www.w3.org/1999/xhtml">' + tableContent + '</div>');
    },

    function _getHandyNode(self, classValue) {
        if(!(classValue in self.tdbElements)) {
            self.tdbElements[classValue] = self.nodeByAttribute('class', classValue);
        }
        return self.tdbElements[classValue];
    },

    function _differentPage(self /*, ...*/) {
        self._toggleThrobberVisibility();

        var args = [];
        for (var i = 1; i < arguments.length; ++i) {
            args.push(arguments[i]);
        }

        var d = self.callRemote.apply(self, args);
        d.addCallback(function(result) {
                          var tdbTable = result[0];
                          var tdbState = result[1];
                          self._setTableContent(tdbTable);
                          self._setPageState.apply(self, tdbState);
                      });
        d.addBoth(function(ign) { self._toggleThrobberVisibility() });
        return false;
    },

    function _setPageState(self, hasPrevPage, hasNextPage, curPage, itemsPerPage, items) {
        var cp = self._getHandyNode("tdb-control-panel");
        if(items == 0) {
            cp.style.display = "none";
        } else {
            cp.style.display = "";
        }
        function setValue(eid, value) {
            var e = self._getHandyNode(eid);
            if(e.childNodes.length == 0) {
                e.appendChild(document.createTextNode(value));
            } else {
                e.firstChild.nodeValue = value;
            }
        }

        var offset = (curPage - 1) * itemsPerPage + 1;
        var end = offset + itemsPerPage - 1;
        if(items < end) {
            end = items;
        }
        setValue("tdb-item-start", offset);
        setValue("tdb-item-end", end);
        setValue("tdb-total-items", items);

        function enable(things) {
            for(var i = 0; i < things.length; i++) {
                var thing = things[i];
                self._getHandyNode(thing).style.display = "inline";
                self._getHandyNode(thing + "-disabled").style.display = "none";
            }
        }

        function disable(things) {
            for(var i = 0; i < things.length; i++) {
                var thing = things[i];
                self._getHandyNode(thing + "-disabled").style.display = "inline";
                self._getHandyNode(thing).style.display = "none";
            }
        }

        var prevs = ["prev-page", "first-page"];
        var nexts = ["next-page", "last-page"];

        if (hasPrevPage) {
            enable(prevs);
        } else {
            disable(prevs);
        }
        if (hasNextPage) {
            enable(nexts);
        } else {
            disable(nexts);
        }

    },

    function prevPage(self) {
        return self._differentPage('prevPage');
    },

    function nextPage(self) {
        return self._differentPage('nextPage');
    },

    function firstPage(self) {
        return self._differentPage('firstPage');
    },

    function lastPage(self) {
        return self._differentPage('lastPage');
    },

    function performAction(self, actionID, targetID) {
        self._toggleThrobberVisibility();

        var d = self.callRemote('performAction', actionID, targetID);
        d.addCallback(function(result) {
                          var tdbTable = result[1][0];
                          var tdbState = result[1][1];
                          self._setTableContent(tdbTable);
                          self._setPageState.apply(self, tdbState);
                          self._actionResult(result[0]);
                      });
        d.addBoth(function(ign) { self._toggleThrobberVisibility() });
        return false;
    },

    function clickSort(self, attributeID) {
        return self._differentPage('clickSort', attributeID);
    },

    function _actionResult(self, message) {
        var resultContainer = self._getHandyNode('tdb-action-result');

        if(resultContainer.childNodes.length)
            resultContainer.removeChild(resultContainer.firstChild);

        var span = document.createElement("span");
        span.appendChild(document.createTextNode(message));
        resultContainer.appendChild(span);

        new Fadomatic(span, 2).fadeOut();
    });
