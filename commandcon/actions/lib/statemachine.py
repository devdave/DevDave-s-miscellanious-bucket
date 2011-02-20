import sys


class ConsoleCls(object):
    isConsoleFriendly = True

def console(f):
    f.isConsoleFriendly = True
    return f


class StateMachine(object):
    """
        In the short-term this is a great idea, but I can see this burying me later
        due to potential interdependancies
    """
    locals    = None
    suspects  = None
    argsc     = 0
    args      = None
    __booted = False
    def __init__(self, locals = None, suspects = None, argsc = None, args = None):
        """
           Only required argument is
           :locals which should be a data structure like the product created from locals()
           
           everything else is there to allow for unit-testing
        """
        if StateMachine.__booted == True:
            return
        
        StateMachine.locals = locals
        if suspects:
            StateMachine.suspects = suspects
        else:
            self.filterLocals()
        
        #cut off the executable as its not needed
        StateMachine.argsc = argsc or len(sys.argv[1:]) 
        StateMachine.args  = args or sys.argv[1:]
        
        StateMachine.__booted = True
            
        self.process()
    
    def filterLocals(self):
        StateMachine.suspects = {}
        for k,v in self.locals.items():
            if k[0] == "_": continue
            if not hasattr(v,"isConsoleFriendly"): continue
            if v.isConsoleFriendly != True: continue
            self.suspects[k] = v    
            
    
    def process(self):
        if self.argsc <= 0:
            print "Available actions"
            for suspect, action in self.suspects.items():
                
                print "\t", suspect.ljust(25),
                if hasattr(action, "summary"):
                    print action.summary,
                print
        else:
            self.executeAction(self.args[0])
            
    def fetchSuspect(self, actionName):
        return self.suspects[actionName]
        
    def executeAction(self, actionName):        
        if actionName in self.suspects:
            action = self.fetchSuspect(actionName)
            action()
        else:
            raise ValueError("Unable to find appropriate action %s" % actionName)