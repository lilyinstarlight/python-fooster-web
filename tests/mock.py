import collections
import io
import multiprocessing
import os
import re
import select
import signal
import time

from fooster.web import web


class MockBytes(bytes):
    def set_len(self, len):
        self.len = len

    def __len__(self):
        return self.len


class ErrorIO(io.BytesIO):
    def __init__(self, *args, errors=1):
        super().__init__(*args)
        self.errors = errors

    def read(self, *args):
        if self.errors:
            self.errors -= 1
            raise ConnectionError()
        else:
            return super().read(*args)

    def write(self, *args):
        if self.errors:
            self.errors -= 1
            raise ConnectionError()
        else:
            return super().write(*args)

    def flush(self, *args):
        if self.errors:
            self.errors -= 1
            raise ConnectionError()
        else:
            return super().flush(*args)


class MockSocket:
    def __init__(self, initial=b'', error=False):
        self.bytes = initial
        self.timeout = None
        self.error = error

    def setsockopt(self, level, optname, value):
        pass

    def settimeout(self, timeout):
        self.timeout = timeout

    def makefile(self, mode='r', buffering=None):
        if self.error:
            return ErrorIO()
        else:
            return io.BytesIO(self.bytes)

    def fileno(self):
        return -1

    def setblocking(self, blocking):
        pass


class MockCondition:
    def __init__(self):
        pass

    def wait(self, timeout):
        return False

    def notify(self):
        raise RuntimeError()

    def __enter__(self):
        pass

    def __exit__(self, _, __, ___):
        pass


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

        self.wfile = self.connection.makefile()

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
    def __init__(self, connection, client_address, server, timeout=None, body=None, headers=None, method='GET', resource='/', groups={}, handler=MockHTTPHandler, handler_args={}, comm={}, response=MockHTTPResponse, keepalive_number=1, handle=True, throw=False):
        if connection:
            self.connection = connection
        else:
            self.connection = MockSocket()

        self.client_address = client_address
        self.server = server

        self.timeout = timeout

        self.rfile = io.BytesIO(body)

        self.response = response(self.connection, client_address, server, self)

        self.keepalive = True

        self.method = method
        self.resource = resource
        self.request_http = web.http_version[-1]
        self.request_line = method + ' ' + resource + ' ' + web.http_version[-1]

        if headers:
            self.headers = headers
        else:
            self.headers = web.HTTPHeaders()

        if body and not self.headers.get('Content-Length'):
            self.headers.set('Content-Length', str(len(body)))

        self.handler = handler(self, self.response, groups, **handler_args)
        self.handler.comm = comm

        self.keepalive_number = keepalive_number

        self.will_handle = handle
        self.will_throw = throw

        self.initial_timeout = None
        self.handled = 0

    def handle(self, keepalive=False, timeout=None):
        if self.will_throw:
            raise Exception()

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


class MockHTTPServerControl:
    def __init__(self, sync, notify_error=False):
        self.server_shutdown = sync.Value('b', 0)
        self.manager_shutdown = sync.Value('b', 0)
        self.worker_shutdown = sync.Value('b', -1)

        self.requests_lock = sync.Lock()
        self.requests = sync.Value('H', 0)
        self.processes_lock = sync.Lock()
        self.processes = sync.Value('H', 0)

        self._connection_ready = sync.Condition()

        self.notify_error = notify_error

    @staticmethod
    def _noop(*args, **kwargs):
        raise RuntimeError()

    @staticmethod
    def _error(*args, **kwargs):
        raise RuntimeError()

    @property
    def connection_ready(self):
        if self.notify_error:
            self.notify_error = False
            return MockCondition()

        return self._connection_ready


class MockHTTPWorker:
    def __init__(self, control, info, num):
        # save server stuff
        self.control = control
        self.info = info

        # save worker num
        self.num = num

        # mock-specific stuff
        self.pipe = os.pipe()

        self.read_fd = self.pipe[0]
        self.write_fd = self.pipe[1]

    def run(self):
        while self.control.worker_shutdown.value != -2 and self.control.worker_shutdown.value != num:
            time.sleep(self.info.poll_interval)

    def shutdown(self, connection):
        while select.select([self.read_fd], [], [], 0)[0]:
            os.read(self.read_fd, 1024)


class MockHTTPManager:
    def __init__(self, control, info):
        # save server stuff
        self.control = control
        self.info = info

    def run(self):
        while not self.control.manager_shutdown.value:
            time.sleep(self.info.poll_interval)


class MockHTTPSelector:
    def __init__(self, control, info):
        # save server stuff
        self.control = control
        self.info = info

    def run(self):
        while not self.control.server_shutdown.value:
            time.sleep(self.info.poll_interval)


class MockHTTPServer:
    def __init__(self, address=None, routes={}, error_routes={}, keyfile=None, certfile=None, *, keepalive=5, timeout=20, backlog=5, num_processes=2, max_processes=6, max_queue=4, poll_interval=0.2, log=None, http_log=None, control=None, socket=None):
        # save server address
        self.address = address

        # make route dictionaries
        self.routes = collections.OrderedDict()
        self.error_routes = collections.OrderedDict()

        # compile the regex routes and add them
        for regex, handler in routes.items():
            self.routes[re.compile('^' + regex + '$')] = handler
        for regex, handler in error_routes.items():
            self.error_routes[re.compile('^' + regex + '$')] = handler

        # store constants
        self.keyfile = keyfile
        self.certfile = certfile

        self.using_tls = self.keyfile and self.certfile

        self.keepalive_timeout = keepalive
        self.request_timeout = timeout

        self.backlog = backlog

        self.num_processes = num_processes
        self.max_processes = max_processes
        self.max_queue = max_queue

        self.poll_interval = poll_interval

        # create the logs
        if log:
            self.log = log
        else:
            self.log = web.default_log

        if http_log:
            self.http_log = http_log
        else:
            self.http_log = web.default_http_log

        # create sync manager
        sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
        self.sync = multiprocessing.get_context(web.start_method).Manager()
        signal.signal(signal.SIGINT, sigint)

        # create process-ready server control object with manager
        if control:
            self.control = control
        else:
            self.control = web.HTTPServerControl(self.sync, self.backlog)

        # lock for automatic handling of resource safety/consistency
        self.res_lock = web.ResLock(self.sync)

        # prepare a socket
        if socket:
            self.socket = socket
        else:
            self.socket = MockSocket()

        # create process-ready server info object
        self.info = web.HTTPServerInfo(self)
