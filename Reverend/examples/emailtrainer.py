#!/usr/bin/python

# This module is part of the Divmod project and is Copyright 2003 Amir Bakhtiar:
# amir@divmod.org.  This is free software; you can redistribute it and/or
# modify it under the terms of version 2.1 of the GNU Lesser General Public
# License as published by the Free Software Foundation.
#

from email.Message import Message
import email
import rfc822

class EmailItem(Message):
    def summary(self):
        return {
            'From': self.sender(),
            'Subject':self.get('subject','<No Subject>'),
        }

    def sender(self):
        fromHeader = self['from'] or '"Nobody" <nobody@nowhere>'
        hdrs = rfc822.AddressList(fromHeader).addresslist
        for dispname, addr in hdrs:
            dispname = dispname.strip().strip('"')
            addr = addr.strip()
            if dispname == '':
                dispname = addr
        return dispname

    def columnDefs(self):
        return [('From', 20), ('Subject', 30)]
    columnDefs = classmethod(columnDefs)

    def fromFile(self, fp):
        try:
            msg = email.message_from_file(fp, self)
        except email.Errors.MessageParseError:
            print 'bad message'
            return None
        return msg
    fromFile = classmethod(fromFile)

def runTrainer():
    from reverend.ui.trainer import Trainer
    from Tkinter import Tk
    from reverend.guessers.email import EmailClassifier
    root = Tk()
    root.title('Reverend Trainer')
    root.minsize(width=300, height=300)
    #root.maxsize(width=600, height=600)
    guesser = EmailClassifier()
    display = Trainer(root, guesser=guesser, itemClass=EmailItem)
    root.mainloop()

def runTester():
    from reverend.ui.tester import DirectoryExam
    de = DirectoryExam('spam', 'Spam', EmailItem)
    for m, ans in de:
        print m['from'], ans

    
if __name__ == "__main__":
    runTrainer()
    #runTester()
