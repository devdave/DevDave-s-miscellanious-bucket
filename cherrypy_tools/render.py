import os
from os import path

try:
    from mako.template import Template
    from mako.lookup import TemplateLookup
except ImportError:
    print "You need Mako installed"

try:
    from config import AppConf
except ImportError:
    print "You need to replace or add this, config.py:def AppConf() which is a stateless config fetcher"
    """
        def AppConf(key = None):
    
            conf = {
                "template.path": path.join(HERE, "templates")
                , "template.cpath": path.join(HERE, "compiled")        
            }
            conf['couchdb.url'] = "http://%s:%s@%s" % (conf['couchdb.user'], conf['couchdb.pass'], conf['couchdb.host'])
            
            return conf.get(key) if key else conf
    """




class Render(object):
    """
        Given rootPath & cachePath, manage the details of rendering a given template path with a provided
        dict called params.
        
        BTW, semi-important but this also automatically creates the template file if it doesn't exist!
        
    """    
    rootPath = AppConf("template.path")
    cachePath = AppConf("template.cpath")
    makoLookup = TemplateLookup(directories=[AppConf("template.path")], default_filters = ['decode.utf8'])
    
    def __init__(self, pathname, params = None):
        """
            pathname is a relative path like /controller/actionName ( suffix is ALWAYS assumed to be .mako )            
        """
        
        keys = {}
        rootName = "%s.mako" % pathname if not pathname.endswith('.mako') else path.join(self.rootPath, pathname)
        rootPath = path.join(self.rootPath, rootName )
        
        keys['filename'] = rootPath        
        keys['module_directory'] = self.cachePath
        keys['lookup']  = self.makoLookup
        
        
        try:
            self.template = Template(**keys)
        except OSError:
            #@TODO add a dev flag or something
            dirname = path.dirname( rootPath )
            split = dirname.split("/")
            if not os.path.exists(dirname):
                for i in range(len(split)):
                    try:
                        root = "/".join(split[:i+1])
                        if not path.exists(root):
                            os.mkdir(root)
                            
                    except IndexError:
                        raise ValueError("Unable to build %s path" % keys['filename'])
            
#HEY - Look here
            #if a template doesn't exist, this automatically creates it, which is lazy but conveniant when building a product
            with open(rootPath, 'wa') as templateObj:
                templateObj.write("%s" % rootPath)            
            
            self.template = Template(**keys)
            
        self.params = params if params is not None else {}
        self.path = path
        
    #These are not perfect as they will hide mispellings and absence of values... but I am fine with that
    def __getitem__(self, key, default = None):
        return self.params.get(key, default)
    
    #These are not perfect as they will hide mispellings and absence of values... but I am fine with that
    def __setitem__(self, key, value):
        self.params[key] = value
        return self.params[key]
    
    #These are not perfect as they will hide mispellings and absence of values... but I am fine with that
    def __delitem__(self, key, default = None):
        return self.params.pop(key, default)
    
        
    def __contains__(self, key):
        return key in self.params
    
    def gen(self):
        return self.template.render(**self.params)
        
    def __str__(self):
        return self.gen()
    
from functools import wraps

def AutoRender(f):
    """
        Usage example -
        
        class MyController:
     
          @AutoRender
          def action(self):
              result = do_stuff()
              return { result: result }
              
        will automatically try to render a template @ template.path/mycontroller/action.mako
        while also exposing the method to the Cherrypy routing system.
        
    """
    name =  f.__name__
    f.exposed = True
    #raise Exception([ name, [(k, getattr(f,k),"\n",) for k in dir(f)]])
    
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        cls = self.__class__.__name__.lower()
        result = f(self, *args, **kwargs)
        pathname = "%s/%s" % (cls, name, )
        
        return Render(pathname , result ).gen()
        
    
    wrapper.exposed = True
    return wrapper
    
