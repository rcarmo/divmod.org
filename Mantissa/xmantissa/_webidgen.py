import random

maxLongInt = (2**63)-1

def genkey():
    """
    Generate a key (an int representing 16 bytes of random data).
    """
    return random.randint(0, maxLongInt)

def _swapat(key, n):
    # n: 0-8; a swap is an 8-bit value; 2 ints between 0-15
    return (key >> ((8 * (n))+4)) & 0xf, (key >> (8 * n)) & 0xf

def _swap(l, a, b):
    l[a], l[b] = l[b], l[a]

def webIDToStoreID(key, webid):
    """
    Takes a webid (a 16-character str suitable for including in URLs) and a key
    (an int, a private key for decoding it) and produces a storeID.
    """
    if len(webid) != 16:
        return None
    try:
        int(webid, 16)
    except TypeError:
        return None
    except ValueError:
        return None
    l = list(webid)
    for nybbleid in range(7, -1, -1):
        a, b = _swapat(key, nybbleid)
        _swap(l, b, a)
    i = int(''.join(l), 16)
    return i ^ key

def storeIDToWebID(key, storeid):
    """
    Takes a key (int) and storeid (int) and produces a webid (a 16-character
    str suitable for including in URLs)
    """
    i = key ^ storeid
    l = list('%0.16x' % (i,))
    for nybbleid in range(0, 8):
        a, b = _swapat(key, nybbleid)
        _swap(l, a, b)
    return ''.join(l)

def _test():
    for y in range(100):
        key = genkey()
        print 'starting with key', key, hex(key)
        for sid in range(1000):
            wid = storeIDToWebID(key, sid)
            sid2 = webIDToStoreID(key, wid)
            assert sid == sid2, '%s != %s [%r %r]' % (sid, sid2, wid, key)
            #print wid, '<=>', sid, ':', hex(key)


def _simpletest():
    key = 0xfedcba9876543210
    web = storeIDToWebID(key, 100)
    print 'web', repr(web)
    sid = webIDToStoreID(key, web)
    print 'store', hex(sid)

if __name__ == '__main__':
    _test()
