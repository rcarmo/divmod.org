from twisted.python.filepath import FilePath

from axiom.test.historic.stubloader import saveStub
from xmantissa.people import Mugshot, Person

def createDatabase(s):
    imgfile = FilePath(__file__).parent().parent().child('resources').child('square.png')
    outfile = s.newFile('the-image')
    outfile.write(imgfile.getContent())
    outfile.close()

    Mugshot(store=s,
            person=Person(store=s, name=u'Bob'),
            body=outfile.finalpath,
            type=u'image/png')

if __name__ == '__main__':
    saveStub(createDatabase, 7671)
