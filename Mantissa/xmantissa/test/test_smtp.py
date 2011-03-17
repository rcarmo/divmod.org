
from twisted.trial.unittest import TestCase

from xmantissa.smtp import Address, parseAddress
from xmantissa.error import ArgumentError

class AddressParserTestCase(TestCase):
    """
    Test the RFC 2821 address parser.
    """
    def _addrTest(self, addr, exp):
        """
        Assert that the given address string parses to the given address
        object.

        @type addr: C{str}
        @type exp: L{Address}
        """
        a = parseAddress(addr)
        self.assertEquals(a, exp, "Misparsed %r to %r" % (addr, a))


    def test_longAddressRejected(self):
        """
        Test that an address longer than 256 bytes is rejected as illegal.
        """
        format = '<%s@example.com>'
        address = format % ('x' * (257 - len(format) + 2),)
        self.assertEqual(len(address), 257)
        self.assertRaises(ArgumentError, parseAddress, address)


    def test_nullAddress(self):
        """
        Test the parsing of the null address.
        """
        return self._addrTest('<>', Address(None, None, None))


    def test_emptyAddress(self):
        """
        Test the parsing of an address with empty local and domain parts.
        """
        return self._addrTest('<@>', Address(None, '', ''))


    def test_localOnly(self):
        """
        Test the parsing of an address with a non-empty local part and an
        empty domain part.
        """
        return self._addrTest('<localpart@>', Address(None, 'localpart', ''))


    def test_domainOnly(self):
        """
        Test the parsing of an address with an empty local part and a
        non-empty domain part.
        """
        return self._addrTest(
            '<@example.com>', Address(None, '', 'example.com'))


    def test_commonAddress(self):
        """
        Test the common case, an address with non-empty local and domain
        parts.
        """
        return self._addrTest(
            '<localpart@example.com>',
            Address(None, 'localpart', 'example.com'))


    def test_dottedLocalpart(self):
        """
        Test parsing of an address with a dotted local part.
        """
        return self._addrTest(
            '<local.part@>', Address(None, 'local.part', ''))


    def test_ipv4Literal(self):
        """
        Test parsing of an IPv4 domain part literal.
        """
        return self._addrTest('<@9.8.7.6>', Address(None, '', '9.8.7.6'))


    def test_ipv4LiteralWithLocalpart(self):
        """
        Test parsing of an IPv4 domain part literal with a non-empty local
        part.
        """
        return self._addrTest(
            '<localpart@1.2.3.4>', Address(None, 'localpart', '1.2.3.4'))


    def test_singlePartSourceRoute(self):
        """
        Test parsing of an address with a one element source route.
        """
        return self._addrTest(
            '<@foo.bar:localpart@example.com>',
            Address(['foo.bar'], 'localpart', 'example.com'))


    def test_multiplePartSourceRoute(self):
        """
        Test parsing of an address with a two element source route.
        """
        return self._addrTest(
            '<@foo.bar,@bar.baz:localpart@example.com>',
            Address(['foo.bar', 'bar.baz'], 'localpart', 'example.com'))


    def test_ipv6Literal(self):
        """
        Test parsing of an IPv6 domain part literal.
        """
        return self._addrTest('<@IPv6:::1>', Address(None, '', '::1'))
    test_ipv6Literal.skip = "Add IPv6 support to Twisted"


    def test_ipv6LiteralWithLocalpart(self):
        """
        Test parsing of an IPv6 domain part literal with a non-empty local
        part.
        """
        return self._addrTest(
            '<localpart@IPv6:::1>', Address(None, 'localpart', '::1'))
    test_ipv6LiteralWithLocalpart.skip = "Add IPv6 support to Twisted"
