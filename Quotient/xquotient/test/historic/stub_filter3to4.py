# -*- test-case-name: xquotient.test.historic.test_filter3to4 -*-

"""
Stub database generator for version 3 of L{Filter}.
"""

from axiom.test.historic.stubloader import saveStub
from axiom.dependency import installOn

from xquotient.spam import Filter

USE_POSTINI_SCORE = True
POSTINI_THRESHHOLD = 0.5


def createDatabase(store):
    installOn(
        Filter(store=store, usePostiniScore=USE_POSTINI_SCORE,
               postiniThreshhold=POSTINI_THRESHHOLD),
        store)


if __name__ == '__main__':
    saveStub(createDatabase, 17723)
