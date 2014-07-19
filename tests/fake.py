import io

from web import web

class FakeHTTPLog(web.HTTPLog):
	def __init__(self, httpd_log, access_log):
		if isinstance(httpd_log, io.IOBase) and isinstance(access_log, io.IOBase):
			self.httpd_log = httpd_log
			self.access_log = access_log
		else:
			web.HTTPLog.__init__(self, httpd_log, access_log)

class FakeHTTPRequest(object):
	def __init__(self, connection, client_address, server, timeout=None, keepalive_timeout=None):
		self.connection = connection
		self.client_address = client_address
		self.server = server

		self.timeout = timeout
		self.keepalive_timeout = keepalive_timeout

		self.response = FakeHTTPResponse(connection, client_address, server, self)
		self.headers = web.HTTPHeaders()

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

		self.headers = web.HTTPHeaders()

		self.write_body = True

	def setup(self):
		self.wfile = io.BytesIO(b'')

	def handle(self):
		pass

	def finish(self):
		pass
