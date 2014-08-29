import io
import queue
import re
import threading
import time

from web import web

class FakeBytes(bytes):
	def set_len(self, len):
		self.len = len

	def __len__(self):
		return self.len

class FakeSocket(object):
	def __init__(self, initial=b''):
		self.bytes = initial
		self.timeout = None

	def setsockopt(self, level, optname, value):
		pass

	def settimeout(self, timeout):
		self.timeout = timeout

	def makefile(self, mode='r', buffering=None):
		return io.BytesIO(self.bytes)

class FakeHTTPHandler(object):
	def __init__(self, request, response, groups):
		self.request = request
		self.response = response
		self.groups = groups

	def respond(self):
		return 204, ''

class FakeHTTPErrorHandler(FakeHTTPHandler):
	def __init__(self, request, response, groups, error=web.HTTPError(500)):
		FakeHTTPHandler.__init__(self, request, response, groups)
		self.error = error

	def respond(self):
		return 204, ''

class FakeHTTPResponse(object):
	def __init__(self, connection, client_address, server, request):
		self.connection = connection
		self.client_address = client_address
		self.server = server

		self.request = request

		self.wfile = io.BytesIO(b'')

		self.headers = web.HTTPHeaders()

		self.write_body = True

		self.handled = 0

	def handle(self):
		self.handled += 1

	def close(self):
		pass

class FakeHTTPRequest(object):
	def __init__(self, connection, client_address, server, timeout=None, body=None, headers=None, method='GET', resource='/', groups=(), handler=FakeHTTPHandler, handler_args={}, response=FakeHTTPResponse, keepalive_number=0):
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

	def close(self):
		pass

class FakeHTTPLog(web.HTTPLog):
	def __init__(self, httpd_log, access_log):
		self.httpd_log = io.StringIO()
		self.httpd_log_lock = threading.Lock()

		self.access_log = io.StringIO()
		self.access_log_lock = threading.Lock()

	def timestamp(self):
		return '[01/Jan/1970:00:00:00 -0000]'

class FakeHTTPServer(object):
	def __init__(self, routes={}, error_routes={}, keyfile=None, certfile=None, keepalive=5, timeout=20, num_threads=2, max_threads=6, max_queue=4, poll_interval=0.1, log=None):
		self.routes = {}
		for regex, handler in routes.items():
			self.routes[re.compile('^' + regex + '$')] = handler
		self.error_routes = {}
		for regex, handler in error_routes.items():
			self.error_routes[re.compile('^' + regex + '$')] = handler

		self.keepalive_timeout = keepalive
		self.timeout = timeout

		self.num_threads = num_threads
		self.max_threads = max_threads
		self.max_queue = max_queue
		self.poll_interval = poll_interval

		if log:
			self.log = log
		else:
			self.log = FakeHTTPLog(None, None)

		self.manager_thread = None
		self.manager_shutdown = False

		self.worker_threads = None
		self.worker_shutdown = None

		self.res_lock = web.ResLock()

		self.request_queue = queue.Queue()

	def shutdown_request(self, connection):
		pass

	def manager(self):
		while not self.manager_shutdown:
			time.sleep(self.poll_interval)

	def worker(self, num):
		while self.worker_shutdown != -1 and self.worker_shutdown != num:
			time.sleep(self.poll_interval)
