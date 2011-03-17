from itertools import cycle

from twisted.web import microdom
from twisted.trial.unittest import TestCase

from nevow.flat import flatten

from xquotient import mimepart
from xquotient import renderers
from xquotient.benchmarks.rendertools import renderPlainFragment

class RenderersTestCase(TestCase):
    """
    Tests for L{xquotient.renderers}
    """

    def test_spacePreservingStringRenderer(self):
        """
        Check that L{renderers.SpacePreservingStringRenderer} does the
        right thing with newlines and spaces
        """

        def assertRenderedEquals(input, output):
            renderer = renderers.SpacePreservingStringRenderer(input)
            self.assertEqual(renderPlainFragment(renderer), output)

        assertRenderedEquals('', '')
        assertRenderedEquals('hello', 'hello')
        assertRenderedEquals('h ello', 'h ello')
        assertRenderedEquals('  x  ', '&#160; x &#160;')
        assertRenderedEquals('x\ny\n  z', 'x<br />y<br />&#160; z')

    def _renderQuotedMessage(self, levels):
        text = '\n'.join(('>' * i) + str(i) for i in xrange(levels))
        return renderPlainFragment(
                    renderers.ParagraphRenderer(
                        mimepart.FlowedParagraph.fromRFC2646(text)))

    def test_paragraphNesting(self):
        """
        Check that L{renderers.ParagraphRenderer} doesn't explode
        if asked to render a deep tree of paragraphs
        """
        self._renderQuotedMessage(1000)

    def test_quotingLevels(self):
        """
        Check that L{renderers.ParagraphRenderer} assigns the
        right quoting levels to things
        """

        doc = microdom.parseString('<msg>' + self._renderQuotedMessage(5) + '</msg>')
        quoteClass = cycle(renderers.ParagraphRenderer.quoteClasses).next
        self.assertEqual(doc.firstChild().firstChild().nodeValue.strip(), '0')

        for (i, div) in enumerate(doc.getElementsByTagName('div')):
            self.assertEqual(div.attributes['class'], quoteClass())
            self.assertEqual(div.firstChild().nodeValue.strip(), str(i + 1))

        self.assertEqual(i, 3)

    def test_paragraphRendererPreservesWhitespace(self):
        self.assertEqual(
            renderPlainFragment(
                renderers.ParagraphRenderer(
                    mimepart.FixedParagraph.fromString('  foo'))).strip(),
            '&#160; foo')


    def test_paragraphRendererReplacesIllegalChars(self):
        """
        Test that L{xquotient.renderers.ParagraphRenderer} replaces
        XML-illegal characters in the content of the paragraph it is passed
        """
        para = mimepart.FixedParagraph.fromString('\x00 hi!')
        rend = renderers.ParagraphRenderer(para)
        self.assertEqual(renderPlainFragment(rend).strip(), '0x0 hi!')


    def test_replaceIllegalChars(self):
        """
        Test that L{xquotient.renderers.replaceIllegalChars} replaces 0x00 +
        everything in the C0 control set minus CR, LF and HT with strings
        describing the missing characters
        """
        s = ''.join(map(chr, range(32))) + 'foobar'
        # ord('\t') < ord('\n') < ord('\r')
        expected = (
            ''.join(hex(n) for n in xrange(ord('\t'))) +
            '\t\n0xb0xc\r' +
            ''.join(hex(n) for n in xrange(ord('\r')+1, 32)) +
            'foobar')

        self.assertEquals(
            renderers.replaceIllegalChars(s), expected)
