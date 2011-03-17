# -*- test-case-name: xquotient.test.test_renderers -*-
import re

from itertools import imap, cycle

from zope.interface import implements

from nevow import inevow, tags, flat, page

from xmantissa.publicresource import getLoader
from xmantissa import ixmantissa

_ILLEGAL_CHARS = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F]')

def replaceIllegalChars(s):
    """
    Replace characters in C{s} which should not appear in XML documents with a
    string representation of the character (e.g. '\x00 \x01' -> '0x0 0x1').
    This includes 0x00 and the C0 control set (0x01 through 0x1F), with the
    exception of CR (0x0D), LF (0x0A) and HT (0x09).

    See:
        * http://lists.w3.org/Archives/Public/public-i18n-geo/2003May/att-0030/W3C_I18N_Q_A_C0_Range.htm
        * http://www.w3.org/TR/REC-xml/#charsets
    """
    return _ILLEGAL_CHARS.sub(lambda match: hex(ord(match.group(0))), s)

def textToRudimentaryHTML(text):
    return flat.flatten(
                tags.html[
                    tags.body[
                        SpacePreservingStringRenderer(text).rend(None, None)]])

class ButtonRenderingMixin:
    """
    Convenience mixin to render pretty buttons.
    I can be mixed-in with a L{rend.Fragment} or a L{page.Element}
    """
    _buttonPattern = None

    def button(self, request, tag):
        if self._buttonPattern is None:
            self._buttonPattern = inevow.IQ(getLoader('button')).patternGenerator('button')
        # take the contents of the tag and stuff it inside the button pattern,
        # and copy over any attributes

        button = self._buttonPattern()
        button.attributes.update(tag.attributes)
        return button.fillSlots('content', tag.children)
    page.renderer(button)

    def render_button(self, ctx, data):
        return self.button(inevow.IRequest(ctx), ctx.tag)


class SpacePreservingStringRenderer(object):
    implements(inevow.IRenderer)

    def __init__(self, text):
        self.text = text

    def rend(self, context, line):
        # rethink this at some point, we probably dont need to do
        # strange things with stan here.  or do we.
        lines = self.text.split('\n')
        return self.intersperse(tags.br, imap(self.cruftifyMultipleSpaces, lines))

    def cruftifyMultipleSpaces(text):
        """Replace multiple spaces with &nbsp; such that they are rendered as we want."""
        if text.startswith(' '):
            yield tags.xml('&#160;')
            text = text[1:]
        chunks = text.split('  ')
        for i in SpacePreservingStringRenderer.intersperse(tags.xml(' &#160;'), chunks):
            yield i

    cruftifyMultipleSpaces = staticmethod(cruftifyMultipleSpaces)

    def intersperse(sep, seq):
        """yield 'seq' with 'sep' inserted between each element."""
        iterSeq = iter(seq)
        try:
            next = iterSeq.next()
        except StopIteration:
            return

        while True:
            yield next
            try:
                next = iterSeq.next()
            except StopIteration:
                return
            yield sep

    intersperse = staticmethod(intersperse)

class ParagraphRenderer:
    """
    slot content: filled with the content of this paragraph.

    pattern quoting-level: The pattern to use around quoted
        paragraphs. This pattern will be wrapped around the
        actual paragraph text once for each quoting depth.
        slot content: The content, either the unquoted-paragraph
            pattern or a previous quoting-level pattern when
            quote depth > 1
        slot color: The CSS color to use for this paragraph, pulled
            from the quoteColors list.
    """
    implements(inevow.IRenderer)
    quoteClasses = ('quote-one', 'quote-two', 'quote-three')

    def __init__(self, paragraph):
        self.paragraph = paragraph
        self.pattern = inevow.IQ(getLoader('message-detail-patterns')).onePattern('paragraphs')

    def rend(self, ctx, data):
        paragraphPattern = inevow.IQ(self.pattern).patternGenerator('paragraph')
        quoteClass = cycle(self.quoteClasses).next

        def walkParagraph(paragraph):
            for c in paragraph.children:
                if hasattr(c, 'depth'):
                    if 0 < c.depth:
                        qc = quoteClass()
                    else:
                        qc = 'no-quote'
                    p = paragraphPattern()
                    p.fillSlots('content', walkParagraph(c))
                    p.fillSlots('quote-class', qc)
                    yield p
                else:
                    yield SpacePreservingStringRenderer(
                        replaceIllegalChars(c))

        self.pattern.fillSlots('content', walkParagraph(self.paragraph))
        return self.pattern

class HTMLPartRenderer(object):
    implements(inevow.IRenderer)

    def __init__(self, original):
        self.original = original
        # think about this some more - the messageID or partID could be the
        # mangled storeID of the part to facilitate the making of child
        # links here, but nobody except for us really needs to know about
        # this.
        self.docFactory = getLoader('message-detail-patterns')
        self.iframePattern = inevow.IQ(
                self.docFactory).patternGenerator('content-iframe')

        self.urlPrefix = ixmantissa.IWebTranslator(
                            original.part.store).linkTo(original.messageID)

    def rend(self, ctx, data):
        translator = ixmantissa.IWebTranslator(self.original.part.store)
        webid = translator.toWebID(self.original.part)

        messageURL = translator.linkTo(self.original.part.message.storeID)

        return self.iframePattern.fillSlots('location', # argh
                messageURL + '/attachments/' + webid)

