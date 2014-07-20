import io

from web import web

class FakeBytes(bytes):
	def set_len(self, len):
		self.len = len

	def __len__(self):
		return self.len

class FakeSocket(object):
	pass

class FakeHTTPRequest(object):
	def __init__(self, connection, client_address, server, timeout=None, keepalive_timeout=None):
		self.connection = connection
		self.client_address = client_address
		self.server = server

		self.timeout = timeout
		self.keepalive_timeout = keepalive_timeout

		self.rfile = io.BytesIO(b'')

		self.response = FakeHTTPResponse(connection, client_address, server, self)

		self.keepalive = False

		self.headers = web.HTTPHeaders()

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
