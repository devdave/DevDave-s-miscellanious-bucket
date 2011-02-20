
from functools import wraps
from cStringIO import StringIO


def buffout(f):
    """
        A simple decorator that intercepts stdout calls and places them into a
        StringIO buffer.
    """
    f.exposed = True
    
    @wraps(f)
    def wrappit(*args, **kwargs):
        buffer = "<pre> Das buffer FAILED :( <br/>"
        try:
            og_stdout = sys.stdout
            my_stdout = StringIO()
            sys.stdout = my_stdout
            retval = f(*args, **kwargs)
            my_stdout.seek(0)
            buffer = my_stdout.read()
            return buffer
        finally:
            sys.stdout = og_stdout
    
    wrappit.exposed = True
    
    return wrappit