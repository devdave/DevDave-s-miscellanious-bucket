
from lib.statemachine import (StateMachine, ConsoleCls,)


class help(ConsoleCls):
    """Displays any help/doc information on a console action"""
    summary = "help actionName ..."    
    def __init__(self):
        
        if StateMachine.argsc == 1:
            print self.__doc__
        else:
            #assume 0 := executable, 1 := help, 2 > is help target
            target = StateMachine.args[1]            
            suspect = StateMachine().fetchSuspect(target)
            print suspect.__doc__.strip()