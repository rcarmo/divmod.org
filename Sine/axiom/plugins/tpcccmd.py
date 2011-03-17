from twisted.application.service import IService, Service

from axiom import item, attributes
from axiom.scripts import axiomatic
from axiom.dependency import installOn

from sine import sipserver, sip

class TPCC(axiomatic.AxiomaticCommand):
    longdesc = """
    Install TPCC tester (calls washort@divmod.com, confession@watt.divmod.com)
    """

    name = '3pcc'
    description = '3pcc hooray'
    optParameters = [
        ('port', 'p', '5060',
         'Port to listen on for SIP.')
        ]

    def postOptions(self):
        s = self.parent.getStore()
        svc = s.findOrCreate(sipserver.SIPDispatcherService, lambda svc: installOn(svc, s))
        testsvc = s.findOrCreate(TestService, lambda i: installOn(i, s), dispatcherSvc=svc)

class TestService(item.Item, Service):
    typeName = 'sine_tpcc_test_service'
    schemaVersion = 1
    installedOn = attributes.reference()
    parent = attributes.inmemory()
    running = attributes.inmemory()
    name = attributes.inmemory()

    dispatcherSvc = attributes.reference()

    powerupInterfaces = (IService,)

    def startService(self):
        print "YAY"
        self.dispatcherSvc.setupCallBetween(
            ("Confession Hotline (watt)", sip.URL("watt.divmod.com", "confession"), {},),
            ("Some Bozo", sip.URL("divmod.com", "washort"), {}),
            )
