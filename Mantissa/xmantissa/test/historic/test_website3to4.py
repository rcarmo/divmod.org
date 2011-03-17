
"""
Test for upgrading a WebSite by giving it a hostname attribute.
"""

from xmantissa.test.historic.test_website4to5 import WebSiteUpgradeTests

# Subclass it to make a TestCase with a __module__ which won't confuse trial
# and to make stub discovery work correctly.  These two things are implicitly
# discovered from the class definition are unfortunate. -exarkun
class WebSiteUpgradeTests(WebSiteUpgradeTests):
    # This website was so old, it had no hostname information.  So a default
    # will be filled in. -exarkun
    expectedHostname = u"localhost"
