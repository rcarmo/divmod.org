
"""
Account configuration and management features, via the web.

This is a pitiful implementation of these concepts (hence the pitiful
module name).  It will be replaced by a real implementation when
clustering is ready for general use.
"""

import pytz

from zope.interface import implements

from twisted.python.components import registerAdapter
from twisted.internet import defer

from nevow import inevow, athena
from nevow.athena import expose

from epsilon import extime

from axiom import item, attributes, userbase

from xmantissa import ixmantissa, websession

class InvalidPassword(Exception):
    pass

class NonExistentAccount(Exception):
    pass

class NoSuchSession(Exception):
    pass


class AuthenticationApplication(item.Item):

    typeName = 'mantissa_web_authentication_application'
    schemaVersion = 1

    lastCredentialsChange = attributes.timestamp(allowNone=False)

    def __init__(self, **kw):
        if 'lastCredentialsChange' not in kw:
            kw['lastCredentialsChange'] = extime.Time()
        super(AuthenticationApplication, self).__init__(**kw)

    def _account(self):
        substore = self.store.parent.getItemByID(self.store.idInParent)
        for account in self.store.parent.query(userbase.LoginAccount,
                                               userbase.LoginAccount.avatars == substore):
            return account
        raise NonExistentAccount()

    def _username(self):
        for (localpart, domain) in userbase.getAccountNames(self.store):
            return (localpart + '@' + domain).encode('utf-8')

    def hasCurrentPassword(self):
        return defer.succeed(self._account().password is not None)

    def changePassword(self, oldPassword, newPassword):
        account = self._account()
        if account.password is not None and account.password != oldPassword:
            raise InvalidPassword()
        else:
            account.password = newPassword
            self.lastCredentialsChange = extime.Time()


    def persistentSessions(self):
        username = self._username()
        return self.store.parent.query(
            websession.PersistentSession,
            websession.PersistentSession.authenticatedAs == username)


    def cancelPersistentSession(self, uid):
        username = self._username()
        for sess in self.store.parent.query(websession.PersistentSession,
                                            attributes.AND(websession.PersistentSession.authenticatedAs == username,
                                                           websession.PersistentSession.sessionKey == uid)):
            sess.deleteFromStore()
            break
        else:
            raise NoSuchSession()


class AuthenticationFragment(athena.LiveFragment):
    implements(ixmantissa.INavigableFragment)

    fragmentName = 'authentication-configuration'
    live = 'athena'
    title = 'Change Password'

    jsClass = u'Mantissa.Authentication'

    def __init__(self, original):
        self.store = original.store
        athena.LiveFragment.__init__(self, original)

    def head(self):
        return None

    def render_currentPasswordField(self, ctx, data):
        d = self.original.hasCurrentPassword()

        def cb(result):
            if result:
                patName = 'current-password'
            else:
                patName = 'no-current-password'
            return inevow.IQ(self.docFactory).onePattern(patName)

        return d.addCallback(cb)


    def render_cancel(self, ctx, data):
        # XXX See previous XXX 19th
        handler = 'Mantissa.Authentication.get(this).cancel(%r); return false'
        return ctx.tag(onclick=handler % (data['session'].sessionKey,))


    def changePassword(self, currentPassword, newPassword):
        try:
            self.original.changePassword(unicode(currentPassword), unicode(newPassword))
        except NonExistentAccount:
            raise NonExistentAccount('You do not seem to exist.  Password unchanged.')
        except InvalidPassword:
            raise InvalidPassword('Incorrect password!  Nothing changed.')
        else:
            return u'Password Changed!'
    expose(changePassword)


    def cancel(self, uid):
        try:
            self.original.cancelPersistentSession(str(uid))
        except NoSuchSession:
            raise NoSuchSession('That session seems to have vanished.')
        else:
            return u'Session discontinued'
    expose(cancel)


    def data_persistentSessions(self, ctx, data):
        zone = pytz.timezone('US/Eastern')
        for session in self.original.persistentSessions():
            yield dict(lastUsed=session.lastUsed.asHumanly(zone) + ' ' + zone.zone,
                       session=session)


registerAdapter(AuthenticationFragment, AuthenticationApplication, ixmantissa.INavigableFragment)
