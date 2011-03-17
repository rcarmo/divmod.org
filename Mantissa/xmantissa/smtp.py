# -*- test-case-name: xmantissa.test.test_smtp -*-

"""
An RFC 2821 address parser.
"""

import inspect, re

from twisted.internet import address

from xmantissa.error import (
    AddressTooLong, InvalidAddress, InvalidTrailingBytes)


class Address(object):
    """
    An RFC 2821 path.

    @ivar route: C{None} or a C{list} of C{str} giving the source-specified
    route of this message.  This is obsolete and should not be respected,
    but is made available for completeness.

    @ivar localpart: C{None} or a C{str} giving the local part of this address.

    @ivar domain: C{None} or a C{str}, L{IPv4Address} or L{IPv6Address}
    giving the domain part of this address.
    """
    route = localpart = domain = None

    def __init__(self, route, localpart, domain):
        assert (localpart is None) == (domain is None)

        self.route = route
        self.localpart = localpart
        self.domain = domain


    def __eq__(self, other):
        """
        Compare this address to another for equality.

        Two addresses are equal if their route, localpart, and domain
        attributes are equal.  Comparison against non-Address objects is
        unimplemented.
        """
        if isinstance(other, Address):
            a = (self.route, self.localpart, self.domain)
            b = (other.route, other.localpart, other.domain)
            return a == b
        return NotImplemented


    def __ne__(self, other):
        """
        Compare this address to another for inequality.

        See L{__eq__}.
        """
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result


    def __str__(self):
        """
        Format this address as an RFC 2821 path string.
        """
        mailbox = ''
        if self.localpart is not None:
            mailbox = '%s@%s' % (self.localpart, self.domain)
        route = ''
        if self.route is not None:
            route = '@' + ',@'.join(self.route) + ':'
        return '<%s%s>' % (route, mailbox)


    def __repr__(self):
        return 'Address(%r, %r, %r)' % (self.route, self.localpart, self.domain)



class _AddressParser(object):
    def f(s):
        d = inspect.currentframe().f_back.f_locals
        return "(?:" + (s % d) + ")"

    alpha = 'a-zA-Z'
    digit = '0-9'
    hexdigit = 'a-fA-F0-9'

    letDig = f(r"[%(alpha)s%(digit)s]")
    ldhStr = f(r"[%(alpha)s%(digit)s-]*%(letDig)s")

    sNum = f(r"[%(digit)s]{1,3}")
    ipv4AddressLiteral = f(r"%(sNum)s(?:\.%(sNum)s){3}")

    ipv6Hex = f(r"[%(hexdigit)s]")
    ipv6Full = f(r"%(ipv6Hex)s(?::%(ipv6Hex)s){7}")
    ipv6Comp = f(r"(?:%(ipv6Hex)s(?::%(ipv6Hex)s){0,5})?::(?:%(ipv6Hex)s(?::%(ipv6Hex)s){0,5})?")

    ipv6v4Full = f(r"%(ipv6Hex)s(?::%(ipv6Hex)s){5}:%(ipv4AddressLiteral)s")
    ipv6v4Comp = f(r"(?:%(ipv6Hex)s(?::%(ipv6Hex)s){0,3})?::(?:%(ipv6Hex)s(?::%(ipv6Hex)s){0,3})?%(ipv4AddressLiteral)s")

    ipv6Address = f(r"%(ipv6Full)s|%(ipv6Comp)s|%(ipv6v4Full)s|%(ipv6v4Comp)s")
    ipv6AddressLiteral = f(r"IPv6:%(ipv6Address)s")

    standardizedTag = ldhStr

    noWsCtl = '\x01-\x08\x0B\x0C\x0E-\x7F'

    somePrintableUSAscii = '\x21-\x5A\x5E-\x7E'

    text = '\x01-\x09\x0B\x0C\x0E-\x7F'
    quotedPair = f(r"\\[%(text)s]") # XXX obs-qp

    dtext = f(r"[%(noWsCtl)s%(somePrintableUSAscii)s]")
    dcontent = f(r"%(dtext)s|%(quotedPair)s")

    generalAddressLiteral = f(r"%(standardizedTag)s:%(dcontent)s+")

    qtext = f(r"%(noWsCtl)s|[\x21\x23-\x5B\x5D-\x7F]")
    qcontent = f(r"%(qtext)s|%(quotedPair)s")
    quotedString = f(r"\"(?:%(qcontent)s)*\"")

    addressLiteral = f(r"%(ipv4AddressLiteral)s|%(ipv6AddressLiteral)s|%(generalAddressLiteral)s")
    addressLiteralNamed = f(
        r"(?P<ipv4Literal>%(ipv4AddressLiteral)s)|"
        r"(?P<ipv6Literal>%(ipv6AddressLiteral)s)|"
        r"(?P<generalLiteral>%(generalAddressLiteral)s)")

    subdomain = f(r"%(letDig)s(?:%(ldhStr)s)?")
    domain = f(r"(?:%(subdomain)s(?:\.%(subdomain)s)+)|%(addressLiteral)s")
    domainNamed = f(r"(?P<domain>(?:%(subdomain)s(?:\.%(subdomain)s)+)|%(addressLiteralNamed)s)")
    atDomain = f(r"@%(domain)s")

    atext = f(r"%(letDig)s|[!#$%%&'*+-/=?^_`{|}-]")
    atom = f(r"%(atext)s+")
    dotString = f(r"%(atom)s(\.%(atom)s)*")

    localPart = f(r"%(dotString)s|%(quotedString)s")

    adl = f(r"(?P<adl>%(atDomain)s(?:,%(atDomain)s)*)")
    mailbox = f(r"(?P<localPart>%(localPart)s)?(?P<at>@)%(domainNamed)s?")

    path = f(r"<(?:%(adl)s:)?(?:%(mailbox)s)?>")

    address = re.compile("^" + path + "$")

    def __call__(self, arglist, line):
        # RFC 2821 4.5.3.1
        if len(line) > 256:
            raise AddressTooLong()

        match = self.address.match(line)
        if match is None:
            raise InvalidAddress()

        d = match.groupdict()

        if d['adl']:
            route = d['adl'][1:].split(',@')
        else:
            route = None

        localpart = d['localPart']

        if d['domain']:
            domain = d['domain']
        elif d['ipv4Literal']:
            domain = address.IPv4Address(d['ipv4Literal'])
        elif d['ipv6Literal']:
            # Chop off the leading 'IPv6:'
            domain = address.IPv6Address(d['ipv6Literal'][5:])
        else:
            domain = d['generalLiteral']

        at = d['at']

        if at:
            localpart = localpart or ''
            domain = domain or ''

        arglist.append(Address(route, localpart, domain))

        return match.end()



def parseAddress(address):
    """
    Parse the given RFC 2821 email address into a structured object.

    @type address: C{str}
    @param address: The address to parse.

    @rtype: L{Address}

    @raise xmantissa.error.ArgumentError: The given string was not a valid RFC
    2821 address.
    """
    parts = []
    parser = _AddressParser()
    end = parser(parts, address)
    if end != len(address):
        raise InvalidTrailingBytes()
    return parts[0]
