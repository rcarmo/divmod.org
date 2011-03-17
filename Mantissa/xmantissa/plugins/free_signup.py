
from xmantissa import signup

freeTicket = signup.SignupMechanism(
    name = 'Free Ticket',
    description = '''
    Create a page which will allow anyone with a verified email
    address to sign up for the system.  When the user enters their
    email address, a confirmation email is sent to it containing a
    link which will allow signup to proceed.  When the link is
    followed, an account will be created and endowed by the
    benefactors associated with this instance.
    ''',
    itemClass = signup.FreeTicketSignup,
    configuration = signup.freeTicketSignupConfiguration)

userInfo = signup.SignupMechanism(
    name = 'Required User Information',
    description = '''
    Create a signup mechanism with several self-validating fields.

    This will also require the user to select a local username before the
    account is created, and it will create the account immediately rather than
    waiting for the ticket to be claimed.
    ''',
    itemClass = signup.UserInfoSignup,
    configuration = signup.freeTicketSignupConfiguration)
