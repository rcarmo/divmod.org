# -*- test-case-name: xmantissa.test.test_signup,xmantissa.test.test_password_reset -*-

import os, rfc822, md5, time, random
from itertools import chain

from zope.interface import Interface, implements

from twisted.cred.portal import IRealm
from twisted.python.components import registerAdapter
from twisted.mail import smtp, relaymanager
from twisted.python.util import sibpath
from twisted.python import log
from twisted import plugin

from epsilon import extime

from axiom.item import Item, transacted, declareLegacyItem
from axiom.attributes import integer, reference, text, timestamp, AND
from axiom.iaxiom import IBeneficiary
from axiom import userbase, upgrade
from axiom.userbase import getDomainNames
from axiom.dependency import installOn

from nevow.rend import Page, NotFound
from nevow.url import URL
from nevow.inevow import IResource, ISession
from nevow import inevow, tags, athena
from nevow.athena import expose

from xmantissa.ixmantissa import (
    ISiteRootPlugin, IStaticShellContent, INavigableElement,
    INavigableFragment, ISignupMechanism, ITemplateNameResolver)
from xmantissa.website import PrefixURLMixin, WebSite
from xmantissa.websession import usernameFromRequest
from xmantissa.publicweb import PublicAthenaLivePage, PublicPage
from xmantissa.webnav import Tab
from xmantissa.webtheme import ThemedDocumentFactory, getLoader
from xmantissa.webapp import PrivateApplication
from xmantissa import plugins, liveform
from xmantissa.websession import PersistentSession
from xmantissa.smtp import parseAddress
from xmantissa.error import ArgumentError
from xmantissa.product import Product


_theMX = None
def getMX():
    """
    Retrieve the single MXCalculator instance, creating it first if
    necessary.
    """
    global _theMX
    if _theMX is None:
        _theMX = relaymanager.MXCalculator()
    return _theMX



def _sendEmail(_from, to, msg):

    def gotMX(mx):
        return smtp.sendmail(str(mx.name), _from, [to], msg)

    return getMX().getMX(to.split('@', 1)[1]).addCallback(gotMX)



class PasswordResetResource(PublicPage):
    """
    I handle the user-facing parts of password reset - the web form junk and
    sending of emails.

    The user sees a password reset form. The form asks the user for the
    username they use on this server. The form data is posted back to the
    C{PasswordResetResource}. On render, the resource creates a new 'attempt'
    (a L{_PasswordResetAttempt}) and sends an email to one of user's external
    addresses, if such a thing exists. The email contains a URL which is a
    child of this page, the last segment being the attempt ID.

    The user can then check their external email account and follow the link.
    Clicking the link loads the stored attempt and presents a password change
    form. The user can then specify a new password, click submit and their
    password will be reset.

    Currently unspecified behavior:
    - What happens when the provided username doesn't exist.
    - What happens when the provided passwords mismatch.
    - What happens when the user doesn't have an external account registered.

    @ivar store: a site store containing a L{WebSite}.
    @type store: L{axiom.store.Store}

    @ivar templateResolver: a template resolver instance that will return
        the appropriate doc factory.
    """

    attempt = None

    def __init__(self, store, templateResolver=None):
        if templateResolver is None:
            templateResolver = ITemplateNameResolver(store)
        PublicPage.__init__(self, None, store,
                            templateResolver.getDocFactory('reset'),
                            None, None, templateResolver)
        self.store = store
        self.loginSystem = store.findUnique(userbase.LoginSystem, default=None)


    def locateChild(self, ctx, segments):
        """
        Initialize self with the given key's L{_PasswordResetAttempt}, if any.

        @param segments: a L{_PasswordResetAttempt} key (hopefully)
        @return: C{(self, ())} with C{self.attempt} initialized, or L{NotFound}
        @see: L{attemptByKey}
        """
        if len(segments) == 1:
            attempt = self.attemptByKey(unicode(segments[0]))
            if attempt is not None:
                self.attempt = attempt
                return (self, ())
        return NotFound


    def renderHTTP(self, ctx):
        """
        Handle the password reset form.

        The following exchange describes the process:

            S: Render C{reset}
            C: POST C{username} or C{email}
            S: L{handleRequestForUser}, render C{reset-check-email}

            (User follows the emailed reset link)

            S: Render C{reset-step-two}
            C: POST C{password1}
            S: L{resetPassword}, render C{reset-done}
        """
        req = inevow.IRequest(ctx)

        if req.method == 'POST':
            if req.args.get('username', [''])[0]:
                user = unicode(usernameFromRequest(req), 'ascii')
                self.handleRequestForUser(user, URL.fromContext(ctx))
                self.fragment = self.templateResolver.getDocFactory(
                    'reset-check-email')
            elif req.args.get('email', [''])[0]:
                email = req.args['email'][0].decode('ascii')
                acct = self.accountByAddress(email)
                if acct is not None:
                    username = '@'.join(
                        userbase.getAccountNames(acct.avatars.open()).next())
                    self.handleRequestForUser(username, URL.fromContext(ctx))
                self.fragment = self.templateResolver.getDocFactory('reset-check-email')
            elif 'password1' in req.args:
                (password,) = req.args['password1']
                self.resetPassword(self.attempt, unicode(password))
                self.fragment = self.templateResolver.getDocFactory('reset-done')
            else:
                # Empty submit;  redirect back to self
                return URL.fromContext(ctx)
        elif self.attempt:
            self.fragment = self.templateResolver.getDocFactory('reset-step-two')

        return PublicPage.renderHTTP(self, ctx)


    def handleRequestForUser(self, username, url):
        """
        User C{username} wants to reset their password.  Create an attempt
        item, and send them an email if the username is valid
        """
        attempt = self.newAttemptForUser(username)
        account = self.accountByAddress(username)
        if account is None:
            # do we want to disclose this to the user?
            return
        email = self.getExternalEmail(account)
        if email is not None:
            self.sendEmail(url, attempt, email)


    def sendEmail(self, url, attempt, email, _sendEmail=_sendEmail):
        """
        Send an email for the given L{_PasswordResetAttempt}.

        @type url: L{URL}
        @param url: The URL of the password reset page.

        @type attempt: L{_PasswordResetAttempt}
        @param attempt: An L{Item} representing a particular user's attempt to
        reset their password.

        @type email: C{str}
        @param email: The email will be sent to this address.
        """

        host = url.netloc.split(':', 1)[0]
        from_ = 'reset@' + host

        body = file(sibpath(__file__, 'reset.rfc2822')).read()
        body %= {'from': from_,
                 'to': email,
                 'date': rfc822.formatdate(),
                 'message-id': smtp.messageid(),
                 'link': url.child(attempt.key)}

        _sendEmail(from_, email, body)


    def attemptByKey(self, key):
        """
        Locate the L{_PasswordResetAttempt} that corresponds to C{key}
        """

        return self.store.findUnique(_PasswordResetAttempt,
                                     _PasswordResetAttempt.key == key,
                                     default=None)


    def _makeKey(self, usern):
        """
        Make a new, probably unique key. This key will be sent in an email to
        the user and is used to access the password change form.
        """
        return unicode(md5.new(str((usern, time.time(), random.random()))).hexdigest())


    def newAttemptForUser(self, user):
        """
        Create an L{_PasswordResetAttempt} for the user whose username is C{user}
        @param user: C{unicode} username
        """
        # we could query for other attempts by the same
        # user within some timeframe and raise an exception,
        # if we wanted
        return _PasswordResetAttempt(store=self.store,
                                     username=user,
                                     timestamp=extime.Time(),
                                     key=self._makeKey(user))


    def getExternalEmail(self, account):
        """
        @return: str which is an external email address for the C{account}.
        None if there is no such address.
        """
        # XXX - shouldn't userbase do this for me? - jml
        method = self.store.findFirst(
            userbase.LoginMethod,
            AND (userbase.LoginMethod.account == account,
                 userbase.LoginMethod.internal == False))
        if method is None:
            return None
        else:
            return '%s@%s' % (method.localpart, method.domain)


    def accountByAddress(self, username):
        """
        @return: L{userbase.LoginAccount} for C{username} or None
        """
        userAndDomain = username.split('@', 1)
        if len(userAndDomain) != 2:
            return None
        return self.loginSystem.accountByAddress(*userAndDomain)


    def resetPassword(self, attempt, newPassword):
        """
        @param attempt: L{_PasswordResetAttempt}

        reset the password of the user who initiated C{attempt} to C{newPassword},
        and afterward, delete the attempt and any persistent sessions that belong
        to the user
        """

        self.accountByAddress(attempt.username).password = newPassword

        self.store.query(
            PersistentSession,
            PersistentSession.authenticatedAs == str(attempt.username)
            ).deleteFromStore()

        attempt.deleteFromStore()



class _PasswordResetAttempt(Item):
    """
    I represent as as-yet incomplete attempt at password reset
    """

    typeName = 'password_reset_attempt'
    schemaVersion = 1

    key = text()
    username = text()
    timestamp = timestamp()



class PasswordReset(Item):
    """
    I was an item that contained some of the model functionality of
    L{PasswordResetResource}, but now I am just a shell item (see
    L{passwordReset1to2}) and my functionality has been moved to
    L{PasswordResetResource}.
    """
    typeName = 'password_reset'
    schemaVersion = 2

    installedOn = reference()



def passwordReset1to2(old):
    """
    Power down and delete the item
    """
    new = old.upgradeVersion(old.typeName, 1, 2, installedOn=None)
    for iface in new.store.interfacesFor(new):
        new.store.powerDown(new, iface)
    new.deleteFromStore()

upgrade.registerUpgrader(passwordReset1to2, 'password_reset', 1, 2)



class NoSuchFactory(Exception):
    """
    An attempt was made to create a signup page using the name of a benefactor
    factory which did not correspond to anything in the database.
    """



class TicketClaimer(Page):
    def childFactory(self, ctx, name):
        for T in self.original.store.query(
            Ticket,
            AND(Ticket.booth == self.original,
                Ticket.nonce == unicode(name, 'ascii'))):
            something = T.claim()
            res = IResource(something)
            lgo = getattr(res, 'logout', lambda : None)
            ISession(ctx).setDefaultResource(res, lgo)
            return URL.fromContext(ctx).click("/private")
        return None



class TicketBooth(Item, PrefixURLMixin):
    implements(ISiteRootPlugin)

    typeName = 'ticket_powerup'
    schemaVersion = 1

    sessioned = True

    claimedTicketCount = integer(default=0)
    createdTicketCount = integer(default=0)

    defaultTicketEmail = text(default=None)

    prefixURL = 'ticket'

    def createResource(self):
        return TicketClaimer(self)

    def createTicket(self, issuer, email, product):
        t = self.store.findOrCreate(
            Ticket,
            product=product,
            booth=self,
            avatar=None,
            issuer=issuer,
            email=email)
        return t

    createTicket = transacted(createTicket)

    def ticketClaimed(self, ticket):
        self.claimedTicketCount += 1

    def ticketLink(self, domainName, httpPortNumber, nonce):
        httpPort = ''
        httpScheme = 'http'

        if httpPortNumber == 443:
            httpScheme = 'https'
        elif httpPortNumber != 80:
            httpPort = ':' + str(httpPortNumber)

        return '%s://%s%s/%s/%s' % (
            httpScheme, domainName, httpPort, self.prefixURL, nonce)

    def issueViaEmail(self, issuer, email, product, templateData,
                      domainName, httpPort=80):
        """
        Send a ticket via email to the supplied address, which, when claimed, will
        create an avatar and allow the given product to endow it with
        things.

        @param issuer: An object, preferably a user, to track who issued this
        ticket.

        @param email: a str, formatted as an rfc2821 email address
        (user@domain) -- source routes not allowed.

        @param product: an instance of L{Product}

        @param domainName: a domain name, used as the domain part of the
        sender's address, and as the web server to generate a link to within
        the email.

        @param httpPort: a port number for the web server running on domainName

        @param templateData: A string containing an rfc2822-format email
        message, which will have several python values interpolated into it
        dictwise:

            %(from)s: To be used for the From: header; will contain an
             rfc2822-format address.

            %(to)s: the address that we are going to send to.

            %(date)s: an rfc2822-format date.

            %(message-id)s: an rfc2822 message-id

            %(link)s: an HTTP URL that we are generating a link to.

        """

        ticket = self.createTicket(issuer,
                                   unicode(email, 'ascii'),
                                   product)
        nonce = ticket.nonce

        signupInfo = {'from': 'signup@'+domainName,
                      'to': email,
                      'date': rfc822.formatdate(),
                      'message-id': smtp.messageid(),
                      'link': self.ticketLink(domainName, httpPort, nonce)}

        msg = templateData % signupInfo

        return ticket, _sendEmail(signupInfo['from'], email, msg)



def _generateNonce():
    return unicode(os.urandom(16).encode('hex'), 'ascii')



class ITicketIssuer(Interface):
    def issueTicket(emailAddress):
        pass



class SignupMechanism(object):
    """
    I am a Twisted plugin helper.

    Instantiate me at module scope in a xmantissa.plugins submodule, including
    a name and description for the administrator.
    """
    implements(ISignupMechanism, plugin.IPlugin)
    def __init__(self, name, description, itemClass, configuration):
        """

        @param name: the name (a short string) to display to the administrator
        for selecting this signup mechanism.

        @param description: the description (a long string) for this signup
        mechanism.

        @param itemClass: a reference to a callable which takes keyword
        arguments described by L{configuration}, in addition to:

            store: the store to create the item in

            booth: a reference to a L{TicketBooth} that can create tickets for
            the created signup mechanism

            product: the product being installed by this signup.

            emailTemplate: a template for the email to be sent to the user

            prompt: a short unicode string describing this signup mechanism, as
            distinct from others.  For example: "Student Sign Up", or "Faculty
            Sign Up"

        @param configuration: a list of LiveForm arguments.
        """
        self.name = name
        self.description = description
        self.itemClass = itemClass
        self.configuration = configuration



freeTicketSignupConfiguration = [
    liveform.Parameter('prefixURL',
                       liveform.TEXT_INPUT,
                       unicode,
                       u'The web location at which users will be able to request tickets.',
                       default=u'signup')]

class FreeTicketSignup(Item, PrefixURLMixin):
    implements(ISiteRootPlugin)

    typeName = 'free_signup'
    schemaVersion = 6

    sessioned = True

    prefixURL = text(allowNone=False)
    booth = reference()
    product = reference(doc="An instance of L{product.Product} to install on"
                        " the new user's store")
    emailTemplate = text()
    prompt = text()

    def createResource(self):
        return PublicAthenaLivePage(
            self.store,
            getLoader("signup"),
            IStaticShellContent(self.store, None),
            None,
            iface = ITicketIssuer,
            rootObject = self)

    def issueTicket(self, url, emailAddress):
        domain, port = url.get('hostname'), int(url.get('port') or 80)
        if os.environ.get('CC_DEV'):
            ticket = self.booth.createTicket(self, emailAddress, self.product)
            return '<a href="%s">Claim Your Account</a>' % (
                    self.booth.ticketLink(domain, port, ticket.nonce),)
        else:
            ticket, issueDeferred = self.booth.issueViaEmail(
                self,
                emailAddress.encode('ascii'), # heh
                self.product,
                self.emailTemplate,
                domain,
                port)

            issueDeferred.addCallback(
                lambda result: u'Please check your email for a ticket!')

            return issueDeferred



def freeTicketSignup1To2(old):
    return old.upgradeVersion('free_signup', 1, 2,
                              prefixURL=old.prefixURL,
                              booth=old.booth,
                              benefactor=old.benefactor)

upgrade.registerUpgrader(freeTicketSignup1To2, 'free_signup', 1, 2)



def freeTicketSignup2To3(old):
    emailTemplate = file(sibpath(__file__, 'signup.rfc2822')).read()
    emailTemplate %= {'blurb': u'',
                      'subject': 'Welcome to a Generic Axiom Application!',
                      'linktext': "Click here to claim your 'generic axiom application' account"}

    return old.upgradeVersion('free_signup', 2, 3,
                              prefixURL=old.prefixURL,
                              booth=old.booth,
                              benefactor=old.benefactor,
                              emailTemplate=emailTemplate)

upgrade.registerUpgrader(freeTicketSignup2To3, 'free_signup', 2, 3)

declareLegacyItem(typeName='free_signup',
                  schemaVersion=3,
                  attributes=dict(prefixURL=text(),
                                  booth=reference(),
                                  benefactor=reference(),
                                  emailTemplate=text()))



def freeTicketSignup3To4(old):
    return old.upgradeVersion('free_signup', 3, 4,
                              prefixURL=old.prefixURL,
                              booth=old.booth,
                              benefactor=old.benefactor,
                              emailTemplate=old.emailTemplate,
                              prompt=u'Sign Up')

upgrade.registerUpgrader(freeTicketSignup3To4, 'free_signup', 3, 4)

declareLegacyItem(typeName='free_signup',
                  schemaVersion=4,
                  attributes=dict(prefixURL=text(),
                                  booth=reference(),
                                  benefactor=reference(),
                                  emailTemplate=text(),
                                  prompt=text()))

def freeTicketSignup4To5(old):
    return old.upgradeVersion('free_signup', 4, 5,
                              prefixURL=old.prefixURL,
                              booth=old.booth,
                              benefactor=old.benefactor,
                              emailTemplate=old.emailTemplate,
                              prompt=old.prompt)

upgrade.registerUpgrader(freeTicketSignup4To5, 'free_signup', 4, 5)


declareLegacyItem(typeName='free_signup',
                  schemaVersion=5,
                  attributes=dict(prefixURL=text(),
                                  booth=reference(),
                                  benefactor=reference(),
                                  emailTemplate=text(),
                                  prompt=text()))

def freeTicketSignup5To6(old):
    newProduct = old.store.findOrCreate(Product,
                                        types=list(
        chain(*[b.powerupNames for b in
                old.benefactor.benefactors('ascending')])))
    return old.upgradeVersion('free_signup', 5, 6,
                              prefixURL=old.prefixURL,
                              booth=old.booth,
                              product=newProduct,
                              emailTemplate=old.emailTemplate,
                              prompt=old.prompt)

upgrade.registerUpgrader(freeTicketSignup5To6, "free_signup", 5, 6)

class ValidatingSignupForm(liveform.LiveForm):
    jsClass = u'Mantissa.Validate.SignupForm'

    _parameterNames = [
        'realName',
        'username',
        'domain',
        'password',
        'emailAddress']

    docFactory = ThemedDocumentFactory("user-info-signup", "templateResolver")

    def __init__(self, uis):
        self.userInfoSignup = uis
        self.templateResolver = ITemplateNameResolver(uis.store)
        super(ValidatingSignupForm, self).__init__(
            uis.createUser,
            [liveform.Parameter(pname, liveform.TEXT_INPUT, unicode)
             for pname in
             self._parameterNames])


    def getInitialArguments(self):
        """
        Retrieve a domain name from the user info signup item and return it so
        the client will know what domain it can sign up in.
        """
        return (self.userInfoSignup.getAvailableDomains()[0],)


    def usernameAvailable(self, username, domain):
        return self.userInfoSignup.usernameAvailable(username, domain)
    athena.expose(usernameAvailable)



class UserInfo(Item):
    """
    An Item which stores information gleaned from the signup process of
    L{UserInfoSignup}.  The L{UserInfo} will reside in the substore of the
    user (which was created during the signup process), and will record
    information about its owner.
    """
    schemaVersion = 2
    realName = text(
        doc="""
        The name entered at signup time by the user as their I{real} name.
        """)


def upgradeUserInfo1to2(oldUserInfo):
    """
    Concatenate the I{firstName} and I{lastName} attributes from the old user
    info item and set the result as the I{realName} attribute of the upgraded
    item.
    """
    newUserInfo = oldUserInfo.upgradeVersion(
        UserInfo.typeName, 1, 2,
        realName=oldUserInfo.firstName + u" " + oldUserInfo.lastName)
    return newUserInfo
upgrade.registerUpgrader(upgradeUserInfo1to2, UserInfo.typeName, 1, 2)



class UserInfoSignup(Item, PrefixURLMixin):
    """
    This signup page provides a way to sign up while including some relevant
    information about yourself, including the selection of a username.
    """

    implements(ISiteRootPlugin)

    powerupInterfaces = (ISiteRootPlugin,)
    schemaVersion = 2
    sessioned = True

    booth = reference()
    product = reference(
        doc="""
        An instance of L{product.Product} to install on the new user's store.
        """)
    emailTemplate = text()
    prompt = text()

    # ISiteRootPlugin

    prefixURL = text(allowNone=False)

    def createResource(self):
        page = PublicAthenaLivePage(
            self.store,
            ValidatingSignupForm(self),
            IStaticShellContent(self.store, None))
        page.needsSecure = True
        return page


    # UserInfoSignup
    def getAvailableDomains(self):
        """
        Return a list of domain names available on this site.
        """
        return getDomainNames(self.store)


    def usernameAvailable(self, username, domain):
        """
        Check to see if a username is available for the user to select.
        """
        if len(username) < 2:
            return [False, u"Username too short"]
        for char in u"[ ,:;<>@()!\"'%&\\|\t\b":
            if char in username:
                return [False,
                        u"Username contains invalid character: '%s'" % char]

        # The localpart is acceptable if it can be parsed as the local part
        # of an RFC 2821 address.
        try:
            parseAddress("<%s@example.com>" % (username,))
        except ArgumentError:
            return [False, u"Username fails to parse"]

        # The domain is acceptable if it is one which we actually host.
        if domain not in self.getAvailableDomains():
            return [False, u"Domain not allowed"]

        query = self.store.query(userbase.LoginMethod,
                                 AND(userbase.LoginMethod.localpart == username,
                                     userbase.LoginMethod.domain == domain))
        return [not bool(query.count()), u"Username already taken"]


    def createUser(self, realName, username, domain, password, emailAddress):
        """
        Create a user, storing some associated metadata in the user's store,
        i.e. their first and last names (as a L{UserInfo} item), and a
        L{axiom.userbase.LoginMethod} allowing them to login with their email
        address.

        @param realName: the real name of the user.
        @type realName: C{unicode}

        @param username: the user's username.  they will be able to login with
            this.
        @type username: C{unicode}

        @param domain: the local domain - used internally to turn C{username}
            into a localpart@domain style string .
        @type domain: C{unicode}

        @param password: the password to be used for the user's account.
        @type password: C{unicode}

        @param emailAddress: the user's external email address.  they will be
            able to login with this also.
        @type emailAddress: C{unicode}

        @rtype: C{NoneType}
        """
        # XXX This method should be called in a transaction, it shouldn't
        # start a transaction itself.
        def _():
            loginsystem = self.store.findUnique(userbase.LoginSystem)

            # Create an account with the credentials they specified,
            # making it internal since it belongs to us.
            acct = loginsystem.addAccount(username, domain, password,
                                          verified=True, internal=True)

            # Create an external login method associated with the email
            # address they supplied, as well.  This creates an association
            # between that external address and their account object,
            # allowing password reset emails to be sent and letting them log
            # in to this account using that address as a username.
            emailPart, emailDomain = emailAddress.split("@")
            acct.addLoginMethod(emailPart, emailDomain, protocol=u"email",
                                verified=False, internal=False)
            substore = IBeneficiary(acct)
            # Record some of that signup information in case application
            # objects are interested in it.
            UserInfo(store=substore, realName=realName)
            self.product.installProductOn(substore)
        self.store.transact(_)

declareLegacyItem(typeName=UserInfoSignup.typeName,
                  schemaVersion=1,
                  attributes=dict(booth = reference(),
                                  benefactor = reference(),
                                  emailTemplate = text(),
                                  prompt = text(),
                                  prefixURL = text(allowNone=False)))

def userInfoSignup1To2(old):
    newProduct = old.store.findOrCreate(Product,
                                        types=list(
        chain(*[b.powerupNames for b in
                old.benefactor.benefactors('ascending')])))
    return old.upgradeVersion(UserInfoSignup.typeName, 1, 2,
                              booth=old.booth,
                              product=newProduct,
                              emailTemplate=old.emailTemplate,
                              prompt=old.prompt,
                              prefixURL=old.prefixURL)
upgrade.registerUpgrader(userInfoSignup1To2, UserInfoSignup.typeName, 1, 2)


class InitializerBenefactor(Item):
    typeName = 'initializer_benefactor'
    schemaVersion = 1

    realBenefactor = reference()

    def endow(self, ticket, beneficiary):
        beneficiary.findOrCreate(WebSite).installOn(beneficiary)
        beneficiary.findOrCreate(PrivateApplication).installOn(beneficiary)

        # They may have signed up in the past - if so, they already
        # have a password, and we should skip the initializer phase.
        substore = beneficiary.store.parent.getItemByID(beneficiary.store.idInParent)
        for acc in self.store.query(userbase.LoginAccount,
                                    userbase.LoginAccount.avatars == substore):
            if acc.password:
                self.realBenefactor.endow(ticket, beneficiary)
            else:
                beneficiary.findOrCreate(Initializer).installOn(beneficiary)
            break

    def resumeSignup(self, ticket, avatar):
        self.realBenefactor.endow(ticket, avatar)


class Initializer(Item):

    implements(INavigableElement)

    typeName = 'password_initializer'
    schemaVersion = 1

    installedOn = reference()

    powerupInterfaces = (INavigableElement,)

    def getTabs(self):
        # This won't ever actually show up
        return [Tab('Preferences', self.storeID, 1.0)]

    def setPassword(self, password):
        substore = self.store.parent.getItemByID(self.store.idInParent)
        for acc in self.store.parent.query(userbase.LoginAccount,
                                           userbase.LoginAccount.avatars == substore):
            acc.password = password
            self._delegateToBenefactor(acc)
            return

    def _delegateToBenefactor(self, loginAccount):
        site = self.store.parent
        ticket = site.findUnique(Ticket, Ticket.avatar == loginAccount)
        benefactor = ticket.benefactor
        benefactor.resumeSignup(ticket, self.store)

        self.store.powerDown(self, INavigableElement)
        self.deleteFromStore()



class InitializerPage(PublicPage):

    def __init__(self, original):
        for resource, domain in userbase.getAccountNames(original.installedOn):
            username = '%s@%s' % (resource, domain)
            break
        else:
            username = None
        PublicPage.__init__(self, original, original.store.parent, getLoader('initialize'),
                            IStaticShellContent(original.installedOn, None),
                            username)

    def render_head(self, ctx, data):
        tag = PublicPage.render_head(self, ctx, data)
        return tag[tags.script(src='/Mantissa/js/initialize.js')]

    def renderHTTP(self, ctx):
        req = inevow.IRequest(ctx)
        password = req.args.get('password', [None])[0]

        if password is None:
            return Page.renderHTTP(self, ctx)

        self.original.store.transact(self.original.setPassword,
                                     unicode(password)) # XXX TODO: select
                                                        # proper decoding
                                                        # strategy.
        return URL.fromString('/')

registerAdapter(InitializerPage,
                Initializer,
                inevow.IResource)



class Ticket(Item):
    schemaVersion = 2
    typeName = 'ticket'

    issuer = reference(allowNone=False)
    booth = reference(allowNone=False)
    avatar = reference()
    claimed = integer(default=0)
    product = reference(allowNone=False)

    email = text()
    nonce = text()

    def __init__(self, **kw):
        super(Ticket, self).__init__(**kw)
        self.booth.createdTicketCount += 1
        self.nonce = _generateNonce()

    def claim(self):
        if not self.claimed:
            log.msg("Claiming a ticket for the first time for %r" % (self.email,))
            username, domain = self.email.split('@', 1)
            realm = IRealm(self.store)
            acct = realm.accountByAddress(username, domain)
            if acct is None:
                acct = realm.addAccount(username, domain, None)
            self.avatar = acct
            self.claimed += 1
            self.booth.ticketClaimed(self)
            self.product.installProductOn(IBeneficiary(self.avatar))
        else:
            log.msg("Ignoring re-claim of ticket for: %r" % (self.email,))
        return self.avatar
    claim = transacted(claim)


def ticket1to2(old):
    """
    change Ticket to refer to Products and not benefactor factories.
    """
    if isinstance(old.benefactor, Multifactor):
        types = list(chain(*[b.powerupNames for b in
                old.benefactor.benefactors('ascending')]))
    elif isinstance(old.benefactor, InitializerBenefactor):
        #oh man what a mess
        types = list(chain(*[b.powerupNames for b in
                old.benefactor.realBenefactor.benefactors('ascending')]))
    newProduct = old.store.findOrCreate(Product,
                                        types=types)

    if old.issuer is None:
        issuer = old.store.findOrCreate(TicketBooth)
    else:
        issuer = old.issuer
    t = old.upgradeVersion(Ticket.typeName, 1, 2,
                           product = newProduct,
                           issuer = issuer,
                           booth = old.booth,
                           avatar = old.avatar,
                           claimed = old.claimed,

                           email = old.email,
                           nonce = old.nonce)

upgrade.registerUpgrader(ticket1to2, Ticket.typeName, 1, 2)
class _DelegatedBenefactor(Item):
    typeName = 'mantissa_delegated_benefactor'
    schemaVersion = 1

    benefactor = reference(allowNone=False)
    multifactor = reference(allowNone=False)
    order = integer(allowNone=False, indexed=True)



class Multifactor(Item):
    """
    A benefactor with no behavior of its own, but which collects
    references to other benefactors and delegates endowment
    responsibility to them.
    """

    typeName = 'mantissa_multi_benefactor'
    schemaVersion = 1

    order = integer(default=0)

    def benefactors(self, order):
        for deleg in self.store.query(_DelegatedBenefactor,
                                      _DelegatedBenefactor.multifactor == self,
                                      sort=getattr(_DelegatedBenefactor.order, order)):
            yield deleg.benefactor



class _SignupTracker(Item):
    """
    Signup-system private Item used to track which signup mechanisms
    have been created.
    """
    signupItem = reference()
    createdOn = timestamp()
    createdBy = text()



def _getPublicSignupInfo(siteStore):
    """
    Get information about public web-based signup mechanisms.

    @param siteStore: a store with some signups installed on it (as indicated
    by _SignupTracker instances).

    @return: a generator which yields 2-tuples of (prompt, url) where 'prompt'
    is unicode briefly describing the signup mechanism (e.g. "Sign Up"), and
    'url' is a (unicode) local URL linking to a page where an anonymous user
    can access it.
    """

    # Note the underscore; this _should_ be a public API but it is currently an
    # unfortunate hack; there should be a different powerup interface that
    # requires prompt and prefixURL attributes rather than _SignupTracker.
    # -glyph

    for tr in siteStore.query(_SignupTracker):
        si = tr.signupItem
        p = getattr(si, 'prompt', None)
        u = getattr(si, 'prefixURL', None)
        if p is not None and u is not None:
            yield (p, u'/'+u)


class SignupConfiguration(Item):
    """
    Provide administrative configuration tools for the signup options
    available on a Mantissa server.
    """
    typeName = 'mantissa_signup_configuration'
    schemaVersion = 1

    installedOn = reference()

    powerupInterfaces = (INavigableElement,)

    def getTabs(self):
        return [Tab('Admin', self.storeID, 0.5,
                    [Tab('Signup', self.storeID, 0.7)],
                    authoritative=False)]


    def getSignupSystems(self):
        return dict((p.name, p) for p in plugin.getPlugins(ISignupMechanism, plugins))

    def createSignup(self, creator, signupClass, signupConf,
                     product, emailTemplate, prompt):
        """
        Create a new signup facility in the site store's database.

        @param creator: a unicode string describing the creator of the new
        signup mechanism, for auditing purposes.

        @param signupClass: the item type of the signup mechanism to create.

        @param signupConf: a dictionary of keyword arguments for
        L{signupClass}'s constructor.

        @param product: A Product instance, describing the powerups to be
        installed with this signup.

        @param emailTemplate: a unicode string which contains some text that
        will be sent in confirmation emails generated by this signup mechanism
        (if any)

        @param prompt: a short unicode string describing this signup mechanism,
        as distinct from others.  For example: "Student Sign Up", or "Faculty
        Sign Up"

        @return: a newly-created, database-resident instance of signupClass.
        """

        siteStore = self.store.parent

        booth = siteStore.findOrCreate(TicketBooth, lambda booth: installOn(booth, siteStore))
        signupItem = signupClass(
            store=siteStore,
            booth=booth,
            product=product,
            emailTemplate=emailTemplate,
            prompt=prompt,
            **signupConf)
        siteStore.powerUp(signupItem)
        _SignupTracker(store=siteStore,
                       signupItem=signupItem,
                       createdOn=extime.Time(),
                       createdBy=creator)

        return signupItem

class ProductFormMixin(object):
    """
    Utility functions for rendering a form for choosing products to install.
    """
    def makeProductPicker(self):
        """
        Make a LiveForm with radio buttons for each Product in the store.
        """
        productPicker = liveform.LiveForm(
            self.coerceProduct,
            [liveform.Parameter(
              str(id(product)),
              liveform.FORM_INPUT,
              liveform.LiveForm(
              lambda selectedProduct, product=product: selectedProduct and product,
              [liveform.Parameter(
                'selectedProduct',
                liveform.RADIO_INPUT,
                bool,
                repr(product))]
              ))
              for product
              in self.original.store.parent.query(Product)],
            u"Product to Install")
        return productPicker

    def coerceProduct(self, **kw):
        """
        Convert the return value from the form to a list of Products.
        """
        return filter(None, kw.values())[0]




class SignupFragment(athena.LiveFragment, ProductFormMixin):
    fragmentName = 'signup-configuration'
    live = 'athena'

    def head(self):
        # i think this is the lesser evil.
        # alternatives being:
        #  * mangle form element names so we can put these in mantissa.css
        #    without interfering with similarly named things
        #  * put the following line of CSS into it's own file that is included
        #    by only this page
        #  * remove these styles entirely (makes the form unusable, the
        #    type="text" inputs are *tiny*)
        return tags.style(type='text/css')['''
        input[name=linktext], input[name=subject], textarea[name=blurb] { width: 40em }
        ''']

    def render_signupConfigurationForm(self, ctx, data):

        def makeSignupCoercer(signupPlugin):
            """
            Return a function that converts a selected flag and a set of
            keyword arguments into either None (if not selected) or a 2-tuple
            of (signupClass, kwargs).  signupClass is a callable which takes
            the kwargs as keyword arguments and returns an Item (a signup
            mechanism plugin gizmo).
            """
            def signupCoercer(selectedSignup, **signupConf):
                """
                Receive coerced values from the form post, massage them as
                described above.
                """
                if selectedSignup:
                    return signupPlugin.itemClass, signupConf
                return None
            return signupCoercer

        def coerceSignup(**kw):
            return filter(None, kw.values())[0]

        signupMechanismConfigurations = liveform.LiveForm(
            # makeSignupCoercer sets it up, we knock it down. (Nones returned
            # are ignored, there will be exactly one selected).
            coerceSignup,
            [liveform.Parameter(
                signupMechanism.name,
                liveform.FORM_INPUT,
                liveform.LiveForm(
                    makeSignupCoercer(signupMechanism),
                    [liveform.Parameter(
                        'selectedSignup',
                        liveform.RADIO_INPUT,
                        bool,
                        signupMechanism.description)] + signupMechanism.configuration,
                    signupMechanism.name))
             for signupMechanism
             in self.original.getSignupSystems().itervalues()],
            u"Signup Type")

        def coerceEmailTemplate(**k):
            return file(sibpath(__file__, 'signup.rfc2822')).read() % k

        emailTemplateConfiguration = liveform.LiveForm(
            coerceEmailTemplate,
            [liveform.Parameter('subject',
                                liveform.TEXT_INPUT,
                                unicode,
                                u'Email Subject',
                                default='Welcome to a Generic Axiom Application!'),
             liveform.Parameter('blurb',
                                liveform.TEXTAREA_INPUT,
                                unicode,
                                u'Blurb',
                                default=''),
             liveform.Parameter('linktext',
                                liveform.TEXT_INPUT,
                                unicode,
                                u'Link Text',
                                default="Click here to claim your 'generic axiom application' account")],
             description='Email Template')
        emailTemplateConfiguration.docFactory = getLoader('liveform-compact')

        existing = list(self.original.store.parent.query(_SignupTracker))
        if 0 < len(existing):
            deleteSignupForm = liveform.LiveForm(
                lambda **kw: self._deleteTrackers(k for (k, v) in kw.itervalues() if v),
                [liveform.Parameter('signup-' + str(i),
                                    liveform.CHECKBOX_INPUT,
                                    lambda wasSelected, tracker=tracker: (tracker, wasSelected),
                                    repr(tracker.signupItem))
                    for (i, tracker) in enumerate(existing)],
                description='Delete Existing Signups')
            deleteSignupForm.setFragmentParent(self)
        else:
            deleteSignupForm = ''

        productPicker = self.makeProductPicker()

        createSignupForm = liveform.LiveForm(
            self.createSignup,
            [liveform.Parameter('signupPrompt',
                                liveform.TEXT_INPUT,
                                unicode,
                                u'Descriptive, user-facing prompt for this signup',
                                default=u'Sign Up'),
             liveform.Parameter('product',
                                liveform.FORM_INPUT,
                                productPicker,
                                u'Pick some product'),
             liveform.Parameter('signupTuple',
                                liveform.FORM_INPUT,
                                signupMechanismConfigurations,
                                u'Pick just one dude'),
             liveform.Parameter('emailTemplate',
                                liveform.FORM_INPUT,
                                emailTemplateConfiguration,
                                u'You know you want to')],
            description='Create Signup')
        createSignupForm.setFragmentParent(self)

        return [deleteSignupForm, createSignupForm]


    def data_configuredSignupMechanisms(self, ctx, data):
        for _signupTracker in self.original.store.parent.query(_SignupTracker):
            yield {
                'typeName': _signupTracker.signupItem.__class__.__name__,
                'createdBy': _signupTracker.createdBy,
                'createdOn': _signupTracker.createdOn.asHumanly()}


    def createSignup(self,
                     signupPrompt,
                     signupTuple,
                     product,
                     emailTemplate):
        """

        @param signupPrompt: a short unicode string describing this new signup
        mechanism to disambiguate it from others.  For example: "sign up".

        @param signupTuple: a 2-tuple of (signupMechanism, signupConfig),

        """
        (signupMechanism, signupConfig) = signupTuple
        t = self.original.store.transact
        t(self.original.createSignup,
          self.page.username,
          signupMechanism,
          signupConfig,
          product,
          emailTemplate,
          signupPrompt)
        return u'Great job.'
    expose(createSignup)

    def _deleteTrackers(self, trackers):
        """
        Delete the given signup trackers and their associated signup resources.

        @param trackers: sequence of L{_SignupTrackers}
        """

        for tracker in trackers:
            if tracker.store is None:
                # we're not updating the list of live signups client side, so
                # we might get a signup that has already been deleted
                continue

            sig = tracker.signupItem

            # XXX the only reason we're doing this here is that we're afraid to
            # add a whenDeleted=CASCADE to powerups because it's inefficient,
            # however, this is arguably the archetypical use of
            # whenDeleted=CASCADE.  Soon we need to figure out a real solution
            # (but I have no idea what it is). -glyph

            for iface in sig.store.interfacesFor(sig):
                sig.store.powerDown(sig, iface)
            tracker.deleteFromStore()
            sig.deleteFromStore()


registerAdapter(SignupFragment, SignupConfiguration, INavigableFragment)
