# Copyright (c) 2008 Divmod.  See LICENSE for details.

"""
An AMP client which connects to and authenticates with an AMP server using OTP,
then issues a command.
"""

from twisted.internet.protocol import ClientCreator
from twisted.cred.credentials import UsernamePassword
from twisted.protocols.amp import AMP

from epsilon.react import react
from epsilon.ampauth import OTPLogin

from auth_server import Add


def add(proto):
    return proto.callRemote(Add, left=17, right=33)


def display(result):
    print result


def otpLogin(client):
    client.callRemote(OTPLogin, pad='pad')
    return client


def main(reactor):
    cc = ClientCreator(reactor, AMP)
    d = cc.connectTCP('localhost', 7805)
    d.addCallback(otpLogin)
    d.addCallback(add)
    d.addCallback(display)
    return d


if __name__ == '__main__':
    from twisted.internet import reactor
    react(reactor, main, [])
