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

# module details
name = 'web.py'
version = '0.1rc3'

# server details
server_version = name + '/' + version
http_version = 'HTTP/1.1'
http_encoding = 'iso-8859-1'
default_encoding = 'utf-8'

# constraints
max_line_size = 4096
max_headers = 64
max_request_size = 1048576  # 1 MB
stream_chunk_size = 8192

# standard HTTP status messages
status_messages = {
    # 1xx Informational
    100: 'Continue',
    101: 'Switching Protocols',
    102: 'Processing',

    # 2xx Success
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

    # 3xx Redirection
    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    306: 'Switch Proxy',
    307: 'Temporary Redirect',
    308: 'Permanent Redirect',

    # 4xx Client Error
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

    # 5xx Server Error
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


class ResLock(object):
    def __init__(self):
        self.locks = {}
        self.locks_count = {}
        self.locks_lock = threading.Lock()

    def acquire(self, resource):
        with self.locks_lock:
            if resource not in self.locks:
                lock = threading.Lock()
                self.locks[resource] = lock
                self.locks_count[resource] = 1
            else:
                lock = self.locks[resource]
                self.locks_count[resource] += 1

        lock.acquire()

    def release(self, resource):
        with self.locks_lock:
            lock = self.locks[resource]
            if self.locks_count[resource] == 1:
                del self.locks[resource]
                del self.locks_count[resource]
            else:
                self.locks_count[resource] -= 1

        lock.release()

    def wait(self, resource):
        with self.locks_lock:
            try:
                lock = self.locks[resource]
            except KeyError:
                return

        lock.acquire()
        lock.release()


class HTTPLog(object):
    def __init__(self, httpd_log, access_log):
        if httpd_log:
            os.makedirs(os.path.dirname(httpd_log), exist_ok=True)
            self.httpd_log = open(httpd_log, 'a', 1)
        else:
            self.httpd_log = sys.stdout

        self.httpd_log_lock = threading.Lock()

        if access_log:
            os.makedirs(os.path.dirname(access_log), exist_ok=True)
            self.access_log = open(access_log, 'a', 1)
        else:
            self.access_log = sys.stdout

        self.access_log_lock = threading.Lock()

    def timestamp(self):
        return time.strftime('[%d/%b/%Y:%H:%M:%S %z]')

    def write(self, string):
        with self.httpd_log_lock:
            self.httpd_log.write(string)

    def message(self, message):
        self.write(self.timestamp() + ' ' + message + '\n')

    def info(self, message):
        self.message('INFO: ' + message)

    def warn(self, message):
        self.message('WARN: ' + message)

    def error(self, message):
        self.message('ERROR: ' + message)

    def exception(self):
        self.error('Caught exception:\n\t' + traceback.format_exc().replace('\n', '\n\t'))

    def access_write(self, string):
        with self.access_log_lock:
            self.access_log.write(string)

    def request(self, host, request, code='-', size='-', rfc931='-', authuser='-'):
        self.access_write(host + ' ' + rfc931 + ' ' + authuser + ' ' + self.timestamp() + ' "' + request + '" ' + code + ' ' + size + '\n')


class HTTPHeaders(object):
    def __init__(self):
        # lower case header -> value
        self.headers = {}
        # lower case header -> actual case header
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
        # magic for removing newline on header, splitting at the first colon, and removing all extraneous whitespace
        key, value = (item.strip() for item in header[:-2].split(':', 1))
        self.set(key.lower(), value)

    def get(self, key, default=None):
        return self.headers.get(key.lower(), default)

    def set(self, key, value):
        if not isinstance(key, str):
            raise TypeError('\'key\' can only be of type \'str\'')
        if not isinstance(value, str):
            raise TypeError('\'value\' can only be of type \'str\'')
        dict_key = key.lower()
        self.headers[dict_key] = value
        self.headers_actual[dict_key] = key

    def remove(self, key):
        dict_key = key.lower()
        del self.headers[dict_key]
        del self.headers_actual[dict_key]

    def retrieve(self, key):
        return self.headers_actual[key.lower()] + ': ' + self.get(key) + '\r\n'


class HTTPError(Exception):
    def __init__(self, code, message=None, headers=None, status_message=None):
        self.code = code
        self.message = message
        self.headers = headers
        self.status_message = status_message


class HTTPHandler(object):
    nonatomic = ['options', 'head', 'get']

    def __init__(self, request, response, groups):
        self.request = request
        self.response = response
        self.method = self.request.method.lower()
        self.groups = groups

    def methods(self):
        # lots of magic for finding all lower case attributes beginning with 'do_' and removing the 'do_'
        return (option[3:] for option in dir(self) if option.startswith('do_') and option.islower())

    def respond(self):
        # HTTP Status 405
        if not hasattr(self, 'do_' + self.method):
            error_headers = HTTPHeaders()
            error_headers.set('Allow', ','.join(method.upper() for method in self.methods()))
            raise HTTPError(405, headers=error_headers)

        # get the body for the method if wanted
        if self.get_body():
            body_length = int(self.request.headers.get('Content-Length', '0'))

            # HTTP Status 413
            if max_request_size and body_length > max_request_size:
                raise HTTPError(413)

            # if client is expecting a 100, give self a chance to check it and raise an HTTPError if necessary
            if self.request.headers.get('Expect') == '100-continue':
                self.check_continue()
                self.response.wfile.write((http_version + ' 100 ' + status_messages[100] + '\r\n\r\n').encode(http_encoding))

            self.request.body = self.request.rfile.read(body_length)

        # run the do_* method of the implementation
        return getattr(self, 'do_' + self.method)()

    def check_continue(self):
        pass

    def get_body(self):
        return self.method == 'post' or self.method == 'put' or self.method == 'patch'

    def do_options(self):
        self.response.headers.set('Allow', ','.join(method.upper() for method in self.methods()))

        return 204, ''

    def do_head(self):
        # tell response to not write the body
        self.response.write_body = False

        # try self again with get
        self.method = 'get'
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
        HTTPHandler.__init__(self, request, response, groups)
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

        self.wfile = self.connection.makefile('wb', 0)

        self.request = request

    def handle(self):
        self.write_body = True

        self.headers = HTTPHeaders()

        try:
            try:
                nonatomic = self.request.method.lower() in self.request.handler.nonatomic
            except TypeError:
                nonatomic = self.request.handler.nonatomic

            try:
                # try to get the resource, locking if atomic
                if nonatomic:
                    self.server.res_lock.wait(self.request.resource)
                else:
                    self.server.res_lock.acquire(self.request.resource)

                # get the raw response
                raw_response = self.request.handler.respond()
            except Exception as error:
                # if it isn't a standard HTTPError, log it and send a 500
                if not isinstance(error, HTTPError):
                    self.server.log.exception()
                    error = HTTPError(500)

                # set headers to the error headers if applicable, else make a new set
                if error.headers:
                    self.headers = error.headers
                else:
                    self.headers = HTTPHeaders()

                # find an appropriate error handler, defaulting to HTTPErrorHandler
                s_code = str(error.code)
                for regex, handler in self.server.error_routes.items():
                    match = regex.match(s_code)
                    if match:
                        error_handler = handler(self.request.handler.request, self.request.handler.response, self.request.handler.groups, error)
                        break
                else:
                    error_handler = HTTPErrorHandler(self.request.handler.request, self.request.handler.response, self.request.handler.groups, error)

                # use the error response as normal
                raw_response = error_handler.respond()
            finally:
                # make sure to unlock if locked before
                if not nonatomic:
                    self.server.res_lock.release(self.request.resource)

            # get data from response
            try:
                status, response = raw_response
                status_msg = status_messages[status]
            except ValueError:
                status, status_msg, response = raw_response

            # take care of encoding and headers
            if isinstance(response, io.IOBase):
                # use chunked encoding if Content-Length not set
                if not self.headers.get('Content-Length'):
                    self.headers.set('Transfer-Encoding', 'chunked')
            else:
                # convert response to bytes if necessary
                if not isinstance(response, bytes):
                    response = response.encode(default_encoding)

                # set Content-Length for bytes
                self.headers.set('Content-Length', str(len(response)))
        except:
            # catch the most general errors and tell the client with the least likelihood of throwing another exception
            status = 500
            status_msg = status_messages[status]
            response = (str(status) + ' - ' + status_msg + '\n').encode(default_encoding)
            self.headers = HTTPHeaders()
            self.headers.set('Content-Length', str(len(response)))

            self.server.log.exception()
        finally:
            # set a few necessary headers (that should not be changed)
            if not self.request.keepalive:
                self.headers.set('Connection', 'close')
            self.headers.set('Server', server_version)
            self.headers.set('Date', time.strftime('%a, %d %b %Y %H:%M:%S %Z', time.gmtime()))

            # prepare response_length
            response_length = 0

            # if writes fail, the streams are probably closed so log and ignore the error
            try:
                # send HTTP response
                self.wfile.write((http_version + ' ' + str(status) + ' ' + status_msg + '\r\n').encode(http_encoding))

                # have headers written
                for header in self.headers:
                    self.wfile.write(header.encode(http_encoding))

                # write body
                if isinstance(response, io.IOBase):
                    # for a stream, write chunk by chunk and add each chunk size to response_length
                    try:
                        # check whether body needs to be written
                        if self.write_body:
                            content_length = self.headers.get('Content-Length')
                            if content_length:
                                # if there is a Content-Length, write that much from the stream
                                bytes_left = int(content_length)
                                while True:
                                    chunk = response.read(min(bytes_left, stream_chunk_size))
                                    # give up if chunk length is zero (when content-length is longer than the stream)
                                    if not chunk:
                                        break
                                    bytes_left -= len(chunk)
                                    response_length += self.wfile.write(chunk)
                            else:
                                # if no Content-Length, used chunked encoding
                                while True:
                                    chunk = response.read(stream_chunk_size)
                                    # write a hex representation (without any decorations) of the length of the chunk and the chunk separated by newlines
                                    response_length += self.wfile.write(('{:x}'.format(len(chunk)) + '\r\n').encode(http_encoding) + chunk + '\r\n'.encode(http_encoding))
                                    # after chunk length is 0, break
                                    if not chunk:
                                        break
                    # cleanup
                    finally:
                        response.close()
                else:
                    # check whether body needs to be written
                    if self.write_body and response:
                        # just write the whole response and get length
                        response_length += self.wfile.write(response)
            except:
                self.server.log.exception()

            self.wfile.flush()

            self.server.log.request(self.client_address[0], self.request.request_line, code=str(status), size=str(response_length))

    def close(self):
        self.wfile.close()


class HTTPRequest(object):
    def __init__(self, connection, client_address, server, timeout=None):
        self.connection = connection
        self.client_address = client_address
        self.server = server

        self.timeout = timeout

        # disable nagle's algorithm
        self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)

        self.rfile = self.connection.makefile('rb', -1)

        self.response = HTTPResponse(connection, client_address, server, self)

    def handle(self, keepalive=True, initial_timeout=None):
        # default to no keepalive in case something happens while even trying ensure we have a request
        self.keepalive = False

        self.headers = HTTPHeaders()

        # if initial_timeout is set, only wait that long for the initial request line
        if initial_timeout:
            self.connection.settimeout(initial_timeout)
        else:
            self.connection.settimeout(self.timeout)

        # get request line
        try:
            request = self.rfile.readline(max_line_size + 1).decode(http_encoding)
        # if read hits timeout or has some other error, ignore the request
        except:
            return

        # ignore empty requests
        if not request:
            return

        # we have a request, go back to normal timeout
        if initial_timeout:
            self.connection.settimeout(self.timeout)

        # remove \r\n from the end
        self.request_line = request[:-2]

        # set some reasonable defaults in case the worst happens and we need to tell the client
        self.method = ''
        self.resource = ''

        try:
            # HTTP Status 414
            if len(request) > max_line_size:
                raise HTTPError(414)

            # HTTP Status 400
            if request[-2:] != '\r\n':
                raise HTTPError(400)

            # try the request line and error out if can't parse it
            try:
                self.method, self.resource, self.request_http = self.request_line.split()
            # HTTP Status 400
            except ValueError:
                raise HTTPError(400)

            # HTTP Status 505
            if self.request_http != http_version:
                raise HTTPError(505)

            # read and parse request headers
            while True:
                line = self.rfile.readline(max_line_size + 1).decode(http_encoding)

                # hit end of headers
                if line == '\r\n':
                    break

                # HTTP Status 431
                # check if there are too many headers
                if len(self.headers) >= max_headers:
                    raise HTTPError(431)

                # HTTP Status 431
                # check if an individual header is too large
                if len(line) > max_line_size:
                    raise HTTPError(431, status_message=(line.split(':', 1)[0] + ' Header Too Large'))

                # HTTP Status 400
                # sanity checks for headers
                if line[-2:] != '\r\n' or ':' not in line:
                    raise HTTPError(400)

                self.headers.add(line)

            # if we are requested to close the connection after we finish, do so
            if self.headers.get('Connection') == 'close':
                self.keepalive = False
            # else since we are sure we have a request and have read all of the request data, keepalive for more later (if allowed)
            else:
                self.keepalive = keepalive

            # find a matching regex to handle the request with
            for regex, handler in self.server.routes.items():
                match = regex.match(self.resource)
                if match:
                    self.handler = handler(self, self.response, match.groups())
                    break
            # HTTP Status 404
            # if loop is not broken (handler is not found), raise a 404
            else:
                raise HTTPError(404)
        # use DummyHandler so the error is raised again when ready for response
        except Exception as error:
            self.handler = DummyHandler(self, self.response, (), error)
        finally:
            # we finished listening and handling early errors and so let a response class now finish up the job of talking
            self.response.handle()

    def close(self):
        self.rfile.close()
        self.response.close()


class HTTPServer(socketserver.TCPServer):
    allow_reuse_address = True

    def __init__(self, address, routes, error_routes={}, keyfile=None, certfile=None, keepalive=5, timeout=20, num_threads=2, max_threads=6, max_queue=4, poll_interval=1, log=HTTPLog(None, None)):
        # set the log first for use in server_bind
        self.log = log

        # prepare a TCPServer
        socketserver.TCPServer.__init__(self, address, None)

        # make route dictionaries
        self.routes = {}
        self.error_routes = {}

        # compile the regex routes and add them
        for regex, handler in routes.items():
            self.routes[re.compile('^' + regex + '$')] = handler
        for regex, handler in error_routes.items():
            self.error_routes[re.compile('^' + regex + '$')] = handler

        # add TLS if necessary information specified
        if keyfile and certfile:
            self.socket = ssl.wrap_socket(self.socket, keyfile, certfile, server_side=True)
            self.log.info('Socket encrypted with TLS')
            self.using_tls = True
        else:
            self.using_tls = False

        # store constants
        self.keepalive_timeout = keepalive
        self.request_timeout = timeout

        self.num_threads = num_threads
        self.max_threads = max_threads
        self.max_queue = max_queue

        self.poll_interval = poll_interval

        # threads and flags
        self.server_thread = None

        self.manager_thread = None
        self.manager_shutdown = False

        self.worker_threads = None
        self.worker_shutdown = None

        # request queue for worker threads
        self.request_queue = queue.Queue()

        # lock for atomic handling of resources
        self.res_lock = ResLock()

    def close(self, timeout=None):
        if self.is_running():
            self.stop(timeout)

        self.server_close()

    def start(self):
        if self.is_running():
            return

        self.server_thread = threading.Thread(target=self.serve_forever, name='http-server')
        self.server_thread.start()

        self.log.info('Server started')

    def stop(self, timeout=None):
        if not self.is_running():
            return

        self.shutdown()
        self.server_thread.join(timeout)
        self.server_thread = None

        self.log.info('Server stopped')

    def is_running(self):
        return bool(self.server_thread and self.server_thread.is_alive())

    def server_bind(self):
        socketserver.TCPServer.server_bind(self)

        host, port = self.server_address[:2]
        self.log.info('Serving HTTP on ' + host + ':' + str(port))

    def process_request(self, connection, client_address):
        # create a new HTTPRequest and put it on the queue (handler, keepalive, initial_timeout)
        self.request_queue.put((HTTPRequest(connection, client_address, self, self.request_timeout), (self.keepalive_timeout is not None), None))

    def serve_forever(self):
        try:
            # create the worker manager thread that will handle the workers and their dynamic growth
            self.manager_thread = threading.Thread(target=self.manager, name='http-manager')
            self.manager_thread.start()

            socketserver.TCPServer.serve_forever(self, self.poll_interval)

            # wait for all tasks in the queue to finish
            self.request_queue.join()
        finally:
            # tell manager to shutdown
            self.manager_shutdown = True

            # wait for manager thread to quit
            self.manager_thread.join()

            self.manager_shutdown = False
            self.manager_thread = None

    def manager(self):
        try:
            # create each worker thread and store it in a list
            self.worker_threads = []
            for i in range(self.num_threads):
                thread = threading.Thread(target=self.worker, name='http-worker', args=(i,))
                self.worker_threads.append(thread)
                thread.start()

            # manage the workers and queue
            while not self.manager_shutdown:
                # make sure all threads are alive and restart dead ones
                for i, thread in enumerate(self.worker_threads):
                    if not thread.is_alive():
                        self.log.warn('Worker ' + str(i) + ' died and another is starting in its place')
                        thread = threading.Thread(target=self.worker, name='http-worker', args=(i,))
                        self.worker_threads[i] = thread
                        thread.start()

                # if dynamic scaling enabled
                if self.max_queue:
                    # if we hit the max queue size, increase threads if not at max or max is None
                    if self.request_queue.qsize() >= self.max_queue and (not self.max_threads or len(self.worker_threads) < self.max_threads):
                        thread = threading.Thread(target=self.worker, name='http-worker', args=(len(self.worker_threads),))
                        self.worker_threads.append(thread)
                        thread.start()
                    # if we are above normal thread size, stop one if queue is free again
                    elif len(self.worker_threads) > self.num_threads and self.request_queue.qsize() == 0:
                        self.worker_shutdown = len(self.worker_threads) - 1
                        self.worker_threads.pop().join()
                        self.worker_shutdown = None

                time.sleep(self.poll_interval)
        finally:
            # tell all workers to shutdown
            self.worker_shutdown = -1

            # wait for each worker thread to quit
            for thread in self.worker_threads:
                thread.join()

            self.worker_shutdown = None
            self.worker_threads = None

    def worker(self, num):
        while self.worker_shutdown != -1 and self.worker_shutdown != num:
            try:
                # get next request
                handler, keepalive, initial_timeout = self.request_queue.get(timeout=self.poll_interval)
            except queue.Empty:
                # continue loop to check for shutdown and try again
                continue

            # handle request
            try:
                handler.handle(keepalive, initial_timeout)
            except:
                self.log.exception()

            if handler.keepalive:
                # handle again
                self.request_queue.put((handler, keepalive, self.keepalive_timeout))
            else:
                # close handler and request
                handler.close()
                self.shutdown_request(handler.connection)

            # mark task as done
            self.request_queue.task_done()
