from nevow import athena

from xmantissa.fragmentutils import dictFillSlots
from xmantissa.webtheme import getLoader

class SenderPersonFragment(athena.LiveFragment):
    """
    Fragment which renders the email address and name of a person who is not
    in the address book, but could be added
    """
    # FIXME this thing should be renamed and moved out of this module
    jsClass = u'Quotient.Common.SenderPerson'

    def __init__(self, email):
        """
        @param email: an email address
        @type email: L{xquotient.mimeutil.EmailAddress}
        """
        self.email = email
        athena.LiveFragment.__init__(
            self, docFactory=getLoader('sender-person'))

    def render_senderPerson(self, ctx, data):
        return dictFillSlots(
                ctx.tag, dict(name=self.email.anyDisplayName(),
                              identifier=self.email.email))
