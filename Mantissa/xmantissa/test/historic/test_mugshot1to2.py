from twisted.trial.unittest import SkipTest
from axiom.test.historic import stubloader
from xmantissa.people import Mugshot, Person

class MugshotTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        try:
            from PIL import Image
        except ImportError:
            raise SkipTest('PIL is not available')

        m = self.store.findUnique(Mugshot)
        p = self.store.findUnique(Person)

        self.assertIdentical(m.person, p)
        self.assertEqual(p.name, 'Bob')

        img = Image.open(m.smallerBody.open())
        self.assertEqual(img.size, (m.smallerSize, m.smallerSize))
