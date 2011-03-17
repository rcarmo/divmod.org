# Copyright (c) 2008 Divmod.  See LICENSE for details.

from sys import stdout
from getpass import getpass

from zope.interface import implements

from twisted.python.log import msg, startLogging
from twisted.cred.credentials import UsernamePassword
from twisted.internet.protocol import ClientCreator
from twisted.protocols.amp import IBoxReceiver, Box, AMP
from twisted.internet.task import deferLater
from twisted.internet import reactor

from epsilon.react import react
from epsilon.ampauth import login
from epsilon.amprouter import Router

from xmantissa.ampserver import connectRoute


class BoxPrinter:
    implements(IBoxReceiver)

    def startReceivingBoxes(self, sender):
        self.sender = sender


    def ampBoxReceived(self, box):
        msg(str(box))


    def stopReceivingBoxes(self, reason):
        pass


def sendBox(printer):
    printer.sender.sendBox(Box({'foo': 'bar'}))
    return deferLater(reactor, 1, lambda: None)


def main(reactor, username, password):
    startLogging(stdout)
    router = Router()
    proto = AMP(router)
    router.bindRoute(proto, None).connectTo(None)
    cc = ClientCreator(reactor, lambda: proto)
    d = cc.connectTCP(username.split('@')[1], 7805)
    d.addCallback(login, UsernamePassword(username, password))
    d.addCallback(
        connectRoute, router, BoxPrinter(), u'http://divmod.org/ns/echo')
    d.addCallback(sendBox)
    return d


if __name__ == '__main__':
    react(reactor, main, [raw_input('Username (localpart@domain): '),
                          getpass('Password: ')])
