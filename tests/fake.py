import io
import re

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

class FakeHTTPRequest(object):
	def __init__(self, connection, client_address, server, timeout=None, body=None, headers=None, method='GET', resource='/', groups=(), handler=FakeHTTPHandler, handler_args={}):
		self.connection = connection
		self.client_address = client_address
		self.server = server

		self.timeout = timeout

		self.rfile = io.BytesIO(body)

		self.response = FakeHTTPResponse(connection, client_address, server, self)

		self.keepalive = True

		self.method = method

		self.resource = resource

		if headers:
			self.headers = headers
		else:
			self.headers = web.HTTPHeaders()

		if body:
			self.headers.set('Content-Length', str(len(body)))

		self.handler = handler(self, self.response, groups, **handler_args)

	def handle(self):
		pass

	def close(self):
		pass

class FakeHTTPResponse(object):
	def __init__(self, connection, client_address, server, request):
		self.connection = connection
		self.client_address = client_address
		self.server = server

		self.request = request

		self.wfile = io.BytesIO(b'')

		self.headers = web.HTTPHeaders()

		self.write_body = True

	def handle(self):
		pass

	def close(self):
		pass

class FakeHTTPServer(object):
	def __init__(self, routes={}, error_routes={}, log=web.HTTPLog(None, None)):
		self.routes = {}
		for regex, handler in routes.items():
			self.routes[re.compile('^' + regex + '$')] = handler
		self.error_routes = {}
		for regex, handler in error_routes.items():
			self.error_routes[re.compile('^' + regex + '$')] = handler

		self.log = log

		self.locks = []
