
"""
Create an axiom database configured with Mantissa, add a user with an SMTP
account, send a pile of email messages to them and run until they have all been
received.
"""

import sys
from os import system

from twisted.python.filepath import FilePath

from epsilon.scripts.benchmark import start, stop

from xquotient.mail import MailTransferAgent

from xquotient.benchmarks.benchmark_initialize import initializeStore
from xquotient.benchmarks.observer import StoppingMessageFilter

TOTAL_MESSAGES = 50

def main():
    s, userStore = initializeStore()

    MailTransferAgent(store=userStore).installOn(userStore)
    MailTransferAgent(store=s, portNumber=12345).installOn(s)

    StoppingMessageFilter(store=userStore,
                          totalMessages=TOTAL_MESSAGES).installOn(userStore)

    smtpclient = FilePath(__file__).sibling('smtpclient.tac')
    system("SMTP_SERVER_PORT=%d "
           "SMTP_MESSAGE_COUNT=%d "
           "SMTP_RECIPIENT_ADDRESS=%s "
           "twistd -y %s" % (12345, TOTAL_MESSAGES, "testuser@localhost", smtpclient.path))
    start()
    system("axiomatic -d wholesystem.axiom start -n")
    stop()
    system("kill `cat twistd.pid`")



if __name__ == '__main__':
    main()
