# -*- test-case-name: xmantissa.test.test_q2q -*-

from axiom import item, attributes

from vertex import q2qclient

from xmantissa import ixmantissa

class UniversalEndpointService(item.Item):
    """
    """
    typeName = 'mantissa_q2q_service'
    schemaVersion = 1

    q2qPortNumber = attributes.integer(default=8787)
    inboundTCPPortNumber = attributes.integer(default=None)
    publicIP = attributes.integer(default=None)
    udpEnabled = attributes.integer(default=False)
    certificatePath = attributes.path(default=None)

    _svcInst = attributes.inmemory()

    def __init__(self, **kw):
        super(UniversalEndpointService, self).__init__(**kw)
        if self.certificatePath is None:
            self.certificatePath = self.store.newDirectory(str(self.storeID), 'certificates')
        if not self.certificatePath.exists():
            self.certificatePath.makedirs()


    def activate(self):
        self._svcInst = None

    def _makeService(self):
        self._svcInst = q2qclient.ClientQ2QService(
            self.certificatePath.path,
            publicIP=self.publicIP,
            inboundTCPPortnum=self.inboundTCPPortNumber,
            udpEnabled=self.udpEnabled,
            )

    def _getService(self):
        if self._svcInst is None:
            self._makeService()
        return self._svcInst

    def installOn(self, other):
        other.powerUp(self, ixmantissa.IQ2QService)

    def listenQ2Q(self, fromAddress, protocolsToFactories, serverDescription):
        return self._getService().listenQ2Q(fromAddress,
                                       protocolsToFactories,
                                       serverDescription)

    def connectQ2Q(self, fromAddress, toAddress, protocolName,
                   protocolFactory, usePrivateCertificate=None,
                   fakeFromDomain=None, chooser=None):
        return self._getService().connectQ2Q(
            fromAddress, toAddress, protocolName, protocolFactory,
            usePrivateCertificate, fakeFromDomain, chooser)
