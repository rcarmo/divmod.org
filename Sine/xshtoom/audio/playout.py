# from the Python Standard Library
from bisect import bisect
import sys

# from the Twisted library
from twisted.internet import reactor
from twisted.python import log

# TODO's
#  * think about persistent clock skew (the RTP book by Perkins has an extensive discussion and sophisticated algorithm for this)
#  * measure (callLater lag, jitter, clock skew,)
#  * add more livetests
#  * minimize playout buffer. The only reason for the large size
#  of PLAYOUT_BUFFER -- currently 0.8 seconds (!!!) is because we
#  didn't have a precise way to get our Python called *just* before
#  the audio output FIFO underran, on Mac. Such a precise way has been
#  added on Mac thanks to Bob Ippolito. The thing to do on Mac is use
#  the callback Bob provided, which means "the audio output buffer
#  is on the verge of running dry" to move the next packet's worth
#  of audio from jitter buffer to output device FIFO. That is: call
#  "consider_playing_out_sample()" from the audio device's "I'm about to
#  run dry" callback, instead of from a reactor.callLater(). Hopefully
#  similar things could be done on Linux and w32 as well. This *might*
#  trigger a cleanup of this code, because the event that comes from the
#  audio device saying "okay I've just about finished playing those 20
#  ms you gave me" and the event that comes from "hey a network packet
#  arrived with some audio data in it" could be probably be completely
#  separate from each other and each could probably be simpler...

if 'darwin' in sys.platform.lower():
    # stuff up to this many seconds worth of packets into the audio output buffer
    PLAYOUT_BUFFER_SECONDS=0.8
else:
    PLAYOUT_BUFFER_SECONDS=0.03
# store up to this many seconds worth of packets in the jitter buffer before
# switching to playout mode
JITTER_BUFFER_SECONDS=0.8
# if we have this many or more seconds worth of packets, drop the oldest ones
# in order to catch up
CATCHUP_TRIGGER_SECONDS=1.4

EPSILON=0.0001

import time

DEBUG=False
#DEBUG=True

def is_run(packets, i, runsecs):
    """
        Returns True iff packets contains a run of sequential packets starting at
        index i and extending at least runsecs seconds in aggregate length.
    """
    runbytes = runsecs * 16000
    firstseq = packets[i][0]
    runbytessofar = 0
    i2 = 0
    while runbytessofar < runbytes:
        if len(packets) <= i + i2:
            return False
        if packets[i + i2][0] != firstseq + i2:
            return False
        runbytessofar += len(packets[i + i2][1])
        i2 += 1
    return True

class Playout:
    """
    Theory of operation: you have two modes: "playout" mode and "refill" mode.
    When you are in playout mode then you play out sequential audio packets from
    your jitter buffer to the audio output device's FIFO as needed.  Do the
    obvious right thing with out-of-order packets.

    You switch to refill mode when you have a buffer underrun -- that is not
    enough in-order data came in from the network so the audio output device
    (i.e., the speaker) ran dry.  When you are in refill mode, you don't send
    any packets to the audio output device, but instead hoard them until you
    have JITTER_BUFFER_SECONDS worth of sequential, in-order data ready, and
    then switch to playout mode.

    There's an added complication because this code doesn't currently have a
    nice clean way to say "write this 20 milliseconds worth of audio to the
    output device\'s FIFO, and then run the following method *just* before those
    20 milliseconds are all used up".  This complication is called the "playout
    buffer", and it is a way to stuff way more than 20 milliseconds worth of
    audio into the audio output device's FIFO, so that we'll get a chance to add
    more packets before it underruns, even when reactor.callLater() sometimes
    gets called 110 milliseconds later than we wanted.  This happens on Mac.
    See TODO item about playout buffer in comments above.
    """
    def __init__(self, medialayer):
        self.medialayer = medialayer
        self.b = [] # (seqno, bytes,)
        # the sequence number of the (most recent) packet which has gone to
        # the output device
        self.s = 0
        # the time at which the audio output device will have nothing to play
        self.drytime = None
        self.refillmode = True # we start in refill mode
        self.nextcheckscheduled = None
        self.st = time.time()
        self.stopping = False

    def close(self):
        self.stopping = True

    def _schedule_next_check(self, delta, t=time.time):
        if self.nextcheckscheduled:
            return
        self.nextcheckscheduled = reactor.callLater(delta, self._do_scheduled_check)
        if DEBUG:
            log.msg("scheduling next check. now: %0.3f, then: %0.3f, drytime: %0.3f" %
                    (t() - self.st, self.nextcheckscheduled.getTime() - self.st,
                    self.drytime - self.st,))

    def _do_scheduled_check(self, t=time.time):
        if self.stopping:
            return
        if DEBUG:
            log.msg("doing scheduled check at %0.3f == %0.3f late" %
                    (t() - self.st, t()-self.nextcheckscheduled.getTime()))
        self.nextcheckscheduled = None
        self._consider_playing_out_sample()

    def _consider_playing_out_sample(self, t=time.time, newsampseqno=None):
        if not self.b or self.b[0][0] != (self.s + 1):
            # We don't have a packet ready to play out.
            if t() >= self.drytime:
                self._switch_to_refill_mode()
            return

        if self.drytime and (t() >= self.drytime) and ((not newsampseqno) or
                                                    (newsampseqno != (self.s + 1))):
            log.msg(("output device ran dry unnecessarily! now: %0.3f, "+
                    "self.drytime: %s, nextseq: %s, newsampseqno: %s") %
                    (t() - self.st, self.drytime - self.st, self.b[0][0], newsampseqno,))

        # While the output device would run dry within PLAYOUT_BUFFER_SECONDS from
        # now, then play out another sample.
        while ((t() + PLAYOUT_BUFFER_SECONDS >= self.drytime)
                            and self.b and self.b[0][0] == (self.s + 1)):
            (seq, bytes,) = self.b.pop(0)
            self.medialayer._d.write(bytes)
            self.s = seq
            packetlen = len(bytes) / float(16000)
            if self.drytime is None:
                self.drytime = t() + packetlen
            else:
                self.drytime = max(self.drytime + packetlen, t() + packetlen)
            if DEBUG:
                log.msg("xxxxx %0.3f played %s, playbuflen ~= %0.3f, jitterbuf: %d:%s"
                        % (t() - self.st, seq, self.drytime and
                        (self.drytime - t()) or 0, len(self.b),
                        [x[0] for x in self.b],))

        # If we filled the playout buffer then come back and consider refilling it
        # after it has an open slot big enough to hold the next packet.  (If we
        # didn't just fill it then when the next packet comes in from the network
        # self.write() will invoke self._consider_playing_out_sample().)
        if self.b and self.b[0][0] == (self.s + 1):
            # Come back and consider playing out again after we've played out an
            # amount of audio equal to the next packet.
            self._schedule_next_check(len(self.b[0][1]) / float(16000) + EPSILON)


    def _switch_to_refill_mode(self):
        self.refillmode = True
        self._consider_switching_to_play_mode()

    def _consider_switching_to_play_mode(self):
        # If we have enough sequential packets ready, then we'll make them be the
        # current packets and switch to play mode.
        for i in range(len(self.b) - 1):
            if is_run(self.b, i, JITTER_BUFFER_SECONDS):
                self.b = self.b[i:]
                self.s = self.b[0][0] - 1 # prime it for the next packet
                self.refillmode = False
                self._consider_playing_out_sample()
                return

    def write(self, bytes, seq, t=time.time):
        assert isinstance(bytes, basestring)

        if not bytes:
            return 0

        i = bisect(self.b, (seq, bytes,))
        if i > 0 and self.b[i-1][0] == seq:
            log.msg("xxx duplicate packet %s" % seq)
            return

        self.b.insert(i, (seq, bytes,))

        if DEBUG:
            log.msg("xxxxx %0.3f added  %s, playbuflen ~= %0.3f, jitterbuf: %d:%s"
                % (t() - self.st, seq, self.drytime and (self.drytime - t()) or 0,
                len(self.b), [x[0] for x in self.b],))
        if self.refillmode:
            self._consider_switching_to_play_mode()
        else:
            self._consider_playing_out_sample(newsampseqno=seq)
            if (self.b and (self.b[0][0] == self.s + 1) and
                        is_run(self.b, 0, CATCHUP_TRIGGER_SECONDS)):
                (seq, bytes,) = self.b.pop(0) # catch up
                log.msg("xxxxxxx catchup! dropping %s" % seq)
                self.s = self.b[0][0] - 1 # prime it for the next packet

class NullPlayout:
    def __init__(self, medialayer):
        self.medialayer = medialayer

    def write(self, bytes, seq, t=time.time):
        self.medialayer._d.write(bytes)

#Playout=NullPlayout
