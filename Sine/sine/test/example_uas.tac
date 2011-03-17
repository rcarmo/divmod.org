from twisted.application import service, internet
from sine import useragent, sip
from sine.test.test_sip import TestRealm, PermissiveChecker
from twisted import cred
HOSTNAME = LOCAL_HOST = "faraday.divmod.com"
r = TestRealm(HOSTNAME)
r.interface = useragent.ICallRecipient
r.users["foo@"+HOSTNAME] =  useragent.SimpleCallRecipient()
p = cred.portal.Portal(r)
p.registerChecker(PermissiveChecker())
uas = useragent.UserAgentServer(p, LOCAL_HOST)
f = sip.SIPTransport(uas, [HOSTNAME], 5060)

application = service.Application("example_uas")
internet.UDPServer(5060, f).setServiceParent(application)
