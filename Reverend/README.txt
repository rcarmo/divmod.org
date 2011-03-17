Reverend is a simple Bayesian classifier.
It is designed to be easy to adapt and extend for
your application.

A simple example would look like:

from reverend.thomas import Bayes

guesser = Bayes()
guesser.train('fish', 'salmon trout cod carp')
guesser.train('fowl', 'hen chicken duck goose')

guesser.guess('chicken tikka marsala')

You can also "forget" some training:
guesser.untrain('fish','salmon carp')

The first argument of train is the bucket or class that
you want associated with the training. If the bucket does
not exists, Bayes will create it. The second argument
is the object that you want Bayes to be trained on. By
default, Bayes expects a string and uses something like
string.split to break it into indidual tokens (words).
It uses these tokens as the basis of its bookkeeping.


The two ways to extend it are:
1. Pass in a function as the tokenizer when creating
   your Bayes. The function should expect one argument
   which will be whatever you pass to the train() method.
   The function should return a list of strings, which
   are the tokens that are relevant to your app.

2. Subclass Bayes and override the method getTokens to
   return a list of string tokens relevant to your app.


I hope all you guesses are right,
amir@divmod.org
