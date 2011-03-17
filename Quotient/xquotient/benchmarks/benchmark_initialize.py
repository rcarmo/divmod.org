
"""
Create an axiom database configured with Mantissa, an admin user, and a test
user with all of Quotient's benefactors applied to it.
"""

import os

from twisted import plugin
from twisted.python import filepath

from epsilon.scripts import benchmark

from axiom import store, userbase
from axiom.dependency import installOn

import xmantissa.plugins
from xmantissa import offering


def initializeStore():
    # XXX TODO - There should be an API that is as easy to use as this crap.
    wsa = filepath.FilePath("wholesystem.axiom")
    if wsa.exists():
        wsa.remove()
    PFX = "axiomatic -d wholesystem.axiom "
    for cmd in [
        PFX + "mantissa --admin-password password",
        PFX + "offering install Quotient",
        PFX + " userbase create testuser localhost password"]:
        os.system(cmd)

    s = store.Store('wholesystem.axiom')
    ls = s.findUnique(userbase.LoginSystem)
    user = ls.accountByAddress(u'testuser', u'localhost')
    userStore = user.avatars.open()

    for off in offering.getInstalledOfferings(s).values():
        for p in off.installablePowerups:
            installOn(p, userStore)

    return s, userStore


def main():
    benchmark.start()
    initializeStore()
    benchmark.stop()

if __name__ == '__main__':
    main()
