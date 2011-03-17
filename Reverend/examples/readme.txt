This brief readme is designed to help you get
started with using the Reverend training and
testing UI.

This is how I use the trainer.

I first prepare a couple of directories full of
email. One will have a mix of all kinds of email
that I want to classify and one for testing that
is, say, containing only spam files.

I type:
    python emailtrainer.py

I click on the 'New Pool' button and create a
pool for each category or bucket that I want to
classify the data into. e.g. 'Clean' and 'Spam'.

I use the radio buttons to classify the emails.
I page back and forth to make sure that new
training does not undo old training.

Once I am happy with the training. I click 'Save'
to save the Reverend data. I can load it later
and continue training.

When I want to test, I load the Reverend data
using the 'Load' button. I then click on the
'Testing' button on the left. I click 'Run
Test' which brings up the first of 2 dialogs,
asking me to select the test data, e.g. my
directory full of spam. The next dialog asks
for the correct answer to this set of messages.
I type in 'Spam' (case must match your pool name).

I have lots of improvements in mind from training
reinforcement to better testing and analysis.

The trainer is designed to be data-agnostic. Look
at example/emailtrainer.py to see how you can
simply wrap your domain objects and make them
place nice with the UI.

Enjoy,
-A-
