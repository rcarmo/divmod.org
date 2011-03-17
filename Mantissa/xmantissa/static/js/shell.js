
/**
 * This javascript is rendered on all Mantissa pages as a consequence of the
 * fact that Mantissa provides both athena and non-athena pages with a
 * JavaScript-driven navigation system.
 *
 * There are therefore unfortunately no tests for it, as it exists outside the
 * Athena module system.  This script should be replaced by a proper module as
 * soon as we have removed all non-Athena pages from Mantissa.
 */

var MantissaShell = {};

MantissaShell.activeSubtabs = null;
MantissaShell.timeoutID = null;

/**
 * Return the first immediate child of C{node} which has the class name "subtabs"
 */
MantissaShell.getSubtabs = function(node) {
    for(var i = 0; i < node.childNodes.length; i++) {
        if(node.childNodes[i].className == "subtabs") {
            return node.childNodes[i];
        }
    }
};

/**
 * Called when a subtab is hovered over.
 * This action indicates that a user is still interacting with the menu bar,
 * and so it cancels the popdown timeout that gets started when the mouse
 * leaves the top level menu
 */
MantissaShell.subtabHover = function(node) {
    if (MantissaShell.timeoutID) {
        clearTimeout(MantissaShell.timeoutID);
        MantissaShell.timeoutID = null;
    }
};

/**
 * Called when the divmod "start menu" button is hovered over.
 * It cleans up the top level menu before it gets displayed
 */
MantissaShell.menuButtonHover = function() {
    var subtabs, child;
    var menu = document.getElementById("divmod-menu");
    for(var i = 0; i < menu.childNodes.length; i++) {
        child = menu.childNodes[i];
        if(child.tagName) {
            subtabs = MantissaShell.getSubtabs(child);
            if(subtabs && subtabs.style.display != "none") {
                subtabs.style.display = "none";
            }
        }
    }
};

/**
 * Pair of functions that toggle the menu container's class to work around IE's
 * lack of :hover support for anything other than <a> elements.
 */
MantissaShell.menuClick = function(node) {
    var menu = document.getElementById("divmod-menu"),
        nodeClickHandler = node.onclick,
        bodyMouseUpHandler = document.body.onmouseup;

    menu.style.display = "";
    node.onclick = null;
    document.body.onmouseup = function(event) {
        menu.style.display = "none";
        document.body.onmouseup = bodyMouseUpHandler;
        setTimeout(function() {
            node.onclick = nodeClickHandler;
        }, 1);
        return false;
    };
};

/**
 * Called when a top level tab is hovered over.
 * This makes the tab's submenu visible, if there is one.
 *
 * If positionLeft is true (the default), then the submenu should appear
 * directly to the right of the parent item when hovered over.
 */
MantissaShell.tabHover = function(node, positionLeft) {
    var subtabs = MantissaShell.getSubtabs(node.parentNode);
    if (positionLeft === undefined) {
        positionLeft = true;
    }

    if(!subtabs) {
        return;
    }

    if (MantissaShell.timeoutID) {
        clearTimeout(MantissaShell.timeoutID);
        MantissaShell.timeoutID = null;
        if (MantissaShell.activeSubtabs !== subtabs) {
            MantissaShell.activeSubtabs.style.display = 'none';
        }
    }

    if(positionLeft && !subtabs.style.left) {
        subtabs.style.left = node.parentNode.parentNode.clientWidth + "px";
        subtabs.style.marginTop = -node.clientHeight + "px";
    }
    if (subtabs.childNodes.length > 1) {
        subtabs.style.display = "";
    }
    MantissaShell.activeSubtabs = subtabs;
};

/**
 * Called when the mouse leaves a top level tab.
 * This starts a 100usec timer, which, when it expires, will make the
 * start menu disappear.
 * See also the docstring for C{subtabHover}
 */
MantissaShell.tabUnhover = function(node) {
    var subtabs = MantissaShell.getSubtabs(node.parentNode);
    if(subtabs) {
        MantissaShell.timeoutID = setTimeout(function() {
            subtabs.style.display = "none";
            MantissaShell.timeoutID = null;
        }, 100);
    }
};


/**
 * Called when the user clicks the small search button.
 * This toggles the visibility of the search form.
 */
MantissaShell.searchButtonClicked = function(node) {
    node.blur();

    var imgstate, color;
    var sfcont = document.getElementById("search-form");

    if(!sfcont.style.right) {
        sfcont.style.right = sfcont.clientWidth + "px";
    }

    if(sfcont.style.display == "none") {
        sfcont.style.display = "";
        imgstate = "selected";
        color = "#999999";
    } else {
        sfcont.style.display = "none";
        imgstate = "unselected";
        color = "";
    }

    node.firstChild.src = "/Mantissa/images/search-button-" + imgstate + ".png";
    node.parentNode.style.backgroundColor = color;
};
