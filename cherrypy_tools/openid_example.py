"""
   Q. What is this?
   A. An attempt at a reference implementation of Cherrypy & openid
   
   Highlights:
      /index
        Provides a basic form that I literally copy & pasted from the
        python-openid/examples/consumer.py script
    /verify
        Builds out a boolean dict of options plus grabs the target
        openid provider
        
        Inside the try/except brackets is the call to the openID
        provider to develop a mutal secret ( think HTTP digest ).  
        
        At this stage, the cherrypy logic should either trust the provider or reject it
        for various reasons ( no provider, bad response, etc )
        
        
        Additionally by default this always asks for AX values:
            first/last name & email
        Optionally appends PAPE and SREG extension requests
        
        At the end, as determined by python-openid this either makes a client side
        302 REDIRECT GET or auto-submit form POST request to the remote provider.
        
    /process
        Upon the user authenticating and accepting any conditional terms ( sreg/ax/oAuth)
        with their provider, they're redirected back here.
        
        I think the things to focus on is the openid.identity which when combined with
        sreg/ax email should be enough to create a unique identity record.
        
        Everything else in this action/method is either documented or dumped to the browser for
        transparency.
        
"""
#Default cherrypy
import cherrypy
from cherrypy import expose

#My libs
import sys
from functools import wraps, partial
from cStringIO import StringIO
from cgi import escape
from textwrap import wrap

try:
    from dbgp.client import brk
    #Perhaps hijacking cherrypy config might be useful here?
    brk = partial(brk, host="192.168.56.1", port=9000)
except ImportError:
    def brk(*args, **kwatgs):
        pass

#Openid Libs
try:
    from openid.store import memstore
    from openid.store import filestore
    from openid.consumer import consumer
    from openid.oidutil import appendArgs
    from openid.cryptutil import randomString
    from openid.fetchers import setDefaultFetcher, Urllib2Fetcher
    from openid.extensions import (pape, sreg, ax)
    from openid.message import NamespaceMap
except ImportError, e:
    print "Python says ", e, "which I assume is it's way of saying"
    print "\"You should probably install python-openedid\"... that or all of the rum is gone"
    sys.exit(1)

#make this crap slightly prettier

from cStringIO import StringIO



def main():
    """
        Master function, ALWAYS keep @ the top of the file
    """
    config = {
    "tools.sessions.on":  True,
    "tools.sessions.storage_type": "file",
    "tools.sessions.storage_path": "/tmp/",
    "server.socket_host": "0.0.0.0",
    "server.socket_port": 6060
    }
    cherrypy.config.update(config)
    cherrypy.quickstart(Root(),'/')

def oid_store(thread_index):
    """
        This will need to be refactored for a LOT of reasons
        , #1 is the possibility of jumping threads during the authentication
        process
    """
    print "Starting up a new thread @ " , thread_index
    cherrypy.thread_data.store = memstore.MemoryStore()

cherrypy.engine.subscribe("start_thread", oid_store )    

def buffout(f):
    """
        A goofy little hack to avoid having to make templates for everything
        This hijacks stdout temporarily during action execution
        then ideally dumps the buffer to response out while returning stdout
        to it's normal method
    """
    f.exposed = True
    
    @wraps(f)
    def wrappit(*args, **kwargs):
        buffer = "<pre> Das buffer FAILED :( <br/>"
        try:
            og_stdout, my_stdout = sys.stdout, StringIO()
            sys.stdout = my_stdout
            retval = f(*args, **kwargs)
            my_stdout.seek(0)
            return my_stdout.read()
        finally:
            sys.stdout = og_stdout
    
    #I've found that the exposed attribute sometimes gets eaten.
    wrappit.exposed = True
    
    return wrappit
    

def printList(myLocals, title = None):
    """
        Just a silly little debugging tool thing
    """
    print "<table class=\"listedTable\" data-title = \"%s\" border=1 >" % title
    try:
        if title:
            print "<legend>%s</legend>" % title
        
        if hasattr(myLocals, "keys"):    
            sortedkeys = sorted(myLocals.keys())
        else:
            sortedkeys = sorted(dir(myLocals))
            
        for key in sortedkeys:
            #if key[0] == "_": continue
            
            item = myLocals[key] if hasattr(myLocals, "__getitem__") else getattr(myLocals, key)
            #generally don't want a digest list of methods, but this will also
            #avoid any class with a __call__ method in it.
            if callable(item):
                continue
            
            print "<tr>"
            rowHeader = ""
            try:
                rowHeader = str(key)
            except TypeError, e:
                rowHeader = "Type Error %s on " % key , " value = ", key 
            
            print "<th>%s</th>" % rowHeader
            
            print "<td style=\"max-width:'60%'\">"    
            try:
                if item is None:            
                    print  escape( str(item.__class__)), "None"
                elif isinstance(item, str) or isinstance(item, list) or isinstance(item, bool):
                    print  escape( str(item.__class__)),  " - ", escape( str(item))
                elif callable(item):
                    print escape( str(item))
                elif hasattr(item, "__getitem__"):
                    printList(item, key)
                elif hasattr(item, "__dict__"):
                    printList(item.__dict__, key)
                else:
                    print str(item)
            except TypeError, e:
                brk()
                print "Type Error on ", e, item
            finally:
                print "</td>"
                
            print "</tr>"
    finally:
        print "</table>"

class OpIDHelper(object):
    """
        The hope is to keep the controller tier slightly LESS
        cluttered with openID stuff.
    """
    session = None
    
    #https://www.google.com/accounts/o8/id
    @classmethod
    def getConsumer(cls, stateless=False):
        """
            Copy & pasted from consumer.py example in py-OpenID src library
            NOTE - Cherrypy is a multi-threaded deal which will screw everything up
            if the request is made in a different thread from the response handling method
        """
        if stateless:
            store = None
        else:
            store =  cherrypy.thread_data.store
        return consumer.Consumer(cls.getSession(), store)
    
    @classmethod
    def getGoogleRequest(cls, consumer):
        """
            URL provided by Google's federated login docs -
            http://code.google.com/apis/accounts/docs/OpenID.html#endpoint
        """
        return consumer.begin("https://www.google.com/accounts/o8/id")
        
    @classmethod
    def getSession(cls):
        """Return the existing session or a new session"""
        if cls.session is None:
            cls.session = cherrypy.session
        
        return cls.session

    @classmethod
    def requestRegistrationData(cls, request):
        """
            I liked how simple this is compared to the AX implementation
        """
        sreg_request = sreg.SRegRequest(
            required=['nickname'], optional=['fullname', 'email'])
        request.addExtension(sreg_request)

    @classmethod
    def requestPAPEDetails(cls, request):
        """
        http://openid.net/specs/openid-provider-authentication-policy-extension-1_0.html
            From my perspective, it seems like a good idea to ALWAYS request PAPE
            when making an openid request
        """
        pape_request = pape.Request([pape.AUTH_PHISHING_RESISTANT])
        request.addExtension(pape_request)
        
    @classmethod
    def requestAXDetails(cls, request):
        """
            http://openid.net/specs/openid-attribute-exchange-1_0.html
            A new and improved sreg.  Most docs will only list
            the "short" version, but what you really need
            is the URI version.
            
            Also, not tested but read in places that Google only
            obey's required attr requests.
        """
        ax_request = ax.FetchRequest()
        #required=['fullname', 'email', 'firstname', 'lastname']

        #ax_request.add(ax.AttrInfo("fullname", required =True))
        ax_request.add(ax.AttrInfo('http://axschema.org/contact/email', required =True, alias = "email"))
        #note these do not appear to work with google
        ax_request.add(ax.AttrInfo('http://axschema.org/namePerson/first', required =True, alias = "firstname"))
        ax_request.add(ax.AttrInfo('http://axschema.org/namePerson/last', required =True, alias = "lastname"))
        request.addExtension(ax_request)
        
    @classmethod
    def ax2aliases(cls, response):
        """
            Returns a dict where key => AX alias and not the whole goddamn url
            NOTE: I can't help but feel that I am missing something with the AX extension
            as I copy/pasted & modified below DIRECTLY from extensions.ax.py in the
            python-openid library
        """
        ax_args = response.extensionResponse(ax.AXMessage.ns_uri, True)
        valueMap = {}

        #Was originally 2 loops, cut this down to 1        
        for key, value in ax_args.iteritems():
            if key.startswith("type.") == False: continue

            type_uri = value
            alias = key[5:] #Grab everything after type.
            try:
                count_s = ax_args['count.' + alias]
            except KeyError:
                value = ax_args['value.' + alias]
                values = [] if value == u'' else [value]
            else:
                count = int(count_s)
                values = []
                for i in range(1, count + 1):
                    value_key = 'value.%s.%d' % (alias, i)
                    value = ax_args[value_key]
                    values.append(value)
        
            valueMap[alias] = values
                

            
        
        return valueMap

    @classmethod
    def capabilities(cls, request):
        """
            Checks the request object created by py-openID consumer and returns a dict
            of all extensions present
            
            Fun issue I realized AFTER the fact.  This only confirms capabilities for XRD/Yadis
            managed endpoints that are considerate enough to list them.  For simpler endpoints
            like PHP's MyOpenId script... it won't tell you poop until you try.  So better
            to ask for the kingdom up front then come back a second time.
        """
        caps = {}
        endpointCheck = request.endpoint.type_uris
        caps['signon_icon'] = "http://specs.openid.net/extensions/ui/1.0/icon" in endpointCheck
        caps['ax'] = ax.AXMessage.ns_uri in endpointCheck
        caps['auth2'] = "http://specs.openid.net/auth/2.0/server" in endpointCheck
        caps['popup'] = "http://specs.openid.net/extensions/ui/1.0/mode/popup" in endpointCheck
        caps['pape']  = "http://specs.openid.net/extensions/pape/1.0" in endpointCheck
        caps['sreg']  = sreg.ns_uri in endpointCheck
        return caps
        
class Root(object):
    
    
    @expose
    def index(self):
        return mainPage("Main Page", getForm(""))
    
    @buffout
    def verify(self, openid_identifier = None, **queryString):
        
        openid_url = openid_identifier
            
        immediate       = "immediate" in queryString
        use_sreg        = "use_sreg" in queryString
        use_pape        = "use_page" in queryString
        use_stateless   = "use_stateless" in queryString
        #From what I can tell, there are 3 openID endpoints: public mainline google, google apps, and GAE
        #we want public mainline, apps can be reached by appending ?hd=yourDomain.com to the openid provider
        #listed in the XRDS document ( not the federated login endpoint )
        use_google      = "use_gmail" in queryString      
        #brk()
        if not openid_url and not use_google:
            print mainPage("Main Page", getForm(""), "Missing openid url")
            return True
        
        oidconsumer = OpIDHelper.getConsumer(stateless = use_stateless)
        try:
            request = oidconsumer.begin(openid_url) if use_google == False else OpIDHelper.getGoogleRequest(oidconsumer)
        except consumer.DiscoveryFailure, exc:
            print "Error in discovery:", exc[0]
            print mainPage("Main Page", getForm(openid_url))
        else:
            if request is None:
                print "No Openid services found for <code>%s</code" % openid_url
                print mainPage("Main Page", getForm(openid_url))
                
            else:
                
                caps = OpIDHelper.capabilities(request)

                
                if use_sreg:
                    #If in doubt, if you're asking for sreg, always ask for AX as well
                    #Google doesn't support sreg while others don't support AX
                    OpIDHelper.requestRegistrationData(request)
                    OpIDHelper.requestAXDetails(request)
                    
                if use_pape:
                    OpIDHelper.requestPAPEDetails(request)
                
                #Logic here is, however you're reaching cherrypy, you can be redirected back to it
                trust_root = cherrypy.request.base                
                return_to = "%s/process" % trust_root
                
                #Should we just 302 this or print a self-submitting html form?
                #Which really breaks down to, should we send a GET or POST request?
                if request.shouldSendRedirect():
                    redirect_url = request.redirectURL(
                        trust_root, return_to, immediate=immediate)
                    raise cherrypy.HTTPRedirect(redirect_url, 302)                    
                else:
                    #I'm lying if I said I understand the form_tag_attrs argument provided here
                    form_html = request.htmlMarkup(
                        trust_root, return_to,
                        form_tag_attrs={'id':'openid_message'},
                        immediate=immediate)

                    print form_html
                            
        return True
    
    @buffout
    def process(self, *args, **queryStr):
        
        printList(queryStr, "queryStr")

        oidconsumer = OpIDHelper.getConsumer()
        
        url = '%s/process' % cherrypy.request.base
        info = oidconsumer.complete(queryStr, url)
        sreg_resp = None
        pape_resp = None        
        display_identifier = info.getDisplayIdentifier()

        if info.status == consumer.FAILURE and display_identifier:
            # In the case of failure, if info is non-None, it is the
            # URL that we were verifying. We include it in the error
            # message to help the user figure out what happened.
            print "Verification of %s failed: %s" % (display_identifier, info.message, )

        elif info.status == consumer.SUCCESS:
            # Success means that the transaction completed without
            # error. If info is None, it means that the user cancelled
            # the verification.
            

            # This is a successful verification attempt. If this
            # was a real application, we would do our login,
            # comment posting, etc. here.
            fmt = "You have successfully verified %s as your identity."
            
            print fmt % (display_identifier,)

            printList(info.__dict__,"info = oidconsumer.complete")
            
            sreg_resp = sreg.SRegResponse.fromSuccessResponse(info)
            pape_resp = pape.Response.fromSuccessResponse(info)
            #brk()
            ax_resp   = ax.FetchResponse.fromSuccessResponse(info)
            

            if ax_resp:
                #For some reason, the aliases I defined earlier ARE returned, used, then thrown away
                #wtf?
                axDict = OpIDHelper.ax2aliases(info)
                printList(axDict, "Attribute Exchange vars\n")
            
            if pape_resp:
                printList(pape_resp, "PAPE response")
                
            if sreg_resp:
                printList(sreg_resp, "SREG response")

                                 
            if info.endpoint.canonicalID:
                #I've yet to get this returned in my tests
                print "  This is an i-name, and its persistent ID is %s" \
                            % (info.endpoint.canonicalID)
                
        elif info.status == consumer.CANCEL:
            # cancelled
            print 'Verification cancelled'            
        elif info.status == consumer.SETUP_NEEDED:
            
            if info.setup_url:
                #I've been reading conflicting documents stating this was/is deprecated
                print '<a href=%s>Setup needed</a>' % (
                    quoteattr(info.setup_url),)
            else:
                # This means auth didn't succeed, but you're welcome to try
                # non-immediate mode.
                print 'Setup needed, try without immediate mode'
        else:
            # Either we don't understand the code or there is no
            # openid_url included with the error. Give a generic
            # failure message. The library should supply debug
            # information in a log.
            print 'Verification failed.', info.status
        
        #print printLocals(locals())
        if hasattr(info, "identity_url") and info.identity_url:
            #Note for google, this looks kind of goofy
            print mainPage("Main Page", getForm(info.identity_url))
        elif openid_url:
            print mainPage("Main Page", getForm(openid_url))
        else:
            print mainPage("Main Page", getForm(""))            
                
 
@buffout
def getForm(openid_identifier = ""):
    print """
    <div id="verify-form">
      <form method="get" accept-charset="UTF-8" action='/verify'>
        <span>Identifier:</span>
        <input type="text" name="openid_identifier" value='%s' >
        <input type="submit" value="Verify" /><br />
        <input type="checkbox" name="immediate" id="immediate" /><label for="immediate">Use immediate mode</label>
        <input type="checkbox" name="use_sreg" id="use_sreg" /><label for="use_sreg">Request registration data</label>
        <input type="checkbox" name="use_pape" id="use_pape" /><label for="use_pape">Request phishing-resistent auth policy (PAPE)</label>
        <input type="checkbox" name="use_stateless" id="use_stateless" /><label for="use_stateless">Use stateless mode</label>
        <input type="checkbox" name="use_gmail" id="use_gmail" /><label for="use_gmail">Use Google</label>
      </form>
    </div>""" % (openid_identifier)
   
def getHead(title = "NotSet"):
    return """
<html>
  <head><title>%s</title></head>
  <style type="text/css">
      * {
        font-family: verdana,sans-serif;
      }
      body {
        width: 50em;
        margin: 1em;
      }
      div {
        padding: .5em;
      }
      tr.odd td {
        background-color: #dddddd;
      }
      table.sreg {
        border: 1px solid black;
        border-collapse: collapse;
      }
      table.sreg th {
        border-bottom: 1px solid black;
      }
      table.sreg td, table.sreg th {
        padding: 0.5em;
        text-align: left;
      }
      table {
        margin: 0;
        padding: 0;
      }
      .alert {
        border: 1px solid #e7dc2b;
        background: #fff888;
      }
      .error {
        border: 1px solid #ff0000;
        background: #ffaaaa;
      }
      #verify-form {
        border: 1px solid #777777;
        background: #dddddd;
        margin-top: 1em;
        padding-bottom: 0em;
      }
  </style>
  </head>
    """ % title
    
@buffout
def mainPage(title, *args):
    print getHead(title)    
    print "\n<body>\n", "\n".join(args ), "\n</body></html>\n"
    return True
    
    
if __name__ == "__main__":
    main()