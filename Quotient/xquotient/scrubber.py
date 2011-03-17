# -*- test-case-name: xquotient.test.test_scrubber -*-
# Copyright 2005 Divmod, Inc.  See LICENSE file for details

"""
Code which can take an incoming DOM tree and \"scrub\" it clean,
removing all tag attributes which could potentially be harmful, and
turning potentially harmful tags such as script and style tags into
div tags.
"""

from twisted.web.microdom import lmx
from twisted.web.microdom import Element, Comment, Text
from twisted.web import domhelpers


# GAWD this is cheap
# remind me to put it in a new release of Twisted at some point

def setTagName(self, tagName):
    self.endTagName = self.nodeName = self.tagName = tagName

Element.setTagName = setTagName


class Scrubber(object):
    _alwaysSafeAttributes = ['class', 'id', 'style', 'lang', 'dir', 'title',
                             'tabindex', 'alt']

    _goodHtml = {
        'html': [],
        'head': [],
        'title': [],
        'body': ['bgcolor'],
        'style': ['type'],
        'a': ['href', 'tabindex', 'title', 'rel', 'rev', 'shape', 'coords',
              'charset', 'type', 'name', 'hreflang'],
        'abbr': [],
        'acronym': [],
        'address': [],
        'area': ['name', 'shape', 'coords', 'nohref', 'usemap'],
        'b': [],
        'base': [],
        'basefont': [],
        'bdo': [],
        'big': [],
        'blockquote': ['cite'],
        'br': ['clear'],
        'caption': ['align'],
        'center': [],
        'cite': [],
        'code': [],
        'col': ['span', 'width'],
        'colgroup': ['span', 'width'],
        'dd': [],
        'del': ['cite', 'datetime'],
        'dfn': [],
        'dir': ['compact'],
        'div': [],
        'dl': [],
        'dt': [],
        'em': [],
        'fieldset': [],
        'font': ['size', 'face', 'style', 'color'],
        'form': ['action', 'method'],
        'hr': ['align', 'noshade', 'size', 'width'],
        'h1': [],
        'h2': [],
        'h3': [],
        'h4': [],
        'h5': [],
        'h6': [],
        'i': [],
        'img': ['width', 'height', 'src'],
        'input': ['type', 'name', 'value', 'checked', 'alt', 'maxlength',
                  'size', 'tabindex', 'accept'],
        'ins': ['cite', 'datetime'],
        'isindex': ['prompt'],
        'kbd': [],
        'label': ['for'],
        'legend': ['align'],
        'li': ['type', 'start', 'value', 'compact'],
        'map': [],
        'menu': ['compact'],
        'noscript': [],
        'ol': ['type', 'start', 'value', 'compact'],
        'optgroup': ['name', 'size', 'multiple', 'tabindex'],
        'option': ['name', 'size', 'multiple', 'tabindex'],
        'p': ['align'],
        'pre': ['width'],
        'q': ['cite'],
        's': [],
        'samp': [],
        'select': ['name', 'size', 'multiple', 'tabindex'],
        'small': [],
        'span': [],
        'strike': [],
        'strong': [],
        'style': [],
        'sub': [],
        'sup': [],
        'table': ['width', 'height', 'cellpadding', 'cellspacing', 'border', 'bgcolor', 'valign', 'summary', 'align'],
        'tbody': ['align', 'char', 'charoff', 'valign'],
        'tr': ['bgcolor', 'valign', 'height', 'align', 'char', 'charoff'],
        'td': ['width', 'height', 'valign', 'align', 'nowrap', 'bgcolor',
               'headers', 'scope', 'abbr', 'axis', 'rowspan', 'colspan',
               'nowrap', 'charoff', 'char'],
        'textarea': ['name', 'rows', 'cols', 'readonly', 'disabled',
                     'tabindex'],
        'tfoot': ['align', 'char', 'charoff', 'valign'],
        'th': ['width', 'height', 'valign', 'align', 'nowrap', 'bgcolor',
               'headers', 'scope', 'abbr', 'axis', 'rowspan', 'colspan',
               'nowrap', 'charoff', 'char'],
        'thead': ['align', 'char', 'charoff', 'valign'],
        'tt': [],
        'u': [],
        'ul': ['type', 'start', 'value', 'compact'],
        'var': []
        }

    _linkAttributes = ('src', 'href', 'usemap', 'cite')

    def iternode(self, n):
        """
        Iterate a node using a pre-order traversal, yielding every
        Element instance.
        """
        if getattr(n, 'clean', None):
            return
        if isinstance(n, Element):
            yield n
        newChildNodes = None
        for c in n.childNodes:
            if isinstance(c, Comment):
                if not newChildNodes:
                    newChildNodes = n.childNodes[:]
            else:
                for x in self.iternode(c):
                    yield x
        if newChildNodes:
            n.childNodes = newChildNodes


    def spanify(self, node):
        node.attributes = {}
        node.childNodes = []
        node.endTagName = node.nodeName = node.tagName = 'span'
        lnew = lmx(node).span()
        lnew.node.clean = True
        return lnew

    def _handle_img(self, node):
        ## TODO: Pass some sort of context object so we can know whether the user
        ## wants to display images for this message or not
        # del node.attributes['src'] #  = '/images/missing.png'
        oldSrc = node.attributes.get('src', '')
        l = self.spanify(node)
        l['class'] = 'blocked-image'
        a = l.a(href=oldSrc)
        img = a.img(src="/images/bumnail.png", style="height: 25px; width: 25px")
        img.clean = True
        return node

    def _filterCIDLink(self, node):
        for attr in self._linkAttributes:
            if (attr in node.attributes
                    and node.attributes[attr][:4].lower() == 'cid:'):
                return True

    def scrubCIDLinks(self, node):
        """
        Remove all nodes with links that point to CID URIs

        For reasons of convenience, this mutates its input
        """
        for e in self.iternode(node):
            if self._filterCIDLink(e):
                e.parentNode.removeChild(e)

    def scrub(self, node, filterCIDLinks=True):
        """
        Remove all potentially harmful elements from the node and
        return a wrapper node.

        For reasons (perhaps dubious) of performance, this mutates its
        input.
        """
        if node.nodeName == 'html':
            filler = body = lmx().div(_class="message-html")
            for c in node.childNodes:
                if c.nodeName == 'head':
                    for hc in c.childNodes:
                        if hc.nodeName == 'title':
                            body.div(_class="message-title").text(domhelpers.gatherTextNodes(hc))
                            break
                elif c.nodeName == 'body':
                    filler = body.div(_class='message-body')
                    break
        else:
            filler = body = lmx().div(_class="message-nohtml")
        for e in self.iternode(node):
            if getattr(e, 'clean', False):
                # If I have manually exploded this node, just forget about it.
                continue
            ennl = e.nodeName.lower()

            if filterCIDLinks and self._filterCIDLink(e):
                # we could replace these with a marker element, like we do
                # with dangerous tags, but i'm not sure there is a reason to
                e.parentNode.removeChild(e)

            if ennl in self._goodHtml:
                handler = getattr(self, '_handle_' + ennl, None)
                if handler is not None:
                    e = handler(e)
                newAttributes = {}
                oldAttributes = e.attributes
                e.attributes = newAttributes
                goodAttributes = self._goodHtml[ennl] + self._alwaysSafeAttributes
                for attr in goodAttributes:
                    if attr in oldAttributes:
                        newAttributes[attr] = oldAttributes[attr]
            else:
                e.attributes.clear()
                e.setTagName("div")
                e.setAttribute("class", "message-html-unknown")
                e.setAttribute("style", "display: none")
                div = Element('div')
                div.setAttribute('class', 'message-html-unknown-tag')
                div.appendChild(Text("Untrusted %s tag" % (ennl, )))
                e.childNodes.insert(0, div)
        filler.node.appendChild(node)
        return body.node

scrub = Scrubber().scrub
scrubCIDLinks = Scrubber().scrubCIDLinks
