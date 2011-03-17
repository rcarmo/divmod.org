# -*- test-case-name: xquotient.test.test_compose -*-
from email import (Parser as P, Generator as G, MIMEMultipart as MMP,
                   MIMEText as MT, MIMEMessage as MM, Header as MH,
                   Utils as EU)

import StringIO as S

from zope.interface import implements

from twisted.python.components import registerAdapter
from twisted.mail import smtp

from nevow import inevow, rend, json
from nevow.athena import expose

from axiom import attributes, item
from axiom.upgrade import (
    registerUpgrader, registerAttributeCopyingUpgrader,
    registerDeletionUpgrader)
from axiom.dependency import dependsOn

from xmantissa.fragmentutils import dictFillSlots
from xmantissa import webnav, ixmantissa, people, liveform, prefs
from xmantissa.webapp import PrivateApplication
from xmantissa.webtheme import getLoader

from xquotient import iquotient, equotient, renderers, mimeutil

from smtpout import (FromAddress, MessageDelivery,
                     _getFromAddressFromStore, FromAddressConfigFragment)

from xquotient.exmess import ActionlessMessageDetail, REDIRECTED_STATUS
from xquotient.mail import MailDeliveryAgent, DeliveryAgent
from xquotient.mimebakery import saveDraft, sendMail

class ComposePreferenceCollection(item.Item, prefs.PreferenceCollectionMixin):
    """
    L{xmantissa.ixmantissa.IPreferenceCollection} which collects preferences
    that have something to do with compose or outgoing mail
    """
    implements(ixmantissa.IPreferenceCollection)

    schemaVersion = 3

    installedOn = attributes.reference()
    powerupInterfaces = (ixmantissa.IPreferenceCollection,)

    def getPreferenceParameters(self):
        return None

    def getSections(self):
        return (FromAddressConfigFragment(self),)

    def getTabs(self):
        return (webnav.Tab('Mail', self.storeID, 0.0, children=(
                    webnav.Tab('Outgoing', self.storeID, 0.0),),
                    authoritative=False),)



class Drafts(item.Item):
    """
    Shell of an item that exists only to be deleted. The 'Drafts' menu item is
    no longer. Instead, drafts are accessed through a mail view.
    """

    typeName = 'quotient_drafts'
    schemaVersion = 2

    installedOn = attributes.reference()



def drafts1to2(old):
    """
    Delete the Drafts item. It is now superfluous.
    """
    new = old.upgradeVersion(old.typeName, 1, 2, installedOn=None)
    new.deleteFromStore()


registerUpgrader(drafts1to2, Drafts.typeName, 1, 2)



class File(item.Item):
    typeName = 'quotient_file'
    schemaVersion = 1

    type = attributes.text(allowNone=False)
    body = attributes.path(allowNone=False)
    name = attributes.text(allowNone=False)

    message = attributes.reference()
    cabinet = attributes.reference(allowNone=False)

class FileCabinet(item.Item):
    typeName = 'quotient_file_cabinet'
    schemaVersion = 1

    name = attributes.text()
    filesCount = attributes.integer(default=0)

    def createFileItem(self, name, type, data):
        """
        @param name: file name
        @param type: content-type
        @param data: file contents

        @return: C{File} item
        """
        outf = self.store.newFile('cabinet-'+str(self.storeID),
                                  str(self.filesCount))
        outf.write(data)
        outf.close()

        f = File(store=self.store,
                 body=outf.finalpath,
                 name=name,
                 type=type,
                 cabinet=self)

        self.filesCount += 1
        return f

class FileCabinetPage(rend.Page):
    lastFile = None

    def __init__(self, original):
        rend.Page.__init__(self, original, docFactory=getLoader('file-upload'))

    def renderHTTP(self, ctx):
        req = inevow.IRequest(ctx)
        if req.method == 'POST':
            uploadedFileArg = req.fields['uploaddata']
            def txn():
                self.lastFile = self.original.createFileItem(
                                        name=unicode(uploadedFileArg.filename),
                                        type=unicode(uploadedFileArg.type),
                                        data=uploadedFileArg.file.read())
            self.original.store.transact(txn)

        return rend.Page.renderHTTP(self, ctx)

    def render_lastFileData(self, ctx, data):
        if self.lastFile is None:
            return ''
        return json.serialize({u'id': self.lastFile.storeID,
                               u'name': self.lastFile.name})

registerAdapter(FileCabinetPage, FileCabinet, inevow.IResource)



class Composer(item.Item):
    implements(ixmantissa.INavigableElement, iquotient.IMessageSender)

    typeName = 'quotient_composer'
    schemaVersion = 6

    powerupInterfaces = (ixmantissa.INavigableElement, iquotient.IMessageSender)

    privateApplication = dependsOn(PrivateApplication)
    mda = dependsOn(MailDeliveryAgent)
    deliveryAgent = dependsOn(DeliveryAgent)
    prefs = dependsOn(ComposePreferenceCollection)

    def installed(self):
        defaultFrom = self.store.findOrCreate(FromAddress, _address=None)
        defaultFrom.setAsDefault()

    def getTabs(self):
        return [webnav.Tab('Mail', self.storeID, 0.6, children=
                    [webnav.Tab('Compose', self.storeID, 0.1)],
                authoritative=False)]


    def sendMessage(self, fromAddress, toAddresses, msg):
        """
        Send a message from this composer.

        @param toAddresses: List of email addresses (Which can be
            coerced to L{smtp.Address}es).
        @param msg: The L{exmess.Message} to send.
        """
        m = MessageDelivery(composer=self, message=msg,
                                    store=self.store)
        m.send(fromAddress, toAddresses)


    def _createBounceMessage(self, log, toAddress, msg):
        """
        Create a multipart MIME message that will be sent to the user to indicate
        that their message has bounced.

        @param log: ???
        @param toAddress: The email address that bounced
        @param msg: The message that bounced

        @return: L{MP.MIMEMultipart}
        """
        bounceText = (
            'Your message to %(recipient)s, subject "%(subject)s", '
            'could not be delivered.')
        bounceText %= {
            'recipient': toAddress,
            'subject': msg.impl.getHeader(u'subject')}

        original = P.Parser().parse(msg.impl.source.open())

        m = MMP.MIMEMultipart(
            'mixed',
            None,
            [MT.MIMEText(bounceText, 'plain'),
             MT.MIMEText(log, 'plain'),
             MM.MIMEMessage(original)])

        m['Subject'] = 'Unable to deliver message to ' + toAddress
        m['From'] = '<>'
        m['To'] = ''
        return m


    def _sendBounceMessage(self, m):
        """
        Insert the given MIME message into the inbox for this user.

        @param m: L{MMP.MIMEMultipart}
        """
        s = S.StringIO()
        G.Generator(s).flatten(m)
        s.seek(0)
        self.createMessageAndQueueIt(
            FromAddress.findDefault(self.store).address, s, False)


    def messageBounced(self, log, toAddress, msg):
        m = self._createBounceMessage(log, toAddress, msg)
        self._sendBounceMessage(m)


    def createMessageAndQueueIt(self, fromAddress, s, draft):
        """
        Create a message out of C{s}, from C{fromAddress}

        @param fromAddress: address from which to send the email
        @type fromAddress: C{unicode}
        @param s: message to send
        @type s: line iterable
        @type draft: C{bool}
        @param draft: Flag indicating whether this is a draft message or not
        (eg, a bounce message).

        @rtype: L{xquotient.exmess.Message}
        """
        def deliverMIMEMessage():
            md = iquotient.IMIMEDelivery(self.store)
            if draft:
                mr = md._createMIMEDraftReceiver('sent://' + fromAddress)
            else:
                mr = md.createMIMEReceiver('sent://' + fromAddress)
            for L in s:
                mr.lineReceived(L.rstrip('\n'))
            mr.messageDone()
            return mr.message
        return self.store.transact(deliverMIMEMessage)


    def updateDraftMessage(self, fromAddress, messageFile, message):
        """
        Change the IMessageData associated with the given message to a
        L{mimestorage.Part} created by parsing C{messageFile}.

        @type fromAddress: C{unicode}
        @param fromAddress: RFC 2821 address from which to send the email

        @param messageFile: an iterable of lines from the new MIME message

        @param message: The existing L{exmess.Message} with which to
        associate the new IMessageData.
        """
        md = iquotient.IMIMEDelivery(self.store)
        mr = md._createDraftUpdateReceiver(message, 'sent://' + fromAddress)
        for L in messageFile:
            mr.lineReceived(L.strip('\n'))
        mr.messageDone()
        return None
    updateDraftMessage = item.transacted(updateDraftMessage)


    def createRedirectedMessage(self, fromAddress, toAddresses, message):
        """
        Create a L{Message} item based on C{message}, with the C{Resent-From}
        and C{Resent-To} headers set

        @type fromAddress: L{smtpout.FromAddress}

        @type toAddresses: sequence of L{mimeutil.EmailAddress}

        @type message: L{Message}

        @rtype: L{Message}
        """
        m = P.Parser().parse(message.impl.source.open())
        def insertResentHeaders(i):
            m._headers.insert(i, ('resent-from', MH.Header(
                fromAddress.address).encode()))
            m._headers.insert(i, ('resent-to', MH.Header(
                mimeutil.flattenEmailAddresses(toAddresses)).encode()))
            m._headers.insert(i, ('resent-date', EU.formatdate()))
            m._headers.insert(i, ('resent-message-id',
                                  smtp.messageid('divmod.xquotient')))
        for (i, (name, _)) in enumerate(m._headers):
            #insert Resent-* headers after all Received headers but
            #before the rest
            if name.lower() != "received":
                insertResentHeaders(i)
                break
        else:
            insertResentHeaders(0)
        s = S.StringIO()
        G.Generator(s).flatten(m)
        s.seek(0)

        return self.createMessageAndQueueIt(fromAddress.address, s, True)


    def redirect(self, fromAddress, toAddresses, message):
        """
        Redirect C{message} from C{fromAddress} to C{toAddresses}.
        Parameters the same as for L{createRedirectedMessage}

        @rtype: C{None}
        """
        msg = self.createRedirectedMessage(fromAddress, toAddresses, message)
        addresses = [addr.email for addr in toAddresses]
        self.sendMessage(fromAddress, addresses, msg)
        message.addStatus(REDIRECTED_STATUS)

def upgradeCompose1to2(oldComposer):
    """
    Version 2 of the Composer powers up IMessageSender, which version 1 did
    not.  Correct that here.
    """
    newComposer = oldComposer.upgradeVersion(
        'quotient_composer', 1, 2,
        installedOn=oldComposer.installedOn)
    newComposer.installedOn.powerUp(
        newComposer, iquotient.IMessageSender)
    return newComposer

registerUpgrader(upgradeCompose1to2, 'quotient_composer', 1, 2)

item.declareLegacyItem(Composer.typeName, 2,
                       dict(installedOn=attributes.reference()))

def composer2to3(old):
    """
    Remove the L{Composer.fromAddress} attribute
    """
    return old.upgradeVersion(old.typeName, 2, 3,
                              installedOn=old.installedOn)

registerUpgrader(composer2to3, Composer.typeName, 2, 3)

item.declareLegacyItem(Composer.typeName, 3,
                       dict(installedOn=attributes.reference()))



def composer3to4(old):
    """
    add dependencies as attributes, remove installedOn
    """
    composer = old.upgradeVersion(old.typeName, 3, 4)
    s = old.store
    composer.privateApplication = s.findOrCreate(PrivateApplication)
    composer.mda = s.findOrCreate(MailDeliveryAgent)
    composer.deliveryAgent = s.findOrCreate(DeliveryAgent)
    composer.prefs = s.findOrCreate(ComposePreferenceCollection)
    composer.drafts = s.findOrCreate(Drafts)
    return composer


registerUpgrader(composer3to4, Composer.typeName, 3, 4)
item.declareLegacyItem(Composer.typeName, 4,
                       dict(privateApplication=attributes.reference(),
                            scheduler=attributes.reference(),
                            mda=attributes.reference(),
                            deliveryAgent=attributes.reference(),
                            prefs=attributes.reference(),
                            drafts=attributes.reference()))



def composer4to5(old):
    """
    Upgrader to remove the 'drafts' attribute.
    """
    return old.upgradeVersion(
        old.typeName, 4, 5,
        privateApplication=old.privateApplication,
        mda=old.mda,
        deliveryAgent=old.deliveryAgent,
        prefs=old.prefs)


registerUpgrader(composer4to5, Composer.typeName, 4, 5)

item.declareLegacyItem(Composer.typeName, 5,
                       dict(privateApplication=attributes.reference(),
                            scheduler=attributes.reference(),
                            mda=attributes.reference(),
                            deliveryAgent=attributes.reference(),
                            prefs=attributes.reference()))

def composer5to6(old):
    """
    Upgrader to remove the C{scheduler} attribute.
    """
    return old.upgradeVersion(
        old.typeName, 5, 6,
        privateApplication=old.privateApplication,
        mda=old.mda,
        deliveryAgent=old.deliveryAgent,
        prefs=old.prefs)

registerUpgrader(composer5to6, Composer.typeName, 5, 6)


class _ComposeFragmentMixin:
    """
    Mixin which provides some stuff that might be useful to fragments which do
    composey things.

    Assumes it is mixed-in to something where C{self.composer} is a
    L{Composer}
    """

    def _coerceEmailAddressString(self, s):
        """
        Turn a string representation of one or more email addresses into a
        list of L{mimetuil.EmailAddress} instances

        @param s: non mime-encoded string
        @type s: C{str}

        @return: L{mimeutil.EmailAddress} instances
        @rtype: sequence
        """
        return mimeutil.parseEmailAddresses(s, mimeEncoded=False)


    def _getFromAddresses(self):
        """
        Return a list of L{FromAddress} instances, in order of preference.
        """
        fromAddrs = []
        for fromAddress in self.composer.store.query(FromAddress):
            if fromAddress._default:
                fromAddrs.insert(0, fromAddress)
            else:
                fromAddrs.append(fromAddress)
        return fromAddrs


    def _formatFromAddressSelection(self, fromAddresses):
        """
        Turn the given L{smtpout.FromAddress} items into some stan,
        using the C{from-select} and C{from-select-option} patterns
        from the template
        """
        iq = inevow.IQ(self.docFactory)
        return iq.onePattern('from-select').fillSlots(
                        'options', [iq.onePattern(
                                    'from-select-option').fillSlots(
                                        'address', addr.address).fillSlots(
                                        'value', self.translator.toWebID(addr))
                                        for addr in fromAddresses])


    def getPeople(self):
        """
        @return: a sequence of pairs (name, email) for each Person in the
        store of my L{Composer}, where name is the person's display name, and
        email is their email address.  omits people without a display name or
        email address
        """
        peeps = []
        for person in self.composer.store.query(people.Person):
            email = person.getEmailAddress()
            if email is None:
                email = u''
            name = person.getDisplayName()
            if name or email:
                peeps.append((name, email))
        return peeps
    expose(getPeople)


class ComposeFragment(liveform.LiveFormFragment, renderers.ButtonRenderingMixin, _ComposeFragmentMixin):
    implements(ixmantissa.INavigableFragment)

    jsClass = u'Quotient.Compose.Controller'
    fragmentName = 'compose'

    def __init__(self, composer, recipients=None, subject=u'', messageBody=u'',
                 attachments=(), inline=False, parentMessage=None,
                 parentAction=None):
        """
        @type composer: L{Composer}

        @param recipients: email addresses of the recipients of this message.
        defaults to no recipients
        @type recipients: C{dict} which can contain any combination of the
        keys C{to}, C{cc} and C{bcc}, where the values are sequences of
        L{xquotient.mimeutil.EmailAddress} instances

        @param subject: the subject of this message
        @type subject: C{unicode}

        @param messageBody: the body of this message
        @type messageBody: C{unicode}

        @param attachments: the attachments of this message
        @type attachments: sequence of L{xquotient.mimepart.AttachmentPart}
        instances

        @param inline: whether the compose widget is being displayed inline,
        e.g. as a child of another widget
        @type inline: boolean

        @param parentMessage: The existing message this message is in
        response to, if any; otherwise None.

        @param parentAction: The status that should be set on the
        parent message, if any, once this message is delivered. Should
        be a value from L{xquotient.exmess} that ends in C{_STATUS}.

        C{toAddresses}, C{subject}, C{messageBody} and C{attachments} should
        be considered as presets - their values can be manipulated via the
        user interface
        """
        self.composer = composer
        self.cabinet = self.composer.store.findOrCreate(FileCabinet)
        self.translator = ixmantissa.IWebTranslator(composer.store)
        self._savedDraft = None
        super(ComposeFragment, self).__init__(
            callable=self._sendOrSave,
            parameters=[liveform.Parameter(name='fromAddress',
                                           type=liveform.TEXT_INPUT,
                                           coercer=self.translator.fromWebID),
                        liveform.Parameter(name='toAddresses',
                                           type=liveform.TEXT_INPUT,
                                           coercer=self._coerceEmailAddressString),
                        liveform.Parameter(name='subject',
                                           type=liveform.TEXT_INPUT,
                                           coercer=unicode),
                        liveform.Parameter(name='messageBody',
                                           type=liveform.TEXTAREA_INPUT,
                                           coercer=unicode),
                        liveform.Parameter(name='cc',
                                           type=liveform.TEXT_INPUT,
                                           coercer=self._coerceEmailAddressString),
                        liveform.Parameter(name='bcc',
                                           type=liveform.TEXT_INPUT,
                                           coercer=self._coerceEmailAddressString),
                        liveform.Parameter(name='draft',
                                           type=liveform.CHECKBOX_INPUT,
                                           coercer=bool)])
        if recipients is None:
            recipients = {}
        self.recipients = recipients
        self.subject = subject
        self.messageBody = messageBody
        self.attachments = attachments
        self.fileAttachments = []
        self.inline = inline

        self.docFactory = None
        self.parentMessage = parentMessage
        self.parentAction = parentAction

    def invoke(self, formPostEmulator):
        """
        Send the message or save it as a draft.

        The base implementation is overridden to support the slightly
        unusual I{files} parameter.  LiveForm has no support for this weird
        list of previously uploaded files type of data.
        """
        coerced = self.fromInputs(formPostEmulator)
        def cbCoerced(values):
            # we want to allow the javascript to submit an
            # list of filenames of arbitrary length with the form
            values['files'] = formPostEmulator.get('files', ())
            return self.callable(**values)
        return coerced.addCallback(cbCoerced)
    expose(invoke)


    def _sendOrSave(self, fromAddress, toAddresses, subject, messageBody,
                    cc, bcc, files, draft):
        """
        This method is called interactively from the browser via a liveform in
        response to clicking 'send' or 'save draft'.

        @param fromAddress: a L{smtpout.FromAddress} item.

        @param toAddresses: a list of L{mimeutil.EmailAddress} objects,
        representing the people to send this to.

        @param subject: freeform string
        @type subject: L{unicode}

        @param messageBody: the message's body, a freeform string.
        @type messageBody: L{unicode}

        @param cc: a string, likely an rfc2822-formatted list of addresses
        (not validated between the client and here, XXX FIXME)
        @type cc: L{unicode}

        @param bcc: a string, likely an rfc2822-formatted list of addresses
        (not validated between the client and here, XXX FIXME)
        @type bcc: L{unicode}

        @param files: a sequence of stringified storeIDs which should point at
        L{File} items.

        @param draft: a boolean, indicating whether the message represented by
        the other arguments to this function should be saved as a draft or sent
        as an outgoing message.  True for save, False for send.
        """
        if draft:
            f = saveDraft
        else:
            f = sendMail
        self._savedDraft = f(self._savedDraft, self.composer,
                             self.cabinet, self.parentMessage,
                             self.parentAction,
                             fromAddress, toAddresses,
                             subject, messageBody, cc, bcc, files)


    def getInitialArguments(self):
        return (self.inline, self.getPeople())

    def render_attachButton(self, ctx, data):
        return inevow.IQ(self.docFactory).onePattern('attach-button')

    def render_inboxLink(self, ctx, data):
        #XXX circular dependency
        from xquotient.inbox import Inbox
        return self.translator.linkTo(self.composer.store.findUnique(Inbox).storeID)


    def slotData(self):
        """
        @return: a C{dict} of data to be used to fill slots during
        rendering.  The keys in this dictionary will be::

            C{'to'}: a C{unicode} string giving a comma-delimited list
                     of addresses to which this message is directly
                     addressed.

            C{'from'}: a C{list} of C{FromAddress} instances giving
                       the possible values for the from address for
                       this message.

            C{'subject'}: the subject of this message.

            C{'message-body'}: a C{unicode} string giving the body of
                               this message.

            C{'cc'}: a C{unicode} string giving a comma-delimited list
                     of address to which this message is indirectly
                     addressed.

            C{'bcc'}: a C{unicode} string giving a comma-delimited
                      list of addresses to which this message is
                      secretly addressed.

            C{'attachments'}: a C{list} of C{dict} which the keys
                              C{'id'} and C{'name'} giving storeIDs
                              and filenames for the attachments of
                              this message.
        """
        attachments = []
        for a in self.attachments:
            attachments.append(dict(id=a.part.storeID, name=a.filename))
        addrs = {}
        for k in ('to', 'cc', 'bcc'):
            if k in self.recipients:
                # XXX This is mis-factored.  The calling code should
                # be flattening this, if it wants it flattened.
                addrs[k] = mimeutil.flattenEmailAddresses(
                    self.recipients[k])
            else:
                addrs[k] = ''

        return {'to': addrs['to'],
                'from': self._getFromAddresses(),
                'subject': self.subject,
                'message-body': self.messageBody,
                'cc': addrs['cc'],
                'bcc': addrs['bcc'],
                'attachments': attachments}


    def render_compose(self, ctx, data):
        iq = inevow.IQ(self.docFactory)
        bodyPattern = iq.onePattern('message-body')
        subjectPattern = iq.onePattern('subject')
        attachmentPattern = iq.patternGenerator('attachment')

        slotData = self.slotData()
        slotData['from'] = self._formatFromAddressSelection(slotData['from'])
        slotData['subject'] = subjectPattern.fillSlots('subject', slotData['subject'])
        slotData['message-body'] = bodyPattern.fillSlots('body', slotData['message-body'])
        slotData['attachments'] = [
            attachmentPattern.fillSlots('id', d['id']).fillSlots('name', d['name'] or 'No Name')
            for d
            in slotData['attachments']]

        return dictFillSlots(ctx.tag, slotData)


    def render_fileCabinet(self, ctx, data):
        return inevow.IQ(self.docFactory).onePattern('cabinet-iframe').fillSlots(
                    'src', ixmantissa.IWebTranslator(self.cabinet.store).linkTo(self.cabinet.storeID))

    def head(self):
        return None


registerAdapter(ComposeFragment, Composer, ixmantissa.INavigableFragment)


class DraftComposeFragment(ComposeFragment):
    """
    Composition UI initialized from a draft.
    """
    def __init__(self, composer, draft):
        ComposeFragment.__init__(self, composer)
        self._savedDraft = draft

    def slotData(self):
        """
        @see ComposeFragment.slotData
        """
        message = self._savedDraft

        attachments = []

        # i think this will suffice until we have a rich text compose
        (txt,) = list(message.impl.getTypedParts('text/plain'))
        try:
            cc = message.impl.getHeader(u'cc')
        except equotient.NoSuchHeader:
            cc = u''

        for f in message.store.query(File, File.message == message):
            attachments.append(dict(id=f.storeID, name=f.name))

        return {
            'to': message.recipient,
            # XXX WRONG - we have to save from address information somewhere
            'from': self._getFromAddresses(),
            'subject': message.subject,
            'message-body': txt.getBody(decode=True),
            'cc': cc,
            # XXX WRONG - we have to save bcc information somewhere
            'bcc': u'',
            'attachments': attachments}



class RedirectingComposeFragment(liveform.LiveFormFragment, renderers.ButtonRenderingMixin, _ComposeFragmentMixin):
    """
    A fragment which provides UI for redirecting email messages
    """
    implements(ixmantissa.INavigableFragment)

    jsClass = u'Quotient.Compose.RedirectingController'
    fragmentName = 'compose'

    def __init__(self, composer, message):
        """
        @type composer: L{Composer}

        @param message: the message being redirected
        @type message: L{Message}
        """
        self.composer = composer
        self.message = message

        self.translator = ixmantissa.IWebTranslator(composer.store)

        super(RedirectingComposeFragment, self).__init__(
            callable=self.redirect,
            parameters=(liveform.Parameter(name='fromAddress',
                                           type=liveform.TEXT_INPUT,
                                           coercer=self.translator.fromWebID),
                        liveform.Parameter(name='toAddresses',
                                           type=liveform.TEXT_INPUT,
                                           coercer=self._coerceEmailAddressString)))


    def render_attachButton(self, ctx, data):
        """
        The template contains an "attachButton" render directive.  Return the
        empty string, as we don't want an attach button for redirected
        messages
        """
        return ''


    def _getMessageBody(self):
        """
        Get a widget which will be used to render the body of the message
        we're redirecting

        @rtype: L{ActionlessMessageDetail}
        """
        f = ActionlessMessageDetail(self.message)
        f.setFragmentParent(self)
        f.docFactory = getLoader(f.fragmentName)
        return f


    def render_compose(self, ctx, data):
        """
        Only fill in the C{from} and C{message-body} slots with anything
        useful - the stuff that L{ComposeFragment} puts in the rest of slots
        will be apparent from the L{MessageDetail} fragment we put in
        C{message-body}
        """
        return dictFillSlots(ctx.tag,
                {'to': '',
                 'from': self._formatFromAddressSelection(self._getFromAddresses()),
                 'subject': '',
                 'message-body': self._getMessageBody(),
                 'cc': '',
                 'bcc': '',
                 'attachments': ''})


    def getInitialArguments(self):
        return (self.getPeople(),)


    def redirect(self, fromAddress, toAddresses):
        """
        Ask L{Composer} to redirect C{self.message}

        @param fromAddress: the address to send from
        @type fromAddress: L{smtpout.FromAddress}

        @param toAddresses: L{mimeutil.EmailAddress} instances
        @type toAddresses: sequence
        """
        self.composer.redirect(fromAddress, toAddresses, self.message)


class ComposeBenefactor(item.Item):
    endowed = attributes.integer(default=0)
    powerupNames = ["xquotient.compose.Composer"]

registerAttributeCopyingUpgrader(ComposePreferenceCollection, 1, 2)

item.declareLegacyItem(ComposePreferenceCollection.typeName, 2,
                       dict(installedOn=attributes.reference(),
                            preferredSmarthost=attributes.text(),
                            smarthostUsername=attributes.text(),
                            smarthostPassword=attributes.text(),
                            smarthostPort=attributes.integer(),
                            smarthostAddress=attributes.text()))

def composePreferenceCollection2to3(old):
    """
    Create an L{smtpout.FromAddress} out of the appropriate
    L{userbase.LoginMethod} in the store, using L{_getFromAddressFromStore}.
    This probably should happen in the L{Composer} 2->3 upgrader, but we also
    make an L{smtpout.FromAddress} item out the smarthost attributes of C{old}
    if they are set, and we need to do that after creating the initial
    L{smtpout.FromAddress}, so it gets set as the default.

    Copy C{old.installedOn} onto the new L{ComposePreferenceCollection}
    """
    baseFrom = FromAddress(
        store=old.store, address=_getFromAddressFromStore(old.store))

    if old.preferredSmarthost is not None:
        s = old.store
        smarthostFrom = FromAddress(store=s,
                                            address=old.smarthostAddress,
                                            smtpHost=old.preferredSmarthost,
                                            smtpPort=old.smarthostPort,
                                            smtpUsername=old.smarthostUsername,
                                            smtpPassword=old.smarthostPassword)
        smarthostFrom.setAsDefault()
    else:
        baseFrom.setAsDefault()

    return old.upgradeVersion(old.typeName, 2, 3,
                              installedOn=old.installedOn)

registerUpgrader(composePreferenceCollection2to3,
                 ComposePreferenceCollection.typeName,
                 2, 3)


class Draft(item.Item):
    """
    No longer used. Exists only for upgrade purposes.
    """

    typeName = 'quotient_draft'
    schemaVersion = 2

    empty = attributes.reference()

item.declareLegacyItem('quotient_draft', 1,
                       dict(message=attributes.reference(allowNone=False)))

registerDeletionUpgrader(Draft, 1, 2)
