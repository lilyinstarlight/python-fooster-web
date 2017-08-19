import collections
import io
import logging
import multiprocessing
import queue
import re
import time

from web import web


class MockBytes(bytes):
    def set_len(self, len):
        self.len = len

    def __len__(self):
        return self.len


class MockSocket:
    def __init__(self, initial=b''):
        self.bytes = initial
        self.timeout = None

    def setsockopt(self, level, optname, value):
        pass

    def settimeout(self, timeout):
        self.timeout = timeout

    def makefile(self, mode='r', buffering=None):
        return io.BytesIO(self.bytes)


class MockHTTPHandler:
    def __init__(self, request, response, groups):
        self.request = request
        self.response = response
        self.groups = groups

    def respond(self):
        return 204, ''


class MockHTTPErrorHandler(MockHTTPHandler):
    def __init__(self, request, response, groups, error=web.HTTPError(500)):
        MockHTTPHandler.__init__(self, request, response, groups)
        self.error = error

    def respond(self):
        return 204, ''


class MockHTTPResponse:
    def __init__(self, connection, client_address, server, request, handle=True):
        self.connection = connection
        self.client_address = client_address
        self.server = server

        self.request = request

        self.will_handle = handle

        self.wfile = io.BytesIO(b'')

        self.headers = web.HTTPHeaders()

        self.write_body = True

        self.handled = 0

        self.closed = False

    def handle(self):
        self.handled += 1

        if self.will_handle:
            return True
        else:
            return self.handled > 1

    def close(self):
        self.closed = True


class MockHTTPRequest:
    def __init__(self, connection, client_address, server, timeout=None, body=None, headers=None, method='GET', resource='/', groups=(), handler=MockHTTPHandler, handler_args={}, response=MockHTTPResponse, keepalive_number=0, handle=True):
        self.connection = connection
        self.client_address = client_address
        self.server = server

        self.timeout = timeout

        self.rfile = io.BytesIO(body)

        self.response = response(connection, client_address, server, self)

        self.keepalive = True

        self.method = method
        self.resource = resource
        self.request_line = method + ' ' + resource + ' ' + web.http_version

        if headers:
            self.headers = headers
        else:
            self.headers = web.HTTPHeaders()

        if body:
            self.headers.set('Content-Length', str(len(body)))

        self.handler = handler(self, self.response, groups, **handler_args)

        self.keepalive_number = keepalive_number

        self.will_handle = handle

        self.initial_timeout = None
        self.handled = 0

    def handle(self, keepalive=False, timeout=None):
        self.keepalive_number -= 1
        if self.keepalive_number == 0:
            self.keepalive = False
        else:
            self.keepalive = keepalive
        self.initial_timeout = timeout
        self.handled += 1

        if self.will_handle:
            return True
        else:
            return self.handled > 1

    def close(self):
        pass


class MockNamespace:
    pass


class MockSync:
    def Lock(self):
        return multiprocessing.Lock()

    def Namespace(self):
        return multiprocessing.Namespace()

    def dict(self):
        return {}

    def list(self):
        return []


class MockHTTPServer:
    def __init__(self, address=None, routes={}, error_routes={}, keyfile=None, certfile=None, keepalive=5, timeout=20, num_processes=2, max_processes=6, max_queue=4, poll_interval=1, log=None, http_log=None, sync=None):
        self.routes = collections.OrderedDict()
        self.error_routes = collections.OrderedDict()

        for regex, handler in routes.items():
            self.routes[re.compile('^' + regex + '$')] = handler
        for regex, handler in error_routes.items():
            self.error_routes[re.compile('^' + regex + '$')] = handler

        self.keepalive_timeout = keepalive
        self.timeout = timeout

        self.num_processes = num_processes
        self.max_processes = max_processes
        self.max_queue = max_queue
        self.poll_interval = poll_interval

        # create the logs
        if log:
            self.log = log
        else:
            self.log = logging.getLogger('web')

        if http_log:
            self.http_log = http_log
        else:
            self.http_log = logging.getLogger('http')

            handler = logging.StreamHandler()
            handler.setFormatter(web.HTTPLogFormatter())
            self.http_log.addHandler(handler)
            self.http_log.addFilter(web.HTTPLogFilter())

        self.namespace = MockNamespace()
        self.namespace.manager_shutdown = False
        self.namespace.worker_shutdown = None

        self.res_lock = web.ResLock(MockSync())

        self.request_queue = queue.Queue()

    def shutdown_request(self, connection):
        pass

    def manager(self):
        while not self.manager_shutdown:
            time.sleep(self.poll_interval)

    def worker(self, num):
        while self.worker_shutdown != -1 and self.worker_shutdown != num:
            time.sleep(self.poll_interval)
