import os
import re
import socket
import socketserver
import ssl
import sys
import time
import traceback
import threading

#Server details
server_version = 'web.py/0.1'
http_version = 'HTTP/1.1'
http_encoding = 'iso-8859-1'
default_encoding = 'utf-8'

#Constraints
max_request_size = 4096
max_line_size = 1024
max_headers = 64

#Standard HTTP status messages
status_messages = {
	#1xx Informational
	100: 'Continue',
	101: 'Switching Protocols',
	102: 'Processing',

	#2xx Success
	200: 'OK',
	201: 'Created',
	202: 'Accepted',
	203: 'Non-Authoritative Information',
	204: 'No Content',
	205: 'Reset Content',
	206: 'Partial Content',
	207: 'Multi-Status',
	208: 'Already Reported',
	226: 'IM Used',

	#3xx Redirection
	300: 'Multiple Choices',
	301: 'Moved Permanently',
	302: 'Found',
	303: 'See Other',
	304: 'Not Modified',
	305: 'Use Proxy',
	306: 'Switch Proxy',
	307: 'Temporary Redirect',
	308: 'Permanent Redirect',

	#4xx Client Error
	400: 'Bad Request',
	401: 'Unauthorized',
	402: 'Payment Required',
	403: 'Forbidden',
	404: 'Not Found',
	405: 'Method Not Allowed',
	406: 'Not Acceptable',
	407: 'Proxy Authentication Required',
	408: 'Request Timeout',
	409: 'Conflict',
	410: 'Gone',
	411: 'Length Required',
	412: 'Precondition Failed',
	413: 'Request Entity Too Large',
	414: 'Request-URI Too Long',
	415: 'Unsupported Media Type',
	416: 'Requested Range Not Satisfiable',
	417: 'Expectation Failed',
	418: 'I\'m a teapot',
	419: 'Authentication Timeout',
	422: 'Unprocessable Entity',
	423: 'Locked',
	424: 'Failed Dependency',
	425: 'Unordered Collection',
	426: 'Upgrade Required',
	428: 'Precondition Required',
	429: 'Too Many Requests',
	431: 'Request Header Fields Too Large',
	451: 'Unavailable For Legal Reasons',

	#5xx Server Error
	500: 'Internal Server Error',
	501: 'Not Implemented',
	502: 'Bad Gateway',
	503: 'Service Unavailable ',
	504: 'Gateway Timeout',
	505: 'HTTP Version Not Supported',
	506: 'Variant Also Negotiates',
	507: 'Insufficient Storage',
	508: 'Loop Detected',
	510: 'Not Extended',
	511: 'Network Authentication Required',
}

#Server runtime details
host = ''
port = 0

#The HTTPServer object
httpd = None

#HTTPLog object
_log = None

class HTTPError(Exception):
	def __init__(self, error, message=None):
		self.error = error
		self.message = message

class HTTPHandler(object):
	nonatomic = [ 'options', 'head', 'get' ]

	def __init__(self, request, response, groups):
		self.request = request
		self.response = response
		self.method = 'do_' + self.request.method.lower()
		self.groups = groups

	def respond(self):
		#HTTP Status 405
		if not hasattr(self, self.method):
			raise HTTPError(405)

		#If client is expecting a 100, give self a chance to check it and throw an HTTPError if necessary
		if self.request.headers.get('Expect') == '100-continue':
			self.check_continue()
			self.response.wfile.write(http_version + ' 100 ' + status_messages[100] + '\r\n\r\n')

		#Get the body for the do_* method if wanted
		if self.get_body():
			body_length = int(self.request.headers.get('Content-Length', '0'))
			self.request.body = self.request.rfile.read(body_length)

		#Run the do_* method of the implementation
		return getattr(self, self.method)()

	def check_continue(self):
		pass

	def get_body(self):
		return self.method == 'do_post' or self.method == 'do_put' or self.method == 'do_patch'

	def do_options(self):
		#Lots of magic for finding all attributes beginning with 'do_', removing the 'do_' and making it upper case, and joining the list with commas
		self.response.headers.set('Allow', ','.join([option[3:].upper() for option in dir(self) if option.startswith('do_')]))
		return 200, ''

	def do_head(self):
		#Try self again with do_get
		self.method = 'do_get'
		response = self.respond()
		#Status is always first
		status = response[0]
		#Response is always last
		response = response[-1]
		self.response.headers.set('Content-Length', len(response))
		return status, ''

class DummyHandler(HTTPHandler):
	nonatomic = True

	def __init__(self, request, response, groups, error=HTTPError(500)):
		HTTPHandler.__init__(self, request, response, groups)
		self.error = error

	def respond(self):
		raise self.error

class HTTPErrorHandler(HTTPHandler):
	nonatomic = True

	def __init__(self, request, response, groups, error=500, message=None):
		self.error = error
		self.message = message

	def respond(self):
		if self.message:
			return self.error, status_messages[self.error], self.message
		else:
			return self.error, status_messages[self.error], str(self.error) + ' - ' + status_messages[self.error]

class HTTPLog(object):
	def __init__(self, httpd_log, access_log):
		if httpd_log:
			os.makedirs(os.path.dirname(httpd_log), exist_ok=True)
			self.httpd_log = open(httpd_log, 'a', 1)
		else:
			self.httpd_log = sys.stderr

		if access_log:
			os.makedirs(os.path.dirname(access_log), exist_ok=True)
			self.access_log = open(access_log, 'a', 1)
		else:
			self.access_log = sys.stderr


	def write(self, message):
		self.httpd_log.write(message + '\n')

	def access_write(self, message):
		self.access_log.write(message + '\n')

	def request(self, host, request, code='-', size='-', rfc931='-', authuser='-'):
		self.access_write(host + ' ' + rfc931 + ' ' + authuser + ' ' + time.strftime('[%d/%b/%Y:%H:%M:%S %z]') + ' "' + request + '" ' + code + ' ' + size)

	def info(self, message):
		self.write('INFO: ' + message)

	def warn(self, message):
		self.write('WARN: ' + message)

	def error(self, message):
		self.write('ERROR: ' + message)

	def exception(self):
		self.error('Caught exception:\n\t' + traceback.format_exc().replace('\n', '\n\t'))

class HTTPHeaders(object):
	def __init__(self):
		self.headers = {}

	def __iter__(self):
		for key in self.headers.keys():
			yield self.retrieve(key)
		yield '\r\n'

	def __len__(self):
		return len(self.headers)

	def add(self, header):
		key, value = (item.strip() for item in header.rstrip('\r\n').split(':', 1))
		self.set(key.lower(), value)

	def get(self, key, default=None):
		return self.headers.get(key.lower(), default)

	def set(self, key, value):
		self.headers[key.lower()] = str(value)

	def unset(self, key):
		del self.headers[key.lower()]

	def retrieve(self, key):
		return key.lower().title() + ': ' + self.get(key) + '\r\n'

class HTTPResponse(object):
	def __init__(self, request):
		self.request = request
		self.wfile = request.wfile
		self.server = request.server
		self.headers = HTTPHeaders()

	def handle(self):
		try:
			try:
				atomic = not self.request.method.lower() in self.request.handler.nonatomic
			except TypeError:
				atomic = not self.request.handler.nonatomic

			#Atomic handling of resources - wait for resource to become available if necessary
			if atomic:
				while self.request.resource in self.server.locks:
					time.sleep(0.01)

			#Do appropriate resource locks and try to get HTTP status, response text, and possibly status message
			if atomic:
				self.server.locks.append(self.request.resource)
			try:
				response = self.request.handler.respond()
			except Exception as e:
				#Extract info from an HTTPError
				if isinstance(e, HTTPError):
					error = e.error
					message = e.message
				else:
					_log.exception()
					error = 500
					message = None

				#Find an appropriate error handler, defaulting to HTTPErrorHandler
				s_error = str(error)
				error_handler = HTTPErrorHandler(self.request.handler.request, self.request.handler.response, self.request.handler.groups, error, message)
				for regex, handler in self.server.error_routes.items():
					match = regex.match(s_error)
					if match:
						error_handler = handler(self.request.handler.request, self.request.handler.response, self.request.handler.groups, error, message)

				#Use the error response as normal
				response = error_handler.respond()
			finally:
				if atomic:
					self.server.locks.remove(self.request.resource)

			#Get data from response
			try:
				status, response = response
				status_msg = status_messages[status]
			except ValueError:
				status, status_msg, response = response

			#Convert response to bytes if necessary
			if not isinstance(response, bytes):
				response = response.encode(default_encoding)

			#If Content-Length has not already been set, do it
			if not self.headers.get('Content-Length'):
				self.headers.set('Content-Length', len(response))

			#Set a few necessary headers (that the handler should not change)
			self.headers.set('Server', server_version)
			self.headers.set('Date', time.strftime('%a, %d %b %Y %H:%M:%S %Z', time.gmtime()))
		except:
			#Catch the most general errors and tell the client with the least likelihood of throwing another exception
			status = 500
			status_msg = status_messages[500]
			response = ('500 - ' + status_messages[500]).encode(default_encoding)
			_log.exception()
		finally:
			_log.request(self.request.client_address[0], self.request.request_line, code=str(status), size=str(len(response)))

			#If writes fail, the streams are probably closed so ignore the error
			try:
				#Send HTTP response
				self.wfile.write((http_version + ' ' + str(status) + ' ' + status_msg + '\r\n').encode(http_encoding))

				#Have headers written
				for header in self.headers:
					self.wfile.write(header.encode(http_encoding))

				#Write response
				self.wfile.write(response)
			except:
				pass

class HTTPRequest(socketserver.StreamRequestHandler):
	def __init__(self, request, client_address, server, timeout=None):
		self.timeout = timeout
		socketserver.StreamRequestHandler.__init__(self, request, client_address, server)

	def handle(self):
		#Get request line
		try:
			request = str(self.rfile.readline(max_request_size), http_encoding)
		#If read hits timeout or has some other error, ignore the request
		except:
			self.keepalive = False
			return
		self.request_line = request.rstrip('\r\n')

		#Set some reasonable defaults and create a response in case the worst happens and we need to tell the client
		self.method = ''
		self.resource = ''
		self.headers = HTTPHeaders()
		self.response = HTTPResponse(self)
		self.keepalive = True

		try:
			#HTTP Status 414
			#If line does not end in \r\n, it must be longer than the buffer
			if len(request) == max_request_size and request[-2:] != '\r\n':
				raise HTTPError(414)

			#Try the request line and error out if can't parse it
			try:
				self.method, self.resource, self.request_http = self.request_line.split()
			#HTTP Status 400
			except ValueError:
				raise HTTPError(400)

			#HTTP Status 505
			if self.request_http != http_version:
				raise HTTPError(505)

			#Read and parse request headers
			while True:
				line = str(self.rfile.readline(max_line_size), http_encoding)

				#HTTP Status 431
				#If line does not end in \r\n, it must be longer than the buffer
				if line[-2:] != '\r\n':
					raise HTTPError(431)

				#Hit end of headers
				if line == '\r\n':
					break

				#HTTP Status 431
				if len(self.headers) >= max_headers:
					raise HTTPError(431)

				self.headers.add(line)

			#If we are requested to close the connection after we finish, do so
			if self.headers.get('Connection') == 'close':
				self.keepalive = False

			#Find a matching regex to handle the request with
			self.handler = None
			for regex, handler in self.server.routes.items():
				match = regex.match(self.resource)
				if match:
					self.handler = handler(self, self.response,  match.groups())

			#HTTP Status 404
			if self.handler == None:
				raise HTTPError(404)
		#Use DummyHandler so the error is raised again when ready for response
		except Exception as e:
			self.handler = DummyHandler(self, self.response, None, e)
		finally:
			#We finished listening and handling early errors and so let a response class now finish up the job of talking
			self.response.handle()

class HTTPServer(socketserver.ThreadingTCPServer):
	def __init__(self, address, routes, error_routes={}, keepalive=5, timeout=8, keyfile=None, certfile=None):
		self.keepalive = keepalive
		self.request_timeout = timeout

		#For atomic handling of resources
		self.locks = []

		#Make route dictionaries
		self.routes = {}
		self.error_routes = {}

		#Compile the regex routes and add them
		for regex, handler in routes.items():
			self.routes[re.compile('^' + regex + '$')] = handler
		for regex, handler in error_routes.items():
			self.error_routes[re.compile('^' + regex + '$')] = handler

		socketserver.ThreadingTCPServer.__init__(self, address, None)

		#Add SSL if necessary information specified
		if keyfile and certfile:
			self.socket = ssl.wrap_socket(self.socket, keyfile, certfile, server_side=True)

	def server_bind(self):
		global host, port
		socketserver.TCPServer.server_bind(self)
		host, port = self.server_address[:2]
		_log.info('Serving HTTP on ' + host + ':' + str(port))

	def finish_request(self, request, client_address):
		#Keep alive by continually accepting requests - set self.keepalive to None (or 0) to effectively disable
		handler = HTTPRequest(request, client_address, self, self.request_timeout)
		while self.keepalive and handler.keepalive:
			#Give them self.keepalive after each request to make another
			handler = HTTPRequest(request, client_address, self, self.keepalive)

def init(address, routes, error_routes={}, log=HTTPLog(None, None), keepalive=5, timeout=8, keyfile=None, certfile=None):
	global httpd, _log

	_log = log

	httpd = HTTPServer(address, routes, error_routes, keepalive, timeout, keyfile, certfile)

def deinit():
	global httpd, _log

	httpd.server_close()
	httpd = None

	_log = None

def start():
	threading.Thread(target=httpd.serve_forever).start()
	_log.info('Server started')

def stop():
	httpd.shutdown()
	_log.info('Server stopped')

def is_running():
	if httpd == None:
		return False

	return not httpd._BaseServer__is_shut_down.is_set()
