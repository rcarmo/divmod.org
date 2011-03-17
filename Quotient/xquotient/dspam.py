# -*- test-case-name: xquotient.test.test_dspam -*-
from ctypes import CDLL, Structure, c_char_p, c_float, c_long, c_char
from ctypes import c_ulonglong, c_int, c_uint, c_void_p, POINTER
from ctypes import SetPointerType, RTLD_GLOBAL
import os, time

STORAGE_DRIVER="/usr/lib/dspam/libhash_drv.so"
DSPAM_LIB="/usr/lib/libdspam.so.7"

if not os.path.exists(STORAGE_DRIVER) or not os.path.exists(DSPAM_LIB):
    raise ImportError(STORAGE_DRIVER + " or " + DSPAM_LIB + " missing, dspam unavailable.")


def startDSPAM(user, home):
    """
    Load DSPAM and create a database handle.
    @param user: The username.
    @param home: The name of the DSPAM homedir
    """
    d = loadLibDSPAM(STORAGE_DRIVER)
    MTX = d.dspam_create(user, None, home, DSM_CLASSIFY, 0)
    return d

def userStats(user, home):
    """Returns the totals kept by DSPAM for a user."""
    d = startDSPAM(user, home)
    MTX = configureContext(d, user, home, DSM_CLASSIFY, DSR_NONE, DSR_NONE)
    d.dspam_addattribute(MTX, "SQLitePragma", "synchronous = OFF")
    d.dspam_attach(MTX, None)
    return dict([(x[0], getattr(MTX.contents.totals, x[0])) for x in MTX.contents.totals._fields_])

def train(user, home, spamDir, hamDir, verbose=False):
    """
    Mass training utility.

    Trains @C{user}'s database (in DSPAM home directory @C{home}) with
    spam and ham messages, stored one message per file in @C{spamDir}
    and @C{hamDir}. If @C{verbose} is true, progress is reported to
    stdout.
    """

    d = startDSPAM(user, home)
    spamCorpus = os.listdir(spamDir)
    nonspamCorpus = os.listdir(hamDir)

    while(spamCorpus or nonspamCorpus):
        if len(nonspamCorpus) > 0:
            count = 0
            msg = os.path.join(hamDir, nonspamCorpus.pop(0))
            testNonspam(msg, user, home, d, verbose)
            if len(spamCorpus) > 0:
                count = len(nonspamCorpus) / float(len(spamCorpus))
            for x in range(1, int(count)):
                msg = os.path.join(hamDir, nonspamCorpus.pop(0))
                testNonspam(msg, user, home, d, verbose)
                time.sleep(0.1) #XXX Going too fast makes dspam blow up sometimes. 

        if len(spamCorpus) > 0:
            count = 0
            msg = os.path.join(spamDir, spamCorpus.pop(0))
            testSpam(msg, user, home, d, verbose)
            if len(nonspamCorpus) > 0:
                count = len(spamCorpus) / float(len(nonspamCorpus))
            for x in range(1, int(count)):
                msg = os.path.join(spamDir, spamCorpus.pop(0))
                testSpam(msg, user, home, d,  verbose)
                time.sleep(0.1)
def classifyMessage(d, user, home, msg, train=True):
    """
    Classify a single message.

    @param d: the dspam library.
    @param user: The username.
    @param home: The name of the DSPAM homedir.
    @param msg: The actual text of the message.
    @param train: If true, this message will train the database with
    its tokens. If false, only a classification will be returned, with
    no modification to the database.

    @return: A 3-tuple containing the result of classification
    (DSR_ISSPAM or DSR_ISINNOCENT), a string describing the
    classification, and the confidence of the classification as a
    float.
    """
    if train:
        mode = DSM_PROCESS
    else:
        mode = DSM_CLASSIFY

    MTX = configureContext(d, user, home, mode, DSR_NONE, DSR_NONE)
    CTX = MTX.contents
    result = d.dspam_process(MTX, msg)
    if result:
        raise IOError(os.strerror(result))
    d.dspam_destroy(MTX)
    return CTX.result, CTX.class_, CTX.confidence

def classifyMessageWithGlobalGroup(d, user, groupname, userhome,
                                   globalhome, msg, train=True):
    """
    Classify a single message. If the user's filter hasn't been
    trained sufficiently, use the global filter.

    @param d: the dspam library.
    @param user: The username.
    @param groupname: The group name of the global filter.
    @param userhome: The name of the DSPAM homedir for the user.
    @param globalhome: the name of the DSPAM homedir for the global group.
    @param msg: The actual text of the message.
    @param train: If true, this message will train the database with
    its tokens. If false, only a classification will be returned, with
    no modification to the database.

    @return: A 3-tuple containing the result of classification
    (DSR_ISSPAM or DSR_ISINNOCENT), a string describing the
    classification, and the confidence of the classification as a
    float.
    """
    if train:
        mode = DSM_PROCESS
    else:
        mode = DSM_CLASSIFY

    MTX = configureContext(d, user, userhome, mode, DSR_NONE, DSR_NONE)
    CTX = MTX.contents
    result = d.dspam_process(MTX, msg)
    if (((CTX.totals.innocent_learned + CTX.totals.innocent_corpusfed < 1000) or
         (CTX.totals.spam_learned + CTX.totals.spam_corpusfed) < 250) and
        "Whitelisted" not in CTX.class_):
        d.dspam_destroy(MTX)
        MTX = configureContext(d, groupname, globalhome,
                               DSM_CLASSIFY, DSR_NONE, DSR_NONE)
        CTX = MTX.contents
        result = d.dspam_process(MTX, msg)

    if result:
        raise IOError(os.strerror(result))
    result, class_, conf = CTX.result, CTX.class_, CTX.confidence
    d.dspam_destroy(MTX)
    return result, class_, conf


def trainMessageFromError(d, user, home, msg, classification):
    """
    Re-train a message that was filed erroneously by the classifier.

    @param d: the dspam library.
    @param user: The username.
    @param home: The name of the DSPAM homedir.
    @param msg: The actual text of the message.
    @param classification: The actual class this message belongs in (DSR_ISSPAM or DSR_ISINNOCENT).
    """
    MTX = configureContext(d, user, home, DSM_PROCESS, classification, DSS_ERROR)
    result = d.dspam_process(MTX, msg)
    if result:
        raise IOError(os.strerror(result))
    d.dspam_destroy(MTX)

############################################################################


#config_shared.h

attrcell = POINTER("attribute_t")
class attribute_t(Structure):
    _fields_ = [("key", c_char_p),
                ("value", c_char_p),
                ("next", attrcell)]
SetPointerType(attrcell, attribute_t)
config_t = attribute_t

#nodetree.h

ntcell = POINTER("nt_node")
class nt_node(Structure):
    _fields_ = [("ptr", c_void_p),
                ("next", ntcell)]
SetPointerType(ntcell, nt_node)

class nt(Structure):
    _fields_ = [("first", POINTER(nt_node)),
                ("insert", POINTER(nt_node)),
                ("items", c_int),
                ("nodetype", c_int)]

#libdspam_objects.h

class _ds_spam_totals(Structure):
    _fields_ = [("spam_learned", c_long),
                ("innocent_learned", c_long),
                ("spam_misclassified", c_long),
                ("innocent_misclassified", c_long),
                ("spam_corpusfed", c_long),
                ("innocent_corpusfed", c_long),
                ("spam_classified", c_long),
                ("innocent_classified", c_long)]

class _ds_spam_signature(Structure):
    _fields_ = [("data", c_void_p),
                ("length", c_long)]

class _ds_message(Structure):
    _fields_ = [("components", POINTER(nt)),
                ("protect", c_int)]

class _ds_config(Structure):
    _fields_ = [("attributes", config_t),
                ("size", c_long)]

class DSPAM_CTX(Structure):
    _fields_ = [("totals", _ds_spam_totals),
                ("signature", POINTER(_ds_spam_signature)),
                ("message", POINTER(_ds_message)),
                ("config", POINTER(_ds_config)),
                ("username", c_char_p),
                ("group", c_char_p),
                ("home", c_char_p),
                ("operating_mode", c_int),
                ("training_mode", c_int),
                ("training_buffer", c_int),
                ("wh_threshold", c_int),
                ("classification", c_int),
                ("source", c_int),
                ("learned", c_int),
                ("flags", c_uint),
                ("algorithms", c_uint),

                ("result", c_int),
                ("class_", c_char * 32),
                ("probability", c_float),
                ("confidence", c_float),
                ("locked", c_int),
                ("storage", c_void_p),
                ("_process_start", c_long), #really time_t
                ("_sig_provided", c_int),
                ("factors", POINTER(nt))]

(DSF_CHAINED, DSF_SIGNATURE, DSF_BIAS, DSF_NOISE, DSF_WHITELIST,
DSF_MERGED, DSF_SBPH, DSF_UNLEARN) = [2**x for x in range(8)]

(DSA_GRAHAM, DSA_BURTON, DSA_ROBINSON, DSA_CHI_SQUARE, DSP_ROBINSON,
DSP_GRAHAM, DSP_MARKOV, DSA_NAIVE) = [2**x for x in range(8)]

DSM_PROCESS, DSM_TOOLS, DSM_CLASSIFY = range(3)
DSM_NONE = 0xFF

DST_TEFT, DST_TOE, DST_TUM = range(3)
DST_NOTRAIN, DST_DEFAULT = 0xFE, 0xFF

DSR_ISSPAM, DSR_ISINNOCENT, DSR_NONE = 0x1, 0x2, 0xFF

DSS_ERROR, DSS_CORPUS, DSS_INOCULATION = range(3)
DSS_NONE = 0xFF

TST_DISK, TST_DIRTY = 1, 2

DTT_DEFAULT, DTT_BNR = 0, 1

DSP_UNCALCULATED = -1

#sqlite_drv.h

class _sqlite_drv_storage(Structure):
    _fields_ = [("dbh", c_void_p),
                ("control_totals", _ds_spam_totals),
                ("merged_totals", _ds_spam_totals),
                ("control_token", c_ulonglong),
                ("control_sh", c_long),
                ("control_ih", c_long),
                ("iter_token", c_void_p),
                ("iter_sig", c_void_p),
                ("dir_handles", nt),
                ("dbh_attached", c_int)]

DSPAM_ALGORITHMS = DSA_GRAHAM | DSA_BURTON | DSP_GRAHAM
DSPAM_TRAININGBUFFER = 5
DSPAM_MODE =  DST_TOE

def configureContext(d, user, home, mode, classification, source):
    MTX = d.dspam_create(user, None, home, mode, DSF_CHAINED | DSF_NOISE | DSF_WHITELIST)
    d.dspam_addattribute(MTX, "HashRecMax", "98317")
    d.dspam_addattribute(MTX, "HashAutoExtend", "on")
    d.dspam_addattribute(MTX, "HashMaxExtents", "0")
    d.dspam_addattribute(MTX, "HashExtentSize", "49157")
    d.dspam_addattribute(MTX, "HashMaxSeek", "100")
    d.dspam_attach(MTX, None)
    CTX = MTX.contents
    CTX.algorithms = DSPAM_ALGORITHMS
    CTX.training_mode = DSPAM_MODE
    CTX.training_buffer = DSPAM_TRAININGBUFFER
    CTX.classification = classification
    CTX.source = source
    return MTX

def loadLibDSPAM(storageDriver, libName=DSPAM_LIB):
    if not os.path.exists(libName):
        raise RuntimeError("DSPAM library not found")
    if not os.path.exists(storageDriver):
        raise RuntimeError("DSPAM storage driver %s not found" % (storageDriver,))
    d = CDLL(libName, mode=RTLD_GLOBAL)
    d.dspam_create.restype = POINTER(DSPAM_CTX)
    d.dspam_create.argtypes = [c_char_p, c_char_p, c_char_p, c_int, c_uint]
    d.libdspam_init.argtypes = [c_char_p]
    d.dspam_addattribute.argtypes= [POINTER(DSPAM_CTX), c_char_p, c_char_p]
    d.dspam_attach.argtypes = [POINTER(DSPAM_CTX), c_void_p]
    d.dspam_destroy.argtypes = [POINTER(DSPAM_CTX)]
    d.dspam_process.argtypes = [POINTER(DSPAM_CTX), c_char_p]
    d.libdspam_init(storageDriver)
    return d


def testNonspam(msgFile, user, home, d, verbose):
    if isinstance(msgFile, basestring):
        msgFile = open(msgFile)
    msg = msgFile.read()
    if verbose:
        print ("[test: nonspam] " + (os.path.split(msgFile.name)[1] + " " * 32)[:32] + " result:"),
    result, class_, conf = classifyMessage(d, user, home, msg, train=True)
    if result != DSR_ISINNOCENT:
        if verbose:
            print "FAIL (%s %s)" % (result, class_)
        trainMessageFromError(d, user, home, msg, DSR_ISINNOCENT)
    else:
        if verbose:
            print "PASS: %s %s" % (result, class_)

def testSpam(msgFile, user, home, d, verbose):
    if isinstance(msgFile, basestring):
        msgFile = open(msgFile)
    msg = msgFile.read()
    if verbose:
        print ("[test: spam   ] " + (os.path.split(msgFile.name)[1] + " " * 32)[:32] + " result:"),
    result, class_, conf = classifyMessage(d, user, home, msg, train=True)

    if result != DSR_ISSPAM:
        if verbose:
            print "FAIL (%s, %s)" % (result, class_)
        trainMessageFromError(d, user, home, msg, DSR_ISSPAM)
    else:
        if verbose:
            print "PASS: %s %s" % (result, class_)

