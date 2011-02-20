

from lib.statemachine import (StateMachine, console)


@console
def simple(*args, **kwargs):
    """ A simple example of how this works """
    print "I am a silly little simple function!"
    print "K, I am done now!"
    
simple.summary = "A simple action"    