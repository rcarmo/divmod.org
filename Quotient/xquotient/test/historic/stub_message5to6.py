from axiom.dependency import installOn
from axiom.scheduler import SubScheduler
from xquotient.mimestorage import IncomingMIMEMessageStorer
from axiom.test.historic.stubloader import saveStub

msg = """\
Received: from psmtp.com ([64.18.1.159] helo=psmtp.com)
        by divmod.com with ESMTP (Quotient beta 28 (0.9.2+build 184))
        for example@divmod.com; Thu, 21 Jun 2007 09:28:19 -0400
Message-ID: <467A7CDD.8010403@gmail.com>
Date: Thu, 21 Jun 2007 09:27:57 -0400
From: Bob <bob@example.org>
To: Alice <example@divmod.com>
Subject: Fwd: Fwd: Re: Re: re: RE: you have to see this
Content-Type: multipart/mixed;
 boundary="------------000701040003040406010604"

This is a multi-part message in MIME format.
--------------000701040003040406010604
Content-Type: text/plain; charset=ISO-8859-1; format=flowed
Content-Transfer-Encoding: 7bit

la ti da

--------------000701040003040406010604
Content-Type: message/rfc822;
 name="Re: reminder"
Content-Transfer-Encoding: 7bit
Content-Disposition: inline;
 filename="Re: reminder"

Received: by 10.100.6.19 with SMTP id 19cs181330anf;
        Wed, 20 Jun 2007 21:07:17 -0700 (PDT)
From: "Carol" <carol@example.org>
To: bob@example.org
Subject: Fwd: Re: Re: re: RE: you have to see this
Date: Thu, 21 Jun 2007 00:05:45 -0400
Content-Type: multipart/mixed;
        boundary="----=_NextPart_000_0085_01C7B397.EB1676A0"
Message-Id: <20070621040711.0A0DACED40@spaceymail-mx1.g.dreamhost.com>

This is a multi-part message in MIME format.

------=_NextPart_000_0085_01C7B397.EB1676A0
Content-Type: text/plain;
        charset="US-ASCII"
Content-Transfer-Encoding: 7bit

tirra lirra

------=_NextPart_000_0085_01C7B397.EB1676A0
Content-Type: image/jpeg;
        name="image-1.jpg"
Content-Transfer-Encoding: base64
Content-Disposition: attachment;
        filename="image-1.jpg"

some jpeg stuff I don't know really

------=_NextPart_000_0085_01C7B397.EB1676A0--



--------------000701040003040406010604--
"""

def createDatabase(s):
    installOn(SubScheduler(store=s), s)
    mms = IncomingMIMEMessageStorer(
        s, s.newFile("mail", "1.eml"),
        u'migration://migration')
    for line in msg.splitlines():
        mms.lineReceived(line)
    mms.messageDone()

    assert len(list(mms.message.impl.walk())) == 3

if __name__ == '__main__':
    saveStub(createDatabase, 12949)
