import os

from twisted.cred import portal
from epsilon.scripts import certcreate

from axiom import errors as userbase
from axiom.scripts import axiomatic
from axiom.dependency import installOn

from xmantissa import website
from sine import confession

class Install(axiomatic.AxiomaticSubCommand):
    longdesc = """
    Install confession things
    """


    optParameters = [
        ('domain', 'd', 'localhost',
         "Domain this registrar is authoritative for;\
         i.e., the domain local users belong to."),
        ('port', 'p', '5060',
         'Port to listen on for SIP.')
        ]

    def postOptions(self):
        s = self.parent.getStore()
        s.findOrCreate(userbase.LoginSystem, lambda i: installOn(i, s))

        for ws in s.query(website.WebSite):
            break
        else:
            ws = website.WebSite(
                store=s,
                portNumber=8080,
                securePortNumber=8443,
                certificateFile='server.pem')
            installOn(ws, s)
            if not os.path.exists('server.pem'):
                certcreate.main([])


        #Is there a real way to do this?
        u = portal.IRealm(s).addAccount(u'confession', self['domain'], u'no password :(')
        us = u.avatars.open()
        installOn(confession.AnonConfessionUser(store=us), us)
        installOn(confession.ConfessionDispatcher(store=us, localHost=self['domain']), us)
