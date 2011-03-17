
"""
Tests for upgrading a WebSite to move the L{IProtocolFactoryFactory} parts onto
a separate item.
"""

from xmantissa.test.historic.test_website4to5 import WebSiteUpgradeTests

# Subclass it to make a TestCase with a __module__ which won't confuse trial
# and to make stub discovery work correctly.  These two things are implicitly
# discovered from the class definition are unfortunate. -exarkun
class WebSiteUpgradeTests6(WebSiteUpgradeTests):
    pass
