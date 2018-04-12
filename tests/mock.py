import collections
import io
import logging
import os
import re
import select
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
            super().read(*args)

    def write(self, *args):
        if self.errors:
            self.errors -= 1
            raise ConnectionError()
        else:
            super().write(*args)

    def flush(self, *args):
        if self.errors:
            self.errors -= 1
            raise ConnectionError()
        else:
            super().flush(*args)


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


class MockLock:
    def __enter__(self, *args):
        self.acquire()

    def __exit__(self, *args):
        self.release()

    def acquire(self):
        pass

    def release(self):
        pass


class MockNamespace:
    pass


class MockValue:
    def __init__(self):
        self.lock = MockLock()
        self.value = 0


class MockEvent:
    def __init__(self):
        self.triggered = False

    def set(self):
        self.triggered = True

    def wait(self):
        while not self.triggered:
            time.sleep(1)


class MockSync:
    def Lock(self, *args):
        return MockLock()

    def Namespace(self, *args):
        return MockNamespace()

    def Value(self, *args):
        return MockValue()

    def list(self, *args):
        return list(*args)

    def dict(self, *kwargs):
        return dict(*kwargs)


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
    def __init__(self, connection, client_address, server, timeout=None, body=None, headers=None, method='GET', resource='/', groups=(), handler=MockHTTPHandler, handler_args={}, response=MockHTTPResponse, keepalive_number=1, handle=True, throw=False, namespace=None):
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
        self.request_line = method + ' ' + resource + ' ' + web.http_version

        if headers:
            self.headers = headers
        else:
            self.headers = web.HTTPHeaders()

        if body and not self.headers.get('Content-Length'):
            self.headers.set('Content-Length', str(len(body)))

        self.handler = handler(self, self.response, groups, **handler_args)

        self.keepalive_number = keepalive_number

        self.will_handle = handle
        self.will_throw = throw

        if namespace:
            self.namespace = namespace
        else:
            self.namespace = MockNamespace()

        self.initial_timeout = None
        self.handled = 0
        self.namespace.request_initial_timeout = self.initial_timeout
        self.namespace.request_handled = self.handled

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
        self.namespace.request_initial_timeout = self.initial_timeout
        self.namespace.request_handled = self.handled

        if self.will_handle:
            return True
        else:
            return self.handled > 1

    def close(self):
        pass


class MockHTTPServer:
    def __init__(self, address=None, routes={}, error_routes={}, keyfile=None, certfile=None, keepalive=5, timeout=20, num_processes=2, max_processes=6, max_queue=4, poll_interval=1, log=None, http_log=None, sync=None, verify=True, throw=False, error=False):
        self.routes = collections.OrderedDict()
        self.error_routes = collections.OrderedDict()

        for regex, handler in routes.items():
            self.routes[re.compile('^' + regex + '$')] = handler
        for regex, handler in error_routes.items():
            self.error_routes[re.compile('^' + regex + '$')] = handler

        self.keepalive_timeout = keepalive
        self.request_timeout = timeout

        self.num_processes = num_processes
        self.max_processes = max_processes
        self.max_queue = max_queue
        self.poll_interval = poll_interval

        if sync:
            self.sync = sync
        else:
            self.sync = MockSync()

        self.will_verify = verify
        self.will_throw = throw
        self.will_error = error

        self.namespace = self.sync.Namespace()

        self.server_process = None
        self.namespace.server_shutdown = False
        self.namespace.manager_shutdown = False
        self.namespace.worker_shutdown = None

        self.namespace.handled = 0

        self.namespace.request_initial_timeout = 0
        self.namespace.request_handled = 0

        self.requests_lock = self.sync.Lock()
        self.requests = self.sync.Value('Q', 0)
        self.cur_processes_lock = self.sync.Lock()
        self.cur_processes = self.sync.Value('Q', 0)

        # lock for atomic handling of resources
        self.res_lock = web.ResLock(self.sync)

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

        self.pipe = os.pipe()

        self.read_fd = self.pipe[0]
        self.write_fd = self.pipe[1]

    def shutdown_request(self, connection):
        while select.select([self.read_fd], [], [], 0)[0]:
            os.read(self.read_fd, 1024)

    def process_request(self, connection, client_address):
        if self.will_throw:
            raise Exception()

        self.request_queue.put((MockHTTPRequest(connection, client_address, None, self.request_timeout, namespace=self.namespace), (self.keepalive_timeout is not None), None, True))

    def get_request(self):
        if self.will_error:
            raise OSError()

        return MockSocket(), ('127.0.0.1', 1337)

    def verify_request(self, connection, client_address):
        return self.will_verify

    def handle_error(self, connection, client_address):
        self.namespace.handled += 1

    def manager(self):
        while not self.namespace.manager_shutdown:
            time.sleep(self.poll_interval)

    def worker(self, num):
        while self.namespace.worker_shutdown != -1 and self.namespace.worker_shutdown != num:
            time.sleep(self.poll_interval)

    def fileno(self):
        return self.read_fd
