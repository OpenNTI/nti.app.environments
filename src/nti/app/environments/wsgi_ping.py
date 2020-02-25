"""
Simple ping paste filter that does nothing but return a 200.
"""

logger = __import__('logging').getLogger(__name__)


class PingHandler(object):
    """
    Handles the ``/_ops/ping`` url exactly.
    """

    def __init__(self, app):
        self.captured = app

    def __call__(self, environ, start_response):
        if environ['PATH_INFO'] == '/_ops/ping':
            start_response('200 OK', [('Content-Type', 'text/plain')])
            result = (b'',)
        else:
            result = self.captured(environ, start_response)
        return result


def ping_handler_factory(app, unused_global_conf=None):
    """
    Paste factory for :class:`PingHandler`
    """
    result = PingHandler(app)
    return result
