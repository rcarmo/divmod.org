"""
Database-creation script for testing the version 2 to version 3 upgrader of
L{Mugshot}.
"""
from twisted.python.filepath import FilePath

from axiom.test.historic.stubloader import saveStub
from xmantissa.people import Mugshot, Person


MUGSHOT_TYPE = u'image/png'
MUGSHOT_BODY_PATH_SEGMENTS = ('mugshot',)



def createDatabase(store):
    """
    Make L{Person} and L{Mugshot} items.  Set the C{body} and C{smallerBody}
    attributes of the L{Mugshot} item to point at a copy of
    I{xmantissa/test/resources/square.png} beneath the store's directory.
    """
    atomicImageFile = store.newFile(*MUGSHOT_BODY_PATH_SEGMENTS)
    imageFilePath = FilePath(__file__).parent().parent().child(
        'resources').child('square.png')
    atomicImageFile.write(imageFilePath.getContent())
    atomicImageFile.close()

    Mugshot(store=store,
            person=Person(store=store),
            body=atomicImageFile.finalpath,
            smallerBody=atomicImageFile.finalpath,
            type=MUGSHOT_TYPE)



if __name__ == '__main__':
    saveStub(createDatabase, 13812)
