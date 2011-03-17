
"""
Test the upgrade of L{UserInfo} from schema version 1 to 2, which collapsed the
I{firstName} attribute and I{lastName} attribute into a single I{realName}
attribute.
"""

from axiom.test.historic.stubloader import StubbedTest

from xmantissa.signup import UserInfo
from xmantissa.test.historic.stub_userinfo1to2 import FIRST, LAST

class UserInfoTests(StubbedTest):
    def test_realName(self):
        """
        L{UserInfo.realName} on the upgraded item should be set to the old
        values for the I{firstName} and I{lastName} attribute, separated by a
        space.
        """
        infoItem = self.store.findUnique(UserInfo)
        self.assertEqual(infoItem.realName, FIRST + u" " + LAST)
