
"""
Create an axiom database configured with Mantissa, add a user with a POP3
grabber, run the POP3 grabber against a POP3 server which we also start up, and
run until all messages have been retrieved.
"""

import os

from twisted.python import filepath

from epsilon import extime
from epsilon.scripts import benchmark

from axiom import scheduler

from xquotient import grabber
from xquotient.benchmarks.benchmark_initialize import initializeStore
from xquotient.benchmarks.observer import StoppingMessageFilter

# Number of messages which will be downloaded before we shut down.
TOTAL_MESSAGES = 50

def main():
    s, userStore = initializeStore()
    g = grabber.POP3Grabber(
        store=userStore,
        username=u"testuser",
        password=u"password",
        domain=u"127.0.0.1",
        port=12345)
    scheduler.IScheduler(userStore).schedule(g, extime.Time())
    StoppingMessageFilter(store=userStore,
                          totalMessages=TOTAL_MESSAGES).installOn(userStore)

    pop3server = filepath.FilePath(__file__).sibling("pop3server.tac")
    os.system("twistd -y " + pop3server.path)
    benchmark.start()
    os.system("axiomatic -d wholesystem.axiom start -n")
    benchmark.stop()
    os.system("kill `cat twistd.pid`")


if __name__ == '__main__':
    main()
