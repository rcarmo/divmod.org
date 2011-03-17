# -*- test-case-name: xmantissa.test.test_offering -*-
# Copyright 2008 Divmod, Inc. See LICENSE file for details
"""
Axiomatic commands for manipulating Mantissa offerings.
"""

from twisted.python import usage
from axiom.scripts import axiomatic

from xmantissa import offering, publicweb

class Install(axiomatic.AxiomaticSubCommand):
    synopsis = "<offering>"

    def parseArgs(self, offering):
        self["offering"] = self.decodeCommandLine(offering)

    def postOptions(self):
        for o in offering.getOfferings():
            if o.name == self["offering"]:
                offering.installOffering(self.store, o, None)
                break
        else:
            raise usage.UsageError("No such offering")

class List(axiomatic.AxiomaticSubCommand):
    def postOptions(self):
        for o in offering.getOfferings():
            print "%s: %s" % (o.name, o.description)



class SetFrontPage(axiomatic.AxiomaticSubCommand):
    """
    Command for selecting the site front page.
    """

    def parseArgs(self, offering):
        """
        Collect an installed offering's name.
        """
        self["name"] = self.decodeCommandLine(offering)


    def postOptions(self):
        """
        Find an installed offering and set the site front page to its
        application's front page.
        """
        o = self.store.findFirst(
            offering.InstalledOffering,
            (offering.InstalledOffering.offeringName ==
             self["name"]))
        if o is None:
            raise usage.UsageError("No offering of that name"
                                   " is installed.")
        fp = self.store.findUnique(publicweb.FrontPage)
        fp.defaultApplication = o.application



class OfferingCommand(axiomatic.AxiomaticCommand):
    name = "offering"
    description = "View and accept the offerings of puny mortals."

    subCommands = [
        ("install", None, Install, "Install an offering."),
        ("list", None, List, "List available offerings."),
        ("frontpage", None, SetFrontPage,
         "Select an application for the front page."),
        ]

    def getStore(self):
        return self.parent.getStore()

