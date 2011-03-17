from axiom.test.historic import stubloader

from xquotient.exmess import Message
from xquotient.mimestorage import Part
from xquotient.gallery import Image

class ImageUpgradeTest(stubloader.StubbedTest):
    def testUpgrade(self):
        image = self.store.findUnique(Image)
        self.assertIdentical(image.part, self.store.findUnique(Part))
        self.assertIdentical(image.message, self.store.findUnique(Message))
        self.assertEquals(image.message.subject, 'Hello!')
        self.assertEquals(image.mimeType, 'foo/bar')
        self.assertEquals(image.thumbnailPath, self.store.newFilePath('foo', 'bar'))
        self.failUnless(image.imageSet is None)
