import io
import os
import queue
import re
import socket
import socketserver
import ssl
import sys
import time
import traceback
import threading

#Module details
name = 'web.py'
version = '0.1b2'

#Server details
server_version = name + '/' + version
http_version = 'HTTP/1.1'
http_encoding = 'iso-8859-1'
default_encoding = 'utf-8'

#Constraints
max_line_size = 4096
max_headers = 64
max_request_size = 1048576 #1 MB
stream_chunk_size = 8192

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

	def timestamp(self):
		return time.strftime('[%d/%b/%Y:%H:%M:%S %z]')

	def write(self, string):
		self.httpd_log.write(string)

	def message(self, message):
		self.write(self.timestamp() + ' ' + message + '\n')

	def access_write(self, string):
		self.access_log.write(string)

	def info(self, message):
		self.message('INFO: ' + message)

	def warn(self, message):
		self.message('WARN: ' + message)

	def error(self, message):
		self.message('ERROR: ' + message)

	def exception(self):
		self.error('Caught exception:\n\t' + traceback.format_exc().replace('\n', '\n\t'))

	def request(self, host, request, code='-', size='-', rfc931='-', authuser='-'):
		self.access_write(host + ' ' + rfc931 + ' ' + authuser + ' ' + self.timestamp() + ' "' + request + '" ' + code + ' ' + size + '\n')

class HTTPHeaders(object):
	def __init__(self):
		#Lower case header -> value
		self.headers = {}
		#Lower case header -> actual case header
		self.headers_actual = {}

	def __iter__(self):
		for key in self.headers.keys():
			yield self.retrieve(key)
		yield '\r\n'

	def __len__(self):
		return len(self.headers)

	def clear(self):
		self.headers.clear()
		self.headers_actual.clear()

	def add(self, header):
		#Magic for removing newline on header, splitting at the first colon, and removing all extraneous whitespace
		key, value = (item.strip() for item in header[:-2].split(':', 1))
		self.set(key.lower(), value)

	def get(self, key, default=None):
		return self.headers.get(key.lower(), default)

	def set(self, key, value):
		dict_key = key.lower()
		if not isinstance(value, str):
			raise TypeError('\'value\' can only be of type \'str\'')
		self.headers[dict_key] = value
		self.headers_actual[dict_key] = key

	def remove(self, key):
		dict_key = key.lower()
		del self.headers[dict_key]
		del self.headers_actual[dict_key]

	def retrieve(self, key):
		return self.headers_actual[key.lower()] + ': ' + self.get(key) + '\r\n'

class HTTPError(Exception):
	def __init__(self, code, message=None, headers=HTTPHeaders(), status_message=None):
		self.code = code
		self.message = message
		self.headers = headers
		self.status_message = status_message

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

		#If client is expecting a 100, give self a chance to check it and raise an HTTPError if necessary
		if self.request.headers.get('Expect') == '100-continue':
			self.check_continue()
			self.response.wfile.write(http_version + ' 100 ' + status_messages[100] + '\r\n\r\n')

		#Get the body for the do_* method if wanted
		if self.get_body():
			body_length = int(self.request.headers.get('Content-Length', '0'))
			#HTTP Status 413
			if max_request_size and body_length > max_request_size:
				raise HTTPError(413)
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
		return 204, ''

	def do_head(self):
		#Tell response to not write the body
		self.response.write_body = False

		#Try self again with do_get
		self.method = 'do_get'
		return self.respond()

class DummyHandler(HTTPHandler):
	nonatomic = True

	def __init__(self, request, response, groups, error=HTTPError(500)):
		HTTPHandler.__init__(self, request, response, groups)
		self.error = error

	def respond(self):
		raise self.error

class HTTPErrorHandler(HTTPHandler):
	nonatomic = True

	def __init__(self, request, response, groups, error=HTTPError(500)):
		self.error = error

	def respond(self):
		if self.error.status_message:
			status_message = self.error.status_message
		else:
			status_message = status_messages[self.error.code]

		if self.error.message:
			message = self.error.message
		else:
			message = str(self.error.code) + ' - ' + status_message + '\n'

		return self.error.code, status_message, message

class HTTPResponse(object):
	def __init__(self, connection, client_address, server, request):
		self.connection = connection
		self.client_address = client_address
		self.server = server

		self.request = request

		self.headers = HTTPHeaders()

		self.write_body = True

	def setup(self):
		self.wfile = self.connection.makefile('wb', 0)

	def handle(self):
		try:
			try:
				atomic = not self.request.method.lower() in self.request.handler.nonatomic
			except TypeError:
				atomic = not self.request.handler.nonatomic

			#Atomic handling of resources - wait for resource to become available if necessary
			while self.request.resource in self.server.locks:
				time.sleep(0.01)

			#Do appropriate resource locks and try to get HTTP status, response text, and possibly status message
			if atomic:
				self.server.locks.append(self.request.resource)
			try:
				response = self.request.handler.respond()
			except Exception as error:
				#If it isn't a standard HTTPError, log it and send a 500
				if not isinstance(error, HTTPError):
					self.server.log.exception()
					error = HTTPError(500)

				#Set headers to the error headers
				self.headers = error.headers

				#Find an appropriate error handler, defaulting to HTTPErrorHandler
				s_code = str(error.code)
				error_handler = HTTPErrorHandler(self.request.handler.request, self.request.handler.response, self.request.handler.groups, error)
				for regex, handler in self.server.error_routes.items():
					match = regex.match(s_code)
					if match:
						error_handler = handler(self.request.handler.request, self.request.handler.response, self.request.handler.groups, error)

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

			#Take care of encoding and headers
			if isinstance(response, io.IOBase):
				#Use chunked encoding if Content-Length not set
				if not self.headers.get('Content-Length'):
					self.headers.set('Transfer-Encoding', 'chunked')
			else:
				#Convert response to bytes if necessary
				if not isinstance(response, bytes):
					response = response.encode(default_encoding)

				#If Content-Length has not already been set, do it
				if not self.headers.get('Content-Length'):
					self.headers.set('Content-Length', str(len(response)))

			#Set a few necessary headers (that the handler should not change)
			if not self.request.keepalive:
				self.headers.set('Connection', 'close')
			self.headers.set('Server', server_version)
			self.headers.set('Date', time.strftime('%a, %d %b %Y %H:%M:%S %Z', time.gmtime()))
		except:
			#Catch the most general errors and tell the client with the least likelihood of throwing another exception
			status = 500
			status_msg = status_messages[500]
			response = ('500 - ' + status_messages[500] + '\n').encode(default_encoding)
			self.headers.clear()
			self.headers.set('Content-Length', str(len(response)))

			self.server.log.exception()
		finally:
			#Prepare response_length
			response_length = 0

			#If writes fail, the streams are probably closed so log and ignore the error
			try:
				#Send HTTP response
				self.wfile.write((http_version + ' ' + str(status) + ' ' + status_msg + '\r\n').encode(http_encoding))

				#Have headers written
				for header in self.headers:
					self.wfile.write(header.encode(http_encoding))

				#Write body
				if isinstance(response, io.IOBase):
					#For a stream, write chunk by chunk and add each chunk size to response_length
					try:
						#Check whether body needs to be written
						if self.write_body:
							content_length = self.headers.get('Content-Length')
							if content_length:
								#If there is a Content-Length, write that much from the stream
								bytes_left = int(content_length)
								while True:
									chunk = response.read(min(bytes_left, stream_chunk_size))
									#Give up if chunk length is zero (when content-length is longer than the stream)
									if not chunk:
										break
									bytes_left -= len(chunk)
									response_length += self.wfile.write(chunk)
							else:
								#If no Content-Length, used chunked encoding
								while True:
									chunk = response.read(stream_chunk_size)
									#Write a hex representation (without any decorations) of the length of the chunk and the chunk separated by newlines
									response_length += self.wfile.write(('{:x}'.format(len(chunk)) + '\r\n').encode(http_encoding) + chunk + '\r\n'.encode(http_encoding))
									#After chunk length is 0, break
									if not chunk:
										break
					#Cleanup
					finally:
						response.close()
				else:
					#Check whether body needs to be written
					if self.write_body and response:
						#Just write the whole response and get length
						response_length += self.wfile.write(response)
			except:
				self.server.log.exception()

			self.server.log.request(self.client_address[0], self.request.request_line, code=str(status), size=str(response_length))

	def finish(self):
		self.wfile.close()

class HTTPRequest(object):
	def __init__(self, connection, client_address, server, timeout=None, keepalive_timeout=None):
		self.connection = connection
		self.client_address = client_address
		self.server = server

		self.timeout = timeout
		self.keepalive_timeout = keepalive_timeout

		self.headers = HTTPHeaders()
		self.response = HTTPResponse(connection, client_address, server, self)

		self.keepalive = False

		self.setup()
		try:
			self.handle()
		finally:
			self.finish()

	def setup(self):
		#Enable nagle's algorithm, prepare buffered read file, and create response with unbuffered write file
		self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
		self.rfile = self.connection.makefile('rb', -1)
		self.response.setup()

	def handle(self):
		if self.keepalive_timeout:
			self.connection.settimeout(self.keepalive_timeout)
		else:
			self.connection.settimeout(self.timeout)

		#Get request line
		try:
			request = self.rfile.readline(max_line_size + 1).decode(http_encoding)
		#If read hits timeout or has some other error, ignore the request
		except:
			return

		#Ignore empty requests
		if not request:
			return

		if self.keepalive_timeout:
			self.connection.settimeout(self.timeout)

		#Remove \r\n from the end
		self.request_line = request[:-2]

		#Since we are sure we have a request, keepalive for more
		self.keepalive = True

		#Set some reasonable defaults in case the worst happens and we need to tell the client
		self.method = ''
		self.resource = ''

		try:
			#HTTP Status 414
			if len(request) > max_line_size:
				raise HTTPError(414)

			#HTTP Status 400
			if request[-2:] != '\r\n':
				raise HTTPError(400)

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
				line = self.rfile.readline(max_line_size + 1).decode(http_encoding)

				#Hit end of headers
				if line == '\r\n':
					break

				#HTTP Status 431
				#Check if an individual header is too large
				if len(line) > max_line_size:
					raise HTTPError(431, status_message=(line.split(':', 1)[0] + ' Header Too Large'))

				#HTTP Status 431
				#Check if there are too many headers
				if len(self.headers) >= max_headers:
					raise HTTPError(431)

				#HTTP Status 400
				#Sanity checks for headers
				if line[-2:] != '\r\n' or not ':' in line:
					raise HTTPError(400)

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
		except Exception as error:
			self.handler = DummyHandler(self, self.response, (), error)
		finally:
			#We finished listening and handling early errors and so let a response class now finish up the job of talking
			self.response.handle()

	def finish(self):
		self.rfile.close()
		self.response.finish()

class HTTPServer(socketserver.TCPServer):
	def __init__(self, address, routes, error_routes={}, keyfile=None, certfile=None, keepalive=5, timeout=20, threads=4, poll_interval=0.5, log=HTTPLog(None, None)):
		self.keepalive_timeout = keepalive
		self.request_timeout = timeout
		self.log = log

		#Make route dictionaries
		self.routes = {}
		self.error_routes = {}

		#Compile the regex routes and add them
		for regex, handler in routes.items():
			self.routes[re.compile('^' + regex + '$')] = handler
		for regex, handler in error_routes.items():
			self.error_routes[re.compile('^' + regex + '$')] = handler

		#Request queue for worker threads
		self.request_queue = queue.Queue()

		#For atomic handling of resources
		self.locks = []

		socketserver.TCPServer.__init__(self, address, None)

		#Add SSL if necessary information specified
		if keyfile and certfile:
			self.socket = ssl.wrap_socket(self.socket, keyfile, certfile, server_side=True)

		#Thread information
		self._BaseServer__is_shut_down.set()
		self.num_threads = threads
		self.poll_interval = poll_interval

	def is_running(self):
		return not self._BaseServer__is_shut_down.is_set()

	def close(self):
		if self.is_running():
			self.stop()

		self.server_close()

	def start(self):
		if self.is_running():
			return

		threading.Thread(target=self.serve_forever, name='HTTPServer').start()
		self.log.info('Server started')

	def stop(self):
		if not self.is_running():
			return

		self.shutdown()
		self.log.info('Server stopped')

	def server_bind(self):
		global host, port

		socketserver.TCPServer.server_bind(self)

		host, port = self.server_address[:2]
		self.log.info('Serving HTTP on ' + host + ':' + str(port))

	def serve_forever(self):
		#Taken mostly from socketserver but adds worker threads
		self._BaseServer__is_shut_down.clear()

		worker_threads = []
		for i in range(self.num_threads):
			thread = threading.Thread(target=self.process_request_thread, name='HTTPServer-Worker')
			thread.start()
			worker_threads.append(thread)

		try:
			while not self._BaseServer__shutdown_request:
				r, w, e = socketserver._eintr_retry(socketserver.select.select, [self], [], [], self.poll_interval)

				if self in r:
					self._handle_request_noblock()

				self.service_actions()
		finally:
			self.request_queue.join()

			for thread in worker_threads:
				thread.join()

			self._BaseServer__shutdown_request = False
			self._BaseServer__is_shut_down.set()

	def process_request_thread(self):
		while not self._BaseServer__shutdown_request:
			try:
				#Get next request
				request, client_address = self.request_queue.get(timeout=self.poll_interval)

				#Handle it as it is done in socketserver
				try:
					self.finish_request(request, client_address)
				except:
					self.handle_error(request, client_address)
				self.shutdown_request(request)

				#Mark task as done
				self.request_queue.task_done()
			except queue.Empty:
				#Pass to another loop iteration
				pass

	def process_request(self, request, client_address):
		self.request_queue.put((request, client_address))

	def finish_request(self, request, client_address):
		#Keep alive by continually accepting requests - set self.keepalive_timeout to None (or 0) to effectively disable
		handler = HTTPRequest(request, client_address, self, self.request_timeout)
		while self.keepalive_timeout and handler.keepalive:
			#Give them self.keepalive_timeout after each request to make another
			handler = HTTPRequest(request, client_address, self, self.request_timeout, self.keepalive_timeout)
