// -*- test-case-name: xmantissa.test.test_javascript -*-
// Copyright (c) 2007-2010 Divmod.
// See LICENSE for details.

/**
 * Functionality for performing string substitution on the content of DOM
 * nodes.
 */

/**
 * Split C{str} where it matches C{pattern}, applying C{replacer} to the
 * matching portions, and replacing them with its return value.
 *
 * @param str: a string.
 * @type str: C{String}
 *
 * @param pattern: a regular expression.
 * @type pattern: C{RegExp}
 *
 * @param replacer: a function which knows how to turn strings into DOM nodes.
 * @type replacer: C{Function}
 *
 * @return: a list of strings and DOM nodes (returned by C{replacer}).
 * @rtype: C{Array} or C{null}, if C{pattern} does not match anywhere.
 */
Mantissa.DOMReplace._intermingle = function _intermingle(str, pattern,
                                                         replacer) {
    var piece;
    var pieces = [str];
    var match;
    while(true) {
        piece = pieces.pop();
        match = pattern.exec(piece);
        if(!match) {
            /* If nothing matched so far, then we can just stop now.  The
             * check at the end of the function will convert the empty result
             * array to a null result which saves us a little bit of DOM
             * munging later.  But if anything else has matched, then we have
             * to push back the string we're checking: it represents part of
             * the original input, and if it's not in the pieces array, it
             * won't end up in the final document.  That would be bad.
             */
            if (pieces.length) {
                pieces.push(piece);
            }
            break;
        }
        if(0 < match.index) {
            pieces.push(piece.slice(0, match.index));
        }
        pieces.push(replacer(match[0]));
        if(match.index + match[0].length < piece.length) {
            pieces.push(piece.slice(match.index + match[0].length,
                                    piece.length));
        } else {
            break;
        }
    }
    if(pieces.length == 0) {
        return null;
    }
    return pieces;
}

/**
 * Enact the series of node-content transformations described by the objects
 * in C{pendingChanges}.
 *
 * @param pendingChanges: A series of objects describing nodes which should be
 * replaced with other nodes.
 * @type pendingChanges: C{Array} of C{Object}, each having a I{reference} key (the
 * old node), and a I{replacements} key (C{Array} of nodes or of C{String}s to replace
 * I{reference} with).
 *
 * @rtype: C{undefined}
 */
Mantissa.DOMReplace._rewrite = function _rewrite(pendingChanges) {
    for(var i = 0; i < pendingChanges.length; i++) {
        for(var j = 0; j < pendingChanges[i].replacements.length; j++) {
            var replacement = pendingChanges[i].replacements[j];
            if(replacement.nodeType == undefined) {
                replacement = document.createTextNode(replacement);
            }
            pendingChanges[i].reference.parentNode.insertBefore(
                replacement,
                pendingChanges[i].reference);
        }
        pendingChanges[i].reference.parentNode.removeChild(pendingChanges[i].reference);
    }
}

/**
 * Replace all instances of C{pattern} that occur within the values of text
 * nodes beneath C{node} with the result of calling C{replacer} on the match
 * text.
 *
 * @param node: the node at which to begin the search.
 * @type node: nodey thing
 *
 * @param pattern: the text we want to look for.
 * @type pattern: C{RegExp}
 *
 * @param replacer: a function which knows how to turn strings into DOM nodes.
 * @type replacer: C{Function}
 *
 * @param descender: (optional) a function which knows what kinds of nodes
 * it's worth descending into.  if specified, this function takes a node and
 * returns a L{Divmod.Runtime.Platform.DOM_*} constant indicating the desired
 * traverser action.  the default will descend into all nodes.
 * @type descender: function

 * @return: nothing.  C{node} is mutated.
 * @rtype: C{undefined}
 */
Mantissa.DOMReplace.replace = function replace(node, pattern, replacer, /*optional*/descender) {
    var pendingChanges = [];
    if(descender === undefined) {
        descender = function(node) {
            return Divmod.Runtime.Platform.DOM_DESCEND;
        }
    }
    Divmod.Runtime.theRuntime.traverse(
        node,
        function(node) {
            if(node.nodeType == node.TEXT_NODE) {
                var replacements = Mantissa.DOMReplace._intermingle(
                    node.nodeValue, pattern, replacer);
                if(replacements !== null) {
                    pendingChanges.push({reference: node,
                                         replacements: replacements});
                }
                return Divmod.Runtime.Platform.DOM_CONTINUE;
            }
            return descender(node);
        });

    Mantissa.DOMReplace._rewrite(pendingChanges);
}

/**
 * Turn C{url} in into a DOM node which will render as a link to C{url}.
 *
 * @param url: a url.
 * @type url: C{String}.
 *
 * @return: an "A" node.
 * @rtype: node.
 */
Mantissa.DOMReplace._urlToLink = function _urlToLink(url) {
    var linkTarget;
    if(url.slice(0, 3).toLowerCase() == "www") {
        linkTarget = "http://" + url;
    } else {
        linkTarget = url;
    }
    var link = document.createElement('a');
    link.href = linkTarget;
    link.target = '_blank';
    link.appendChild(document.createTextNode(url));
    return link;
}

/**
 * Turn the bits of text nodes inside C{node} which look like URLs into "A"
 * nodes linking to those urls.
 *
 * @param node: the node at which to begin the search.
 * @type node: nodey thing
 *
 * @return: nothing.  C{node} is mutated.
 * @rtype: C{undefined}
 */
Mantissa.DOMReplace.urlsToLinks = function urlsToLinks(node) {
    Mantissa.DOMReplace.replace(
        node,
        /(?:\w+:\/\/|www\.)[^\s\<\>\'\(\)\"]+[^\s\<\>\(\)\'\"\?\.]/,
        Mantissa.DOMReplace._urlToLink,
        function(node) {
            /* who cares about urls already in links */
            if(node.tagName.toLowerCase() == "a") {
                return Divmod.Runtime.Platform.DOM_CONTINUE;
            }
            return Divmod.Runtime.Platform.DOM_DESCEND;
        });
}
