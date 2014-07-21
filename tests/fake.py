import io

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

	def settimeout(self, timeout):
		self.timeout = timeout

	def makefile(self, mode='r', buffering=None):
		return self.bytes

class FakeHTTPRequest(object):
	def __init__(self, connection, client_address, server, timeout=None, handler=None):
		self.connection = connection
		self.client_address = client_address
		self.server = server

		self.timeout = timeout

		self.rfile = io.BytesIO(b'')

		self.response = FakeHTTPResponse(connection, client_address, server, self)

		self.keepalive = False

		self.headers = web.HTTPHeaders()

		self.handler = handler

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

def FakeHTTPServer(object):
	def __init__(self, routes={}, error_routes={}, log=web.HTTPLog(None, None)):
		self.routes = routes
		self.error_routes = error_routes

		self.log = log

		self.locks = []
