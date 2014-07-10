import io

from web import HTTPHeaders

class FakeHTTPRequest(object):
	def __init__(self, connection, client_address, server, timeout=None, keepalive_timeout=None):
		self.connection = connection
		self.client_address = client_address
		self.server = server

		self.timeout = timeout
		self.keepalive_timeout = keepalive_timeout

		self.response = FakeHTTPResponse(connection, client_address, server, self)
		self.headers = HTTPHeaders()

		self.keepalive = False

		self.setup()

	def setup(self):
		self.rfile = io.BytesIO(b'')
		self.response.setup()

	def handle(self):
		pass

	def finish(self):
		pass

class FakeHTTPResponse(object):
	def __init__(self, connection, client_address, server, request):
		self.connection = connection
		self.client_address = client_address
		self.server = server

		self.request = request

		self.headers = HTTPHeaders()

		self.write_body = True

	def setup(self):
		self.wfile = io.BytesIO(b'')

	def handle(self):
		pass

	def finish(self):
		pass
