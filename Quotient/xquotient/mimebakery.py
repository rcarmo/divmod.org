# -*- test-case-name: xquotient.test.test_compose -*-
"""
A collection of functions for getting mail from the UI into the
database and sent via SMTP.
"""
from email import (Parser as P, Generator as G, MIMEMultipart as MMP,
                   MIMEText as MT, MIMEBase as MB,
                   Header as MH, Charset as MC, Utils as EU, Encoders as EE)
import StringIO as S
from xquotient.mimestorage import Part
from xquotient.mimepart import FlowedParagraph
from twisted.mail import smtp

from xquotient import mimeutil


def _fileItemToEmailPart(fileItem):
    """
    Convert a L{File} item into an appropriate MIME part object
    understandable by the stdlib's C{email} package
    """
    (majorType, minorType) = fileItem.type.split('/')
    if majorType == 'multipart':
        part = P.Parser().parse(fileItem.body.open())
    else:
        part = MB.MIMEBase(majorType, minorType)
        if majorType == 'message':
            part.set_payload([P.Parser().parse(fileItem.body.open())])
        else:
            part.set_payload(fileItem.body.getContent())
            if majorType == 'text':
                EE.encode_quopri(part)
            else:
                EE.encode_base64(part)
    part.add_header('content-disposition', 'attachment', filename=fileItem.name)
    return part


def createMessage(composer, cabinet, msgRepliedTo, fromAddress,
                  toAddresses, subject, messageBody, cc, bcc, files,
                  createMessageObject=None):
    """
    Create an outgoing message, format the body into MIME parts, and
    populate its headers.

    @param createMessageObject: A one-argument callable which will be
    invoked with a file-like object containing MIME text and which
    should return a Message instance associated with objects
    representing that MIME data.
    """
    MC.add_charset('utf-8', None, MC.QP, 'utf-8')

    encode = lambda s: MH.Header(s).encode()

    s = S.StringIO()
    wrappedMsgBody = FlowedParagraph.fromRFC2646(messageBody).asRFC2646()
    m = MT.MIMEText(wrappedMsgBody, 'plain', 'utf-8')
    m.set_param("format", "flowed")

    fileItems = []
    if files:
        attachmentParts = []
        for storeID in files:
            a = composer.store.getItemByID(long(storeID))
            if isinstance(a, Part):
                a = cabinet.createFileItem(
                        a.getParam('filename',
                                   default=u'',
                                   header=u'content-disposition'),
                        unicode(a.getContentType()),
                        a.getBody(decode=True))
            fileItems.append(a)
            attachmentParts.append(
                _fileItemToEmailPart(a))

        m = MMP.MIMEMultipart('mixed', None, [m] + attachmentParts)

    m['From'] = encode(fromAddress.address)
    m['To'] = encode(mimeutil.flattenEmailAddresses(toAddresses))
    m['Subject'] = encode(subject)
    m['Date'] = EU.formatdate()
    m['Message-ID'] = smtp.messageid('divmod.xquotient')

    if cc:
        m['Cc'] = encode(mimeutil.flattenEmailAddresses(cc))
    if msgRepliedTo is not None:
        #our parser does not remove continuation whitespace, so to
        #avoid duplicating it --
        refs = [hdr.value for hdr in
                msgRepliedTo.impl.getHeaders("References")]
        if len(refs) == 0:
            irt = [hdr.value for hdr in
                   msgRepliedTo.impl.getHeaders("In-Reply-To")]
            if len(irt) == 1:
                refs = irt
            else:
                refs = []
        msgids = msgRepliedTo.impl.getHeaders("Message-ID")
        for hdr in msgids:
            msgid = hdr.value
            refs.append(msgid)
            #As far as I can tell, the email package doesn't handle
            #multiple values for headers automatically, so here's some
            #continuation whitespace.
            m['References'] = u'\n\t'.join(refs)
            m['In-Reply-To'] = msgid
            break
    G.Generator(s).flatten(m)
    s.seek(0)

    if createMessageObject is None:
        def createMessageObject(messageFile):
            return composer.createMessageAndQueueIt(
                fromAddress.address, messageFile, True)
    msg = createMessageObject(s)

    # there is probably a better way than this, but there
    # isn't a way to associate the same file item with multiple
    # messages anyway, so there isn't a need to reflect that here
    for fileItem in fileItems:
        fileItem.message = msg
    return msg


def sendMail(_savedDraft, composer, cabinet, parentMessage, parentAction,
             fromAddress, toAddresses, subject, messageBody, cc, bcc,
             files):
    """
    Construct and send a message over SMTP.
    """
    message = saveDraft(
        _savedDraft, composer, cabinet, parentMessage, parentAction,
        fromAddress, toAddresses, subject, messageBody, cc, bcc, files)

    addresses = [addr.pseudoFormat() for addr in toAddresses + cc + bcc]

    # except we are going to send this draft
    composer.sendMessage(fromAddress, addresses, message)

    if parentMessage is not None and parentAction is not None:
        parentMessage.addStatus(parentAction)



def saveDraft(_savedDraft, composer, cabinet, parentMessage, parentAction,
               fromAddress, toAddresses, subject, messageBody, cc,
               bcc, files):
    """
    Construct a message and save it in the database.

    @return: The Message which has been saved as a draft.
    """
    def updateMessageObject(messageFile):
        return composer.updateDraftMessage(
            fromAddress.address, messageFile, _savedDraft)

    # overwrite the previous draft of this message with another draft
    if _savedDraft is None:
        _savedDraft = createMessage(
            composer, cabinet, parentMessage, fromAddress,
            toAddresses, subject, messageBody, cc, bcc, files)
    else:
        createMessage(
            composer, cabinet, parentMessage, fromAddress,
            toAddresses, subject, messageBody, cc, bcc, files,
            updateMessageObject)
    return _savedDraft
