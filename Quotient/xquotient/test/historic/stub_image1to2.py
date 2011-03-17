from axiom.test.historic.stubloader import saveStub

from xquotient.extract import Image
from xquotient.mimestorage import Part
from xquotient.exmess import Message


def createDatabase(s):
    Image(store=s,
          part=Part(store=s),
          message=Message(store=s,
                          subject=u'Hello!'),
          mimeType=u'foo/bar',
          thumbnailPath=s.newFilePath('foo', 'bar'))

if __name__ == '__main__':
    saveStub(createDatabase, 7052)
