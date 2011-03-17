# -*- test-case-name: xquotient.test.test_mimepart -*-

import itertools
import quopri, binascii, rfc822

from zope.interface import implements

from twisted.python import log

from epsilon.extime import Time

from axiom import item, attributes, iaxiom

from xquotient import mimepart, equotient, mimeutil, exmess, iquotient, smtpout


class Header(item.Item):
    """
    Database resident representation of a MIME header.
    """
    typeName = 'quotient_mime_header'
    schemaVersion = 1

    message = attributes.reference(
        "A reference to the stored top-level L{xquotient.exmess.Message} "
        "object to which this header pertains.",
        reftype=exmess.Message,
        whenDeleted=attributes.reference.CASCADE)
    part = attributes.reference(
        "A reference to the stored MIME part object to which this header "
        "directly pertains.")

    name = attributes.text(
        "The name of this header.  What it is called.",
        allowNone=False)
    value = attributes.text(
        "The decoded value of this header.",
        allowNone=False)
    index = attributes.integer(
        "The position of this header within a part.",
        indexed=True, allowNone=False)

    # This compound index matches the getHeader[s] query and is critical for
    # interactive performance.

    attributes.compoundIndex(part, name)



class Part(item.Item):
    """
    Database resident representation of a MIME-part (including the top level
    part, the message itself).
    """
    implements(iquotient.IMessageData)

    typeName = 'quotient_mime_part'
    schemaVersion = 1

    parent = attributes.reference(
        "A reference to another Part object, or None for the top-level part.")
    message = attributes.reference(
        "A reference to the stored top-level L{xquotient.exmess.Message} "
        "object to which this part pertains.",
        reftype=exmess.Message,
        whenDeleted=attributes.reference.CASCADE)
    partID = attributes.integer(
        "A unique identifier for this Part within the context of its L{message}.")

    source = attributes.path(
        "The file which contains this part, MIME-encoded.")

    headersOffset = attributes.integer(
        "The byte offset within my source file where my headers begin.")
    headersLength = attributes.integer(
        "The length in bytes that all my headers consume within the source file.")
    bodyOffset = attributes.integer(
        "The byte offset within my source file where my body begins (4 bytes "
        "after where my headers end).")
    bodyLength = attributes.integer(
        "The length in bytes that my body consumes within the source file.")


    _partCounter = attributes.inmemory(
        "Temporary Part-ID factory function used to assign IDs to parts "
        "of this message.")
    _headers = attributes.inmemory(
        "Temporary storage for header data before this Part is added to "
        "a database.")
    _children = attributes.inmemory(
        "Temporary storage for child parts before this Part is added to "
        "a database.")

    def __init__(self, *a, **kw):
        super(Part, self).__init__(*a, **kw)
        log.msg(interface=iaxiom.IStatEvent,
                stat_mimePartsCreated=1)

    def addHeader(self, name, value):
        if self.store is not None:
            raise NotImplementedError(
                "Don't add headers to in-database messages - they aren't mutable [yet?]")
        if not hasattr(self, '_headers'):
            self._headers = []

        self._headers.append(Header(name=name.decode('ascii', 'ignore').lower(),
                                    value=value,
                                    part=self,
                                    message=self.message,
                                    index=len(self._headers)))

    def walk(self, shallow=False):
        """
        @param shallow: return only immediate children?
        """
        # this depends on the order the parts are returned by the queries
        if shallow:
            return self._walkShallow()
        return self._walkDeep()

    def _walkDeep(self):
        yield self
        for child in self.store.query(Part, Part.parent == self):
            for grandchild in child.walk():
                yield grandchild

    def _walkShallow(self):
        return self.store.query(Part, Part.parent == self)

    def getSubPart(self, partID):
        return self.store.findUnique(Part,
                attributes.AND(Part.parent==self,
                               Part.partID==partID))

    def getHeader(self, name):
        for hdr in self.getHeaders(name, _limit=1):
            return hdr.value
        raise equotient.NoSuchHeader(name)

    def getHeaders(self, name, _limit=None):
        name = name.lower()
        if self.store is not None:
            if not isinstance(name, unicode):
                name = name.decode("ascii")
            return self.store.query(
                Header,
                attributes.AND(Header.part == self,
                               Header.name == name),
                sort=Header.index.ascending,
                limit=_limit)
        else:
            if not hasattr(self, '_headers'):
                self._headers = []
            return (hdr for hdr in self._headers if hdr.name == name)

    def getAllHeaders(self):
        if self.store is not None:
            return self.store.query(
                Header,
                Header.part == self,
                sort=Header.index.ascending)
        else:
            if hasattr(self, '_headers'):
                return iter(self._headers)
            else:
                return iter(())

    def newChild(self):
        if self.store is not None:
            raise NotImplementedError(
                "Don't add children to in-database messages - they aren't mutable [yet?]")
        if not hasattr(self, '_children'):
            self._children = []
        p = Part(partID=self._partCounter(),
                 source=self.source,
                 _partCounter=self._partCounter)
        self._children.append(p)
        return p


    def _addToStore(self, store, message, sourcepath):
        self.source = sourcepath
        self.message = message
        self.store = store

        if hasattr(self, '_headers'):
            for hdr in self._headers:
                hdr.part = self
                hdr.message = self.message
                hdr.store = store

        if hasattr(self, '_children'):
            for child in self._children:
                child.parent = self
                child._addToStore(store, message, sourcepath)

        del self._headers, self._children

    def associateWithMessage(self, message):
        """
        Implement L{IMessageData.associateWithMessage} to add this part and all
        of its subparts and headers to the same store as the given message, and
        set all of their headers.

        This will only be called on the top-level part.

        @param message: a L{exmess.Message}.
        """
        # XXX: we expect our 'source' attribute to be set, since it is set by
        # the delivery code below before the part is handed over to the Message
        # object for processing... this is kind of ugly.

        self._addToStore(message.store, message, self.source)

    # implementation of IMessageIterator

    def getContentType(self, default='text/plain'):
        try:
            value = self.getHeader(u'content-type')
        except equotient.NoSuchHeader:
            return default

        ctype = value.split(';', 1)[0].lower().strip().encode('ascii')
        if ctype.count('/') != 1:
            return default
        return ctype

    def getParam(self, param, default=None, header=u'content-type', un_quote=True):
        try:
            h = self.getHeader(header)
        except equotient.NoSuchHeader:
            return default
        param = param.lower()
        for pair in [x.split('=', 1) for x in h.split(';')[1:]]:
            if pair[0].strip().lower() == param:
                r = len(pair) == 2 and pair[1].strip() or ''
                if un_quote:
                    return mimepart.unquote(r)
                return r
        return default

    def getContentTransferEncoding(self, default=None):
        """
        @returns: string like 'base64', 'quoted-printable' or '7bit'
        """
        try:
            ctran = self.getHeader(u'content-transfer-encoding')
        except equotient.NoSuchHeader:
            return default

        if ctran:
            ct = ctran.lower().strip()
            return ct
        return default

    def getBody(self, decode=False):
        f = self.source.open()
        offt = self.bodyOffset
        leng = self.bodyLength
        f.seek(offt)
        data = f.read(leng)
        if decode:
            ct = self.getContentTransferEncoding()
            if ct == 'quoted-printable':
                return quopri.decodestring(data)
            elif ct == 'base64':
                for extraPadding in ('', '=', '=='):
                    try:
                        return (data + extraPadding).decode('base64')
                    except binascii.Error:
                        pass
                return data
            elif ct == '7bit':
                return data
        return data

    def getUnicodeBody(self, default='utf-8'):
        """Get the payload of this part as a unicode object."""
        charset = self.getParam('charset', default=default)
        payload = self.getBody(decode=True)

        try:
            return unicode(payload, charset, 'replace')
        except LookupError:
            return unicode(payload, default, 'replace')

    def getTypedParts(self, *types):
        for part in self.walk():
            if part.getContentType() in types:
                yield part

    def walkMessage(self, prefer): # XXX RENAME ME
        """
        Return an iterator of Paragraph, Extract, and Embedded instances for
        this part of the message.
        """
        ctype = self.getContentType()
        if ctype.startswith('multipart'):
            args = (prefer,)
        else:
            args = ()

        methodName = 'iterate_'+ctype.replace('/', '_')
        method = getattr(self, methodName, self.iterateUnhandled)
        return method(*args)


    def getAttachment(self, partID):
        for part in self.walkAttachments():
            if part.identifier == partID:
                return part

    def walkAttachments(self):
        """
        Collect all the subparts of this part regarded as attachments
        (i.e., all non-text parts, or parts whose content disposition
        is"attachment").
        """
        for part in self.walk():
            try:
                disposition = part.getHeader(u'content-disposition')
            except equotient.NoSuchHeader:
                disposition = ''

            ctyp = part.getContentType()
            if (not (ctyp.startswith('text')
                     or ctyp.startswith('multipart'))
                or disposition.startswith('attachment')):

                fname = part.getParam('filename', header=u'content-disposition')
                yield mimepart.AttachmentPart(self.message.storeID,
                                              part.partID, ctyp,
                                              disposition=disposition,
                                              filename=fname,
                                              part=part)


    def iterateUnhandled(self, prefer=None):
        """
        If there is no handler for this part, render it either as multipart/mixed
        (if it is multipart) or as application/octet-stream (if it is not).

        See RFC 2046, Section 4 and Section 5.1.3 for more details.
        """
        if self.getContentType().startswith('multipart'):
            contentType = 'multipart/mixed'
        else:
            contentType = 'application/octet-stream'
        yield mimepart.Part(self.message.storeID, self.partID, contentType,
                            part=self)


    def iterate_text_plain(self):
        content = self.getUnicodeBody()

        if self.getParam('format') == 'flowed':
            pfactory = mimepart.FlowedParagraph.fromRFC2646
        else:
            pfactory = mimepart.FixedParagraph.fromString

        paragraph = pfactory(content)

        yield mimepart.Part(self.message.storeID, self.partID,
                            self.getContentType(), children=[paragraph],
                            part=self)

    def iterate_text_html(self):
        yield mimepart.HTMLPart(self.message.storeID, self.partID,
                                self.getContentType(),
                                part=self)


    def readableParts(self, shallow=False):
        '''return all parts with a content type of text/*'''
        return (part for part in self.walk(shallow=shallow) if part.isReadable())

    def readablePart(self, prefer, shallow=False):
        '''return one text/* part, preferably of type prefer.  or None'''
        parts = list(self.readableParts(shallow=shallow))
        if len(parts) == 0:
            return None
        for part in parts:
            if part.getContentType() == prefer:
                return part
        return parts[0]

    def iterate_multipart_alternative(self, prefer):
        # the previous implementation of this method returned the first
        # text/* part at any level below the current part.  that was a
        # problem because it bypassed the logic of any intermediate
        # multiparts.  e.g. it would do the wrong this for this (unrealistic)
        # example part layout:
        #
        # multipart/alternative:
        #     multipart/related:
        #         text/plain
        #         text/plain
        #     multipart/related:
        #         text/html
        #         text/html
        #
        # it would have picked the first text/plain child inside the first
        # multipart/related, without displaying the second one.
        #
        # this is explicit as possible to avoid further confusion:

        # find all immediate children
        parts = list(self.walk(shallow=True))
        # go through each of them
        for part in parts:
            # stop if we find one with a content-type that matches
            # the "prefer" argument
            if part.getContentType() == prefer:
                break
        # we didn't find one
        else:
            # go through them again
            for part in parts:
                # stop if we find a readable/renderable one
                if part.isReadable():
                    break
            # we didn't find one
            else:
                # go through them again
                for part in parts:
                    # stop if we find a multipart
                    if part.isMultipart():
                        break
                # we didn't find one
                else:
                    # there is no renderable or readable component
                    # to this message, at any level
                    return

        # delegate to whichever part we found
        for child in part.walkMessage(prefer):
            yield child

    def iterate_multipart_mixed(self, prefer):
        # the previous implementation of this method had a similar problem
        # to iterate_multipart_alternative, in that it would just return
        # all readable parts at any level below the current part with
        # considering the logic of any multiparts in between.

        # for each immediate child of this part
        for part in self.walk(shallow=True):
            # if the part is readable/renderable or is a multipart
            if part.isReadable() or part.isMultipart():
                # delegate the decision about what components to render
                for child in part.walkMessage(prefer):
                    yield child
    iterate_multipart_related = iterate_multipart_signed = iterate_multipart_mixed

    def isReadable(self):
        return self.getContentType() in ('text/plain', 'text/html')

    def isMultipart(self):
        return self.getContentType().startswith('multipart/')

    def getFilename(self, default='No-Name'):
        return self.getParam('filename',
                             default=default,
                             header=u'content-disposition')

    def relatedAddresses(self):
        """
        Implement L{IMessageData.relatedAddresses} by looking at relevant
        RFC2822 headers for sender and recipient addresses.
        """
        for header in (u'from', u'sender', u'reply-to'):
            try:
                v = self.getHeader(header)
            except equotient.NoSuchHeader:
                continue

            email = mimeutil.EmailAddress(v, mimeEncoded=False)
            yield (exmess.SENDER_RELATION, email)
            break

        for header, relationship in [
            (u'cc', exmess.COPY_RELATION),
            (u'to', exmess.RECIPIENT_RELATION),
            (u'bcc', exmess.BLIND_COPY_RELATION),
            (u'resent-to', exmess.RESENT_TO_RELATION),
            (u'resent-from', exmess.RESENT_FROM_RELATION)]:
            try:
                v = self.getHeader(header)
            except equotient.NoSuchHeader:
                pass
            else:
                for addressObject in mimeutil.parseEmailAddresses(v, mimeEncoded=False):
                    yield (relationship, addressObject)


    def guessSentTime(self, default=None):
        """
        Try to determine the time this message claims to have been sent by
        analyzing various headers.

        @return: a L{Time} instance, or C{None}, if we don't have a guess.
        """

        try:
            sentHeader = self.getHeader(u'date')
        except equotient.NoSuchHeader:
            sentHeader = None
        else:
            try:
                return Time.fromRFC2822(sentHeader)
            except ValueError:
                pass

        for received in list(self.getHeaders(u'received'))[::-1]:
            lines = received.value.splitlines()
            if lines:
                lastLine = lines[-1]
                parts = lastLine.split('; ')
                if parts:
                    date = parts[-1]
                    try:
                        when = rfc822.parsedate(date)
                        if when is None:
                            continue
                    except ValueError:
                        pass
                    else:
                        return Time.fromStructTime(when)

        return default


    def getAllReplyAddresses(self):
        """
        Figure out the address(es) that a reply to all people involved this
        message should go to

        @return: Mapping of header names to sequences of
        L{xquotient.mimeutil.EmailAddress} instances.  Keys are 'to', 'cc' and
        'bcc'.
        @rtype: C{dict}
        """
        fromAddrs = list(self.store.query(smtpout.FromAddress))
        fromAddrs = set(a.address for a in fromAddrs)

        relToKey = {exmess.SENDER_RELATION: 'to',
                    exmess.RECIPIENT_RELATION: 'to',
                    exmess.COPY_RELATION: 'cc',
                    exmess.BLIND_COPY_RELATION: 'bcc'}
        addrs = {}

        for (rel, addr) in self.relatedAddresses():
            if rel not in relToKey or addr.email in fromAddrs:
                continue
            addrs.setdefault(relToKey[rel], []).append(addr)
        return addrs


    def getReplyAddresses(self):
        """
        Figure out the address(es) that a reply to this message should be sent
        to.

        @rtype: sequence of L{xquotient.mimeutil.EmailAddress}
        """
        try:
            recipient = self.getHeader(u'reply-to')
        except equotient.NoSuchHeader:
            recipient = dict(self.relatedAddresses())[
                exmess.SENDER_RELATION].email
        return mimeutil.parseEmailAddresses(recipient, mimeEncoded=False)


    def getAlternates(self):
        """
        If any exist, return the alternate versions of this part body.

        @return: a sequence of pairs, the first element holding the MIME type,
        the second a L{Part}
        """
        if (self.parent is not None and
                self.parent.getContentType() == 'multipart/alternative'):
            siblings = self.parent.walk(shallow=True)
            for sibling in siblings:
                if sibling is self:
                    continue
                yield (sibling.getContentType(), sibling)


class _MIMEMessageStorerBase(mimepart.MIMEMessageReceiver):
    """
    Base class for different kinds of persistent MIME parser classes.
    """
    def __init__(self, store, fObj, source):
        partCounter = itertools.count().next
        super(_MIMEMessageStorerBase, self).__init__(
            fObj,
            lambda *a, **kw: Part(_partCounter=partCounter,
                                  partID=partCounter(),
                                  *a,
                                  **kw))
        self.store = store
        self.source = source


    def messageDone(self):
        result = super(_MIMEMessageStorerBase, self).messageDone()
        self.part.source = self.file.finalpath
        log.msg(interface=iaxiom.IStatEvent, stat_messagesReceived=1,
                userstore=self.store)
        return result


    def setMessageAttributes(self):
        """
        Assign some values to some attributes of the created Message object.
        """
        ##### XXX XXX XXX this should really be stuff that Message does but the
        ##### ambiguity of the purpose of the 'recipients' field makes me
        ##### reluctant to remove it until there is some better coverage for
        ##### that.  -glyph
        try:
            to = self.part.getHeader(u'to')
        except equotient.NoSuchHeader:
            self.message.recipient = u'<No Recipient>'
        else:
            self.message.recipient = to

        try:
            subject = self.part.getHeader(u'subject')
        except equotient.NoSuchHeader:
            self.message.subject = u'<No Subject>'
        else:
            self.message.subject = subject



class DraftMIMEMessageStorer(_MIMEMessageStorerBase):
    """
    Persistent MIME parser/storage class for draft messages.
    """
    def messageDone(self):
        """
        Create a draft Message and associate the Part with it.
        """
        result = super(DraftMIMEMessageStorer, self).messageDone()
        self.message = exmess.Message.createDraft(
            self.store, self.part, self.source)
        self.setMessageAttributes()
        return result
    messageDone = item.transacted(messageDone)



class IncomingMIMEMessageStorer(_MIMEMessageStorerBase):
    """
    Persistent MIME parser/storage class for messages received by the
    system from external entities.
    """
    def messageDone(self):
        """
        Create an Incoming message and associate the Part with it.
        """
        result = super(IncomingMIMEMessageStorer, self).messageDone()
        self.message = exmess.Message.createIncoming(
            self.store, self.part, self.source)
        self.setMessageAttributes()
        return result
    messageDone = item.transacted(messageDone)


class ExistingMessageMIMEStorer(_MIMEMessageStorerBase):
    """
    Persistent MIME parser/storage class which associates the created
    Part with an existing Message instance.
    """
    def __init__(self, store, fObj, source, message):
        super(ExistingMessageMIMEStorer, self).__init__(store, fObj, source)
        self.message = message


    def messageDone(self):
        """
        Associate the Part which resulted from parsing the message
        with the message which was passed to our initializer.
        """
        result = super(ExistingMessageMIMEStorer, self).messageDone()
        # XXX Should there be a public API for this?
        self.message._associateWithImplementation(self.part, self.source)
        self.setMessageAttributes()
        return result
