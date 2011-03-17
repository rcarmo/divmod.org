
from cStringIO import StringIO
from email import Generator as G, MIMEMultipart as MMP, MIMEText as MT, MIMEImage as MI

from zope.interface import implements

from twisted.python.reflect import qual

from epsilon.extime import Time

from axiom import store
from axiom.item import Item
from axiom.attributes import integer, text
from axiom.userbase import LoginSystem
from axiom.plugins.mantissacmd import Mantissa

from nevow.testutil import FragmentWrapper

from xmantissa.ixmantissa import IOfferingTechnician
from xmantissa.webtheme import getLoader
from xmantissa.product import Product
from xmantissa.plugins.mailoff import plugin as quotientOffering

from xquotient.inbox import Inbox
from xquotient.mail import DeliveryAgent
from xquotient.iquotient import IMessageData
from xquotient.mimeutil import EmailAddress
from xquotient import smtpout

from xquotient.exmess import (SENDER_RELATION, RECIPIENT_RELATION,
                              COPY_RELATION, BLIND_COPY_RELATION)

class ThemedFragmentWrapper(FragmentWrapper):
    """
    I wrap myself around an Athena fragment, providing a minimal amount of html
    scaffolding in addition to an L{athena.LivePage}.

    The fragment will have its fragment parent and docFactory (based on
    fragmentName) set.
    """
    def render_fragment(self, ctx, data):
        f = super(ThemedFragmentWrapper, self).render_fragment(ctx, data)
        f.docFactory = getLoader(f.fragmentName)
        return f

class PartMaker:
    """
    Convenience class for assembling and serializing
    hierarchies of mime parts.
    """

    parent = None

    def __init__(self, ctype, body, *children):
        """
        @param ctype: content-type of this part.
        @param body: the string body of this part.
        @param children: arbitrary number of PartMaker instances
                         representing children of this part.
        """

        self.ctype = ctype
        self.body = body
        for c in children:
            assert c.parent is None
            c.parent = self
        self.children = children

    def _make(self):
        (major, minor) = self.ctype.split('/')

        if major == 'multipart':
            p = MMP.MIMEMultipart(minor,
                                  None,
                                  list(c._make() for c in self.children))
        elif major == 'text':
            p = MT.MIMEText(self.body, minor)
        elif major == 'image':
            p = MI.MIMEImage(self.body, minor)
        else:
            assert (False,
                    "Must be 'multipart', 'text' or 'image' (got %r)"
                    % (major,))

        return p

    def make(self):
        """
        Serialize this part using the stdlib L{email} package.
        @return: string
        """
        s = StringIO()
        G.Generator(s).flatten(self._make())
        s.seek(0)
        return s.read()


class MIMEReceiverMixin:
    def createMIMEReceiver(self):
        return self.deliveryAgent.createMIMEReceiver(
            u'test://' + self.deliveryAgent.store.filesdir.path)


    def setUpMailStuff(self, extraPowerups=(), dbdir=None, generateCert=False):
        filesdir = None
        if dbdir is None:
            filesdir = self.mktemp()
        self.siteStore = store.Store(dbdir=dbdir, filesdir=filesdir)
        Mantissa().installSite(self.siteStore, u"example.com", u"", generateCert)
        IOfferingTechnician(self.siteStore).installOffering(quotientOffering)

        loginSystem = self.siteStore.findUnique(LoginSystem)
        account = loginSystem.addAccount(u'testuser', u'example.com', None)
        self.substore = account.avatars.open()

        product = Product(
            store=self.siteStore,
            types=[qual(Inbox)] + map(qual, extraPowerups))
        product.installProductOn(self.substore)

        self.deliveryAgent = self.substore.findUnique(DeliveryAgent)
        return self.createMIMEReceiver()



class DummyMessageImplementationMixin:
    """
    Mock implementation of message data.
    """
    implements(IMessageData)

    def relatedAddresses(self):
        """Implement related address interface for creating correspondents
        """
        if self.senderInfo is None:
            yield (SENDER_RELATION, EmailAddress(
                    '"Alice Exampleton" <alice@a.example.com>'))
        else:
            yield (SENDER_RELATION, EmailAddress(self.senderInfo))
        yield (RECIPIENT_RELATION, EmailAddress('bob@b.example.com'))

    # maybe the rest of IMessageData...?
    def walkMessage(self, prefer=None):
        return []

    def walkAttachments(self, prefer=None):
        return []

    def associateWithMessage(self, m):
        pass

    def guessSentTime(self, default):
        return Time()

    def getReplyAddresses(self):
        return []

    def getAllReplyAddresses(self):
        return {}



class DummyMessageImplementation(Item, DummyMessageImplementationMixin):
    senderInfo = text(
        doc="""
        The sender as passed by the factory which created this implementation;
        used to provide a sensible implementation of relatedAddresses.
        """,
        default=None, allowNone=True)



class DummyMessageImplWithABunchOfAddresses(Item, DummyMessageImplementationMixin):
    """
    Mock L{xquotient.iquotient.IMessageData} which returns a bunch of things
    from L{relatedAddresses}
    """
    z = integer()

    def relatedAddresses(self):
        """
        Return one address for each relation type
        """
        for (rel, addr) in ((SENDER_RELATION, 'sender@host'),
                            (RECIPIENT_RELATION, 'recipient@host'),
                            (RECIPIENT_RELATION, 'recipient2@host'),
                            (COPY_RELATION, 'copy@host'),
                            (BLIND_COPY_RELATION, 'blind-copy@host')):
            yield (rel, EmailAddress(addr, False))

    def getAllReplyAddresses(self):
        fromAddrs = list(self.store.query(smtpout.FromAddress))
        fromAddrs = set(a.address for a in fromAddrs)

        relToKey = {SENDER_RELATION: 'to',
                    RECIPIENT_RELATION: 'to',
                    COPY_RELATION: 'cc',
                    BLIND_COPY_RELATION: 'bcc'}
        addrs = {}

        for (rel, addr) in self.relatedAddresses():
            if rel not in relToKey or addr.email in fromAddrs:
                continue
            addrs.setdefault(relToKey[rel], []).append(addr)
        return addrs
