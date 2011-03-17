from twisted.application import service, internet
from twisted.internet import reactor
from sine import sip, useragent, echo
e = echo.Echoer()
uac = useragent.UserAgent.client(e, "echo", "faraday.divmod.com")
f = sip.SIPTransport(uac, ["faraday.divmod.com"], 5060)

uac.call(sip.parseURL("sip:washort@divmod.com"))

application = service.Application("echoclient")
internet.UDPServer(5060, f).setServiceParent(application)
