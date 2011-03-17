from twisted.trial.unittest import TestCase
from twisted.web.microdom import parseString, getElementsByTagName
from twisted.web.domhelpers import gatherTextNodes

from xquotient.scrubber import scrub, scrubCIDLinks


class ScrubberTestCase(TestCase):
    def test_scrubCIDLinksWithLinks(self):
        """
        Test L{xquotient.scrubber.Scrubber.scrubCIDLinks with <a>s
        """

        node = parseString("""
        <html>
            <a href="cid:foo">with a CID URI</a>
            <a href="not a cid uri">without a CID URI</a>
        </html>
        """).documentElement

        scrubCIDLinks(node)

        (link,) = node.childNodes
        self.assertEquals(link.attributes['href'], 'not a cid uri')

    def test_scrubCIDLinksWithIFrames(self):
        """
        Test L{xquotient.scrubber.Scrubber.scrubCIDLinks} with <iframe>s
        """

        node = parseString("""
        <html>
            <IFRAME SRC="CID:foo">with a CID URL</IFRAME>
            <IFRAME SRC="http://foo.bar">without a CID URI</IFRAME>
        </html>
        """).documentElement

        scrubCIDLinks(node)

        (iframe,) = node.childNodes
        self.assertEquals(iframe.attributes['src'], 'http://foo.bar')

    def test_scrubCIDLinksWithImages(self):
        """
        Test L{xquotient.scrubber.Scrubber.scrubCIDLinks} with <img>s
        """

        node = parseString("""
        <html>
            <img src="cid:foo" />
            <img src="http://foo.bar" />
            <img src="cid:bar" />
            <img src="http://bar.baz" />
        </html>
        """).documentElement

        scrubCIDLinks(node)

        self.assertEquals(list(e.attributes['src'] for e in node.childNodes),
                          ['http://foo.bar', 'http://bar.baz'])

    def test_scrubCIDLinks(self):
        """
        Test L{xquotient.scrubber.Scrubber.scrubCIDLinks} with a bunch of
        different nodes
        """

        node = parseString("""
        <html>
            <img src="cid:foo" />
            <a href="x" name="1" />
            <iframe src="cid:bar" />
            <iframe name="2" />
            <a href="cid:xxx" />
            <img src="123" name="3" />
            <link href="cid:foo" />
            <link href="xyz" name="4" />
            <script src="cid:baz" />
            <script href="x" name="5" />
        </html>""").documentElement

        scrubCIDLinks(node)

        self.assertEquals(
                list(int(e.attributes['name']) for e in node.childNodes),
                [1, 2, 3, 4, 5])

    def test_scrubWithCIDLinkArg(self):
        """
        Test that L{xquotient.scrubber.Scrubber.scrub} pays attention to
        the C{filterCIDLinks} argument, when passed <a>s
        """

        node = parseString("""
        <html>
            <a href="x" />
            <a href="cid:foo" />
        </html>
        """).documentElement

        scrubbed = scrub(node, filterCIDLinks=False)
        self.assertEquals(
                list(e.attributes['href'] for e in scrubbed.firstChild().childNodes),
                ['x', 'cid:foo'])

        scrubbed = scrub(node, filterCIDLinks=True)
        self.assertEquals(
                list(e.attributes['href'] for e in scrubbed.firstChild().childNodes),
                ['x'])


    def test_scrubTrustsSpan(self):
        """
        Test that L{xquotient.scrubber.Scrubber} considers span to be a safe
        tag. Added because of #1641.
        """

        node = parseString("""
        <html>
            <span style='font-weight: bold; font-family:"Book Antiqua"'>
            Hello
            </span>
        </html>
        """).documentElement

        scrubbed = scrub(node)
        spans = getElementsByTagName(scrubbed, 'span')
        self.assertEquals(len(spans), 1)
        self.assertEquals(gatherTextNodes(spans[0]).strip(), "Hello")


    def test_scrubTrustsH1(self):
        """
        Test that L{xquotient.scrubber.Scrubber} considers h1 to be a safe tag.
        Added because of #1895.
        """
        node = parseString("<h1>Foo</h1>").documentElement
        scrubbed = scrub(node)
        h1s = getElementsByTagName(scrubbed, 'h1')
        self.assertEquals(len(h1s), 1)
        self.assertEquals(gatherTextNodes(h1s[0]).strip(), "Foo")
