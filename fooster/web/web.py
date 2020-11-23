import collections
import io
import logging
import multiprocessing
import os
import queue
import re
import selectors
import signal
import socket
import ssl
import sys
import time


# export everything
__all__ = ['server_version', 'http_version', 'http_encoding', 'default_encoding', 'start_method', 'max_line_size', 'max_headers', 'max_request_size', 'stream_chunk_size', 'status_messages', 'mktime', 'mklog', 'HTTPServer', 'HTTPHandler', 'HTTPErrorHandler', 'HTTPHandlerWrapper', 'HTTPError', 'HTTPHeaders', 'HTTPLogFormatter', 'HTTPLogFilter', 'default_log', 'default_http_log']


# module details
__version__ = '0.4.0rc1'


# server details
server_version = 'fooster-web/' + __version__
http_version = ['HTTP/1.0', 'HTTP/1.1']
http_encoding = 'iso-8859-1'
default_encoding = 'utf-8'
if sys.version_info >= (3, 7):
    start_method = 'spawn'
else:
    start_method = 'fork'

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
    103: 'Early Hints',

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
    413: 'Payload Too Large',
    414: 'URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Range Not Satisfiable',
    417: 'Expectation Failed',
    418: 'I\'m a teapot',
    421: 'Misdirected Request',
    422: 'Unprocessable Entity',
    423: 'Locked',
    424: 'Failed Dependency',
    425: 'Too Early',
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


# helper functions
def mktime(timeval, tzname='GMT'):
    return time.strftime('%a, %d %b %Y %H:%M:%S {}'.format(tzname), timeval)


def mklog(name, access_log=False):
    if name:
        log = logging.getLogger(name)
    else:
        if access_log:
            log = logging.getLogger('http')
        else:
            log = logging.getLogger('web')

    if access_log:
        handler = logging.StreamHandler(sys.stdout)
        handler.addFilter(HTTPLogFilter())
        handler.setFormatter(HTTPLogFormatter())
        log.addHandler(handler)
        log.setLevel(logging.INFO)
    else:
        handler = logging.StreamHandler(sys.stderr)
        log.addHandler(handler)
        log.setLevel(logging.INFO)

    return log


class ResLock:
    def __init__(self, sync):
        self.lock = sync.Lock()
        self.resources = sync.dict()

        self.delay = 0.05

    def acquire(self, request, resource, write):
        request_pid = os.getpid()
        request_id = id(request)

        with self.lock:
            # get lock info
            try:
                lock_readers, lock_processes, lock_pid, lock_request = self.resources[resource]
            except KeyError:
                lock_readers, lock_processes, lock_pid, lock_request = 0, 0, None, None

            # re-enter if we own the request and the same request holds the lock
            if lock_pid and lock_request and lock_pid == request_pid and lock_request == request_id:
                # mark re-entry with another process in the count
                lock_processes += 1

                self.resources[resource] = lock_readers, lock_processes, lock_pid, lock_request

                return True

            # fail if request has write lock
            if lock_request:
                return False

            # increment processes using lock
            lock_processes += 1

            # if a read or write
            if write:
                # update controlling request
                lock_pid = request_pid
                lock_request = request_id

                # wait for readers
                while lock_readers > 0:
                    self.resources[resource] = lock_readers, lock_processes, lock_pid, lock_request
                    self.lock.release()
                    time.sleep(self.delay)
                    self.lock.acquire()
                    lock_readers, lock_processes, lock_pid, lock_request = self.resources[resource]
            else:
                # update readers
                lock_readers += 1

            self.resources[resource] = lock_readers, lock_processes, lock_pid, lock_request

        return True

    def release(self, resource, write):
        with self.lock:
            # get lock info
            try:
                lock_readers, lock_processes, lock_pid, lock_request = self.resources[resource]
            except KeyError as error:
                raise RuntimeError('released unlocked lock') from error

            # decrement process
            lock_processes -= 1

            if not write:
                # decrement this reader
                lock_readers -= 1

            # clean up lock if done with
            if lock_processes <= 0:
                del self.resources[resource]
            else:
                self.resources[resource] = lock_readers, lock_processes, lock_pid, lock_request

    def clean(self, pid):
        with self.lock:
            for resource in list(self.resources.keys()):
                _lock_readers, _lock_processes, lock_pid, _lock_request = self.resources[resource]

                if lock_pid == pid:
                    del self.resources[resource]


class HTTPLogFilter(logging.Filter):
    def filter(self, record):
        record.host, record.request, record.code, record.size, record.ident, record.authuser = record.msg

        return True


class HTTPLogFormatter(logging.Formatter):
    def __init__(self, fmt='{host} {ident} {authuser} [{asctime}] "{request}" {code} {size}', datefmt='%d/%b/%Y:%H:%M:%S %z', style='{', **kwargs):
        logging.Formatter.__init__(self, fmt, datefmt, style, **kwargs)


class HTTPHeaders:
    def __init__(self):
        # lower case header -> [value1, ...]
        self.headers = {}
        # lower case header -> actual case header
        self.headers_actual = {}

    def __iter__(self):
        for key in self.headers:
            yield self.retrieve(key)
        yield '\r\n'

    def __contains__(self, key):
        return key.lower() in self.headers

    def __len__(self):
        return len(self.headers)

    def __getitem__(self, key):
        return self.headers[key.lower()][-1]

    def __setitem__(self, key, value):
        self.set(key, value)

    def __delitem__(self, key):
        self.remove(key)

    def clear(self):
        self.headers.clear()
        self.headers_actual.clear()

    def add(self, header):
        # HTTP Status 431
        # check if there are too many headers
        if len(self) >= max_headers:
            raise HTTPError(431)

        # HTTP Status 431
        # check if an individual header is too large
        if len(header) > max_line_size:
            raise HTTPError(431, status_message=(header.split(':', 1)[0] + ' Header Too Large'))

        # HTTP Status 400
        # sanity checks for headers
        if header[-2:] != '\r\n' or ':' not in header:
            raise HTTPError(400)

        # magic for removing newline on header, splitting at the first colon, and removing all extraneous whitespace
        key, value = (item.strip() for item in header[:-2].split(':', 1))
        self.set(key, value)

    def getlist(self, key, default=None):
        if default is None:
            return self.headers[key.lower()]
        else:
            return self.headers.get(key.lower(), default)

    def get(self, key, default=None):
        return self.getlist(key, [default])[-1]

    def set(self, key, value, overwrite=False):
        if not isinstance(key, str):
            raise TypeError('\'key\' can only be of type \'str\'')
        if not isinstance(value, str):
            raise TypeError('\'value\' can only be of type \'str\'')
        dict_key = key.lower()
        if not overwrite and dict_key in self.headers:
            self.headers[dict_key].append(value)
        else:
            self.headers[dict_key] = [value]
        self.headers_actual[dict_key] = key

    def remove(self, key):
        dict_key = key.lower()
        del self.headers[dict_key]
        del self.headers_actual[dict_key]

    def retrieve(self, key):
        dict_key = key.lower()
        return ''.join(self.headers_actual[dict_key] + ': ' + value + '\r\n' for value in self.getlist(key))


class HTTPError(Exception):
    def __init__(self, code, message=None, headers=None, status_message=None):
        self.code = code
        self.message = message
        self.headers = headers
        self.status_message = status_message

        if self.status_message is None:
            self.status_message = status_messages[self.code]

        if self.message:
            error_str = self.message
        else:
            error_str = str(self.code) + ' - ' + self.status_message

        if isinstance(error_str, bytes):
            error_str = error_str.decode()

        super().__init__(error_str)


class HTTPHandler:
    reader = ['options', 'head', 'get']

    def __init__(self, request, response, groups):
        self.server = request.server
        self.request = request
        self.response = response
        self.method = self.request.method.lower()
        self.groups = groups

    def encode(self, body):  # pylint: disable=no-self-use
        return body

    def decode(self, body):  # pylint: disable=no-self-use
        return body

    def methods(self):
        # things not to show
        hidden = []

        # hide head when there is no get
        if not hasattr(self, 'do_get'):
            hidden.append('head')

        # lots of magic for finding all lower case attributes beginning with 'do_' and removing the 'do_'
        return (option[3:] for option in dir(self) if option.startswith('do_') and option.islower() and option[3:] not in hidden)

    def respond(self):
        # HTTP Status 405
        if not hasattr(self, 'do_' + self.method):
            error_headers = HTTPHeaders()
            error_headers.set('Allow', ','.join(method.upper() for method in self.methods()), True)
            raise HTTPError(405, headers=error_headers)

        # get the body for the method if wanted
        if self.get_body():
            try:
                body_length = int(self.request.headers.get('Content-Length', '0'))
            except ValueError as error:
                raise HTTPError(400) from error

            # HTTP Status 413
            if max_request_size and body_length > max_request_size:
                raise HTTPError(413)

            # if client is expecting a 100, give self a chance to check it and raise an HTTPError if necessary
            if self.request.headers.get('Expect') == '100-continue':
                self.check_continue()
                self.response.wfile.write((self.request.request_http + ' 100 ' + status_messages[100] + '\r\n\r\n').encode(http_encoding))
                self.response.wfile.flush()

            # decode body from input
            self.request.body = self.decode(self.request.rfile.read(body_length))

        # run the do_* method of the implementation
        raw_response = getattr(self, 'do_' + self.method)()

        # encode body from output
        try:
            status, response = raw_response

            return status, self.encode(response)
        except ValueError:
            status, status_msg, response = raw_response

            return status, status_msg, self.encode(response)

    def check_continue(self):
        pass

    def get_body(self):
        return self.method == 'post' or self.method == 'put' or self.method == 'patch'

    def do_options(self):
        self.response.headers.set('Allow', ','.join(method.upper() for method in self.methods()), True)

        return 204, ''

    def do_head(self):
        # tell response to not write the body
        self.response.write_body = False

        # try self again with get
        self.method = 'get'
        return self.respond()


class DummyHandler(HTTPHandler):
    reader = True

    def __init__(self, request, response, groups, error=None):
        # fill in default argument values
        if error is None:
            error = HTTPError(500)

        HTTPHandler.__init__(self, request, response, groups)
        self.error = error

    def respond(self):
        raise self.error


class HTTPErrorHandler(HTTPHandler):
    reader = True

    def __init__(self, request, response, groups, error=None):
        # fill in default argument values
        if error is None:
            error = HTTPError(500)

        HTTPHandler.__init__(self, request, response, groups)
        self.error = error

    def respond(self):
        return self.error.code, self.error.status_message, str(self.error) + '\n'


class HTTPHandlerWrapper:
    def __init__(self, handler, **kwargs):
        self.handler = handler

        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        kwargs.update(self.kwargs)
        return self.handler(*args, **kwargs)


class HTTPResponse:
    def __init__(self, connection, client_address, server, request):
        self.connection = connection
        self.client_address = client_address
        self.server = server

        self.write_body = True
        self.headers = None

        self.wfile = self.connection.makefile('wb', 0)

        self.request = request

    def handle(self):
        self.write_body = True

        self.headers = HTTPHeaders()

        try:
            try:
                writer = self.request.method.lower() not in self.request.handler.reader
            except TypeError:
                writer = not self.request.handler.reader

            locked = False

            try:
                # try to get the resource, locking if atomic
                locked = self.server.res_lock.acquire(self.request, self.request.resource, writer)

                if locked:
                    # disable skip
                    self.request.skip = False
                else:
                    # put back in request queue (and skip parsing stage next time)
                    self.request.skip = True

                    # check if socket is still open
                    try:
                        # HTTP Status 100
                        self.wfile.write((self.request.request_http + ' 100 ' + status_messages[100] + '\r\n\r\n').encode(http_encoding))
                        self.wfile.flush()
                    except ConnectionError as error:
                        # bail on socket error
                        raise HTTPError(408) from error

                    return False

                # get the raw response
                raw_response = self.request.handler.respond()
            except Exception as error:  # pylint: disable=broad-except
                # if it isn't a standard HTTPError, log it and send a 500
                if not isinstance(error, HTTPError):
                    self.server.log.exception('Internal Server Error')
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

            # make sure to unlock if locked before
            if locked:
                self.server.res_lock.release(self.request.resource, writer)

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
                    self.headers.set('Transfer-Encoding', 'chunked', True)
            else:
                # convert response to bytes if necessary
                if not isinstance(response, bytes):
                    response = response.encode(default_encoding)

                # remove existing and set Content-Length for bytes
                self.headers.set('Content-Length', str(len(response)), True)
        except Exception:  # pylint: disable=broad-except
            # catch the most general errors and tell the client with the least likelihood of throwing another exception
            status = 500
            status_msg = status_messages[status]
            response = (str(status) + ' - ' + status_msg + '\n').encode(default_encoding)
            self.headers = HTTPHeaders()
            self.headers.set('Content-Length', str(len(response)), True)

            self.server.log.exception('Severe Server Error')

        # remove keepalive on errors
        if status >= 400:
            self.request.keepalive = False

        # set a few necessary headers (that should not be changed)
        if not self.request.keepalive:
            self.headers.set('Connection', 'close', True)
        self.headers.set('Server', server_version, True)
        self.headers.set('Date', mktime(time.gmtime()), True)

        # prepare response_length
        response_length = 0

        # if writes fail, the streams are probably closed so log and ignore the error
        try:
            # send HTTP response
            self.wfile.write((self.request.request_http + ' ' + str(status) + ' ' + status_msg + '\r\n').encode(http_encoding))

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

            self.wfile.flush()
        except ConnectionError:
            # bail on socket error
            pass
        except Exception:  # pylint: disable=broad-except
            self.server.log.exception('Response Write Failed')

        request_log = (self.client_address[0], self.request.request_line, str(status), str(response_length), '-', '-')

        if status >= 500:
            request_level = logging.ERROR
        elif status >= 400:
            request_level = logging.WARNING
        else:
            request_level = logging.INFO

        self.server.http_log.log(request_level, request_log)

        return True

    def close(self):
        self.wfile.close()


class HTTPRequest:
    def __init__(self, connection, client_address, server, timeout=None):
        self.connection = connection
        self.client_address = client_address
        self.server = server

        self.timeout = timeout

        self.skip = False
        self.keepalive = False
        self.headers = None

        self.request_line = ''
        self.method = ''
        self.resource = '/'
        self.request_http = 'HTTP/1.1'

        self.handler = None

        # disable nagle's algorithm
        self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)

        self.rfile = self.connection.makefile('rb', -1)

        self.response = HTTPResponse(connection, client_address, server, self)

    def handle(self, keepalive=True, initial_timeout=None):
        # we are requested to skip processing and keep the previous values
        if self.skip:
            return self.response.handle()

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
            # ignore empty lines waiting on request
            request = '\r\n'
            while request == '\r\n':
                request = self.rfile.readline(max_line_size + 1).decode(http_encoding)
        # if read hits timeout or has some other error, ignore the request
        except Exception:  # pylint: disable=broad-except
            return True

        # ignore empty requests
        if not request:
            return True

        # we have a request, go back to normal timeout
        if initial_timeout:
            self.connection.settimeout(self.timeout)

        # remove \r\n from the end
        self.request_line = request[:-2]

        # set some reasonable defaults in case the worst happens and we need to tell the client
        self.method = ''
        self.resource = '/'
        self.request_http = http_version[-1]

        try:
            # HTTP Status 414
            if len(request) > max_line_size:
                raise HTTPError(414)

            # HTTP Status 400
            if request[-2:] != '\r\n':
                raise HTTPError(400)

            # try the request line and error out if can't parse it
            try:
                self.method, resource, self.request_http = self.request_line.split()
                self.resource = resource
            # HTTP Status 400
            except ValueError as error:
                raise HTTPError(400) from error

            # HTTP Status 505
            if self.request_http not in http_version:
                raise HTTPError(505)

            # read and parse request headers
            while True:
                line = self.rfile.readline(max_line_size + 1).decode(http_encoding)

                # hit end of headers
                if line == '\r\n':
                    break

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
                    # create a dictionary of groups
                    groups = match.groupdict()
                    values = groups.values()

                    for idx, group in enumerate(match.groups()):
                        if group not in values:
                            groups[idx] = group

                    # create handler
                    self.handler = handler(self, self.response, groups)
                    break
            # HTTP Status 404
            # if loop is not broken (handler is not found), raise a 404
            else:
                raise HTTPError(404)
        # use DummyHandler so the error is raised again when ready for response
        except Exception as error:  # pylint: disable=broad-except
            self.handler = DummyHandler(self, self.response, (), error)

        # we finished listening and handling early errors and so let a response class now finish up the job of talking
        return self.response.handle()

    def close(self):
        self.rfile.close()
        self.response.close()


class HTTPServerInfo:
    def __init__(self, server):
        self.address = server.address

        self.routes = server.routes
        self.error_routes = server.error_routes

        self.keyfile = server.keyfile
        self.certfile = server.certfile
        self.using_tls = server.using_tls

        self.keepalive_timeout = server.keepalive_timeout
        self.request_timeout = server.request_timeout

        self.backlog = server.backlog

        self.num_processes = server.num_processes
        self.max_processes = server.max_processes
        self.max_queue = server.max_queue

        self.poll_interval = server.poll_interval

        self.log = server.log
        self.http_log = server.http_log

        self.socket = server.socket

        self.res_lock = server.res_lock


class HTTPServerControl:
    def __init__(self, sync, backlog):
        self.server_shutdown = sync.Value('b', 0)
        self.manager_shutdown = sync.Value('b', 0)
        self.worker_shutdown = sync.Value('b', -1)

        # request queue for worker processes
        self.requests_lock = sync.Lock()
        self.requests = sync.Value('H', 0)
        self.processes_lock = sync.Lock()
        self.processes = sync.Value('H', 0)

        # create queue to signal available connections
        self.available = sync.Queue(backlog)


class HTTPWorker:
    def __init__(self, control, info, num):
        # save server stuff
        self.control = control
        self.info = info

        # save worker num
        self.num = num

        # run self
        process = multiprocessing.get_context(start_method).Process(target=self.run, name='http-worker')
        process.start()
        self.process = process

    def run(self):
        # add tls to socket if configured
        if self.info.using_tls:
            context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(self.info.certfile, self.info.keyfile)
            sock = context.wrap_socket(self.info.socket, server_side=True)
        else:
            sock = self.info.socket

        # create local queue for parsed requests
        request_queue = queue.Queue()

        # loop over selector
        while self.control.worker_shutdown.value != -2 and self.control.worker_shutdown.value != self.num:
            try:
                # wait for ready connection
                self.control.available.get(request_queue.empty(), self.info.poll_interval)

                try:
                    # get the request
                    request, client_address = sock.accept()
                except BlockingIOError:
                    # ignore lack of request
                    request, client_address = None, None
                except OSError:
                    # bail on socket error
                    continue
            except queue.Empty:
                # ignore lack of request
                request, client_address = None, None

            # verify and process request
            if request:
                try:
                    # create a new HTTPRequest and put it on the queue (handler, keepalive, initial_timeout, handled)
                    request_queue.put((HTTPRequest(request, client_address, self.info, self.info.request_timeout), (self.info.keepalive_timeout is not None), None, True))

                    with self.control.requests_lock:
                        self.control.requests.value += 1
                except Exception:  # pylint: disable=broad-except
                    self.info.log.exception('Connection Error')
                    self.shutdown(request)

            try:
                # get next request
                handler, keepalive, initial_timeout, handled = request_queue.get_nowait()
            except queue.Empty:
                # continue loop to check for shutdown and try again
                continue

            # if this request not previously handled, wait a bit for resource to become free
            if not handled:
                time.sleep(self.info.poll_interval)

            # handle request
            try:
                handled = handler.handle(keepalive, initial_timeout)
            except Exception:  # pylint: disable=broad-except
                handled = True
                handler.keepalive = False
                self.info.log.exception('Request Handling Error')

            if not handled:
                # finish handling later
                request_queue.put((handler, keepalive, initial_timeout, False))

                with self.control.requests_lock:
                    self.control.requests.value += 1
            elif handler.keepalive:
                # handle again later
                request_queue.put((handler, keepalive, self.info.keepalive_timeout, True))

                with self.control.requests_lock:
                    self.control.requests.value += 1
            else:
                # close handler and request
                handler.close()
                self.shutdown(handler.connection)

            # mark task as done
            request_queue.task_done()

            with self.control.requests_lock:
                self.control.requests.value -= 1

    def shutdown(self, connection):  # pylint: disable=no-self-use
        try:
            connection.shutdown(socket.SHUT_WR)
            connection.close()
        except OSError:
            pass


class HTTPManager:
    def __init__(self, control, info):
        # save server stuff
        self.control = control
        self.info = info

        # run self
        process = multiprocessing.get_context(start_method).Process(target=self.run, name='http-manager')
        process.start()
        self.process = process

    def run(self):
        try:
            # create each worker process and store it in a list
            workers = []
            with self.control.processes_lock:
                self.control.processes.value = 0
            for idx in range(self.info.num_processes):
                workers.append(HTTPWorker(self.control, self.info, idx))
                with self.control.processes_lock:
                    self.control.processes.value += 1

            # manage the workers and queue
            while not self.control.manager_shutdown.value:
                # make sure all processes are alive and restart dead ones
                for idx, worker in enumerate(workers):
                    if not worker.process.is_alive():
                        self.info.log.warning('Worker ' + str(idx) + ' died: cleaning locks and starting another in its place')
                        self.info.res_lock.clean(workers[idx].process.pid)
                        workers[idx] = HTTPWorker(self.control, self.info, idx)

                # if dynamic scaling enabled
                if self.info.max_queue:
                    # if we hit the max queue size, increase processes if not at max or max is None
                    if self.control.requests.value >= self.info.max_queue and (not self.info.max_processes or len(workers) < self.info.max_processes):
                        workers.append(HTTPWorker(self.control, self.info, len(workers)))
                        with self.control.processes_lock:
                            self.control.processes.value += 1
                    # if we are above normal process size, stop one if queue is free again
                    elif len(workers) > self.info.num_processes and self.control.requests.value == 0:
                        self.control.worker_shutdown.value = len(workers) - 1
                        workers.pop().process.join()
                        with self.control.processes_lock:
                            self.control.processes.value -= 1
                        self.control.worker_shutdown.value = -1

                time.sleep(self.info.poll_interval)
        finally:
            # tell all workers to shutdown
            self.control.worker_shutdown.value = -2

            # wait for each worker process to quit
            for worker in workers:
                worker.process.join()

            self.control.worker_shutdown.value = -1
            workers = None
            with self.control.processes_lock:
                self.control.processes.value = 0


class HTTPSelector:
    def __init__(self, control, info):
        # save server stuff
        self.control = control
        self.info = info

        # run self
        process = multiprocessing.get_context(start_method).Process(target=self.run, name='http-server')
        process.start()
        self.process = process

    def run(self):
        # create the worker manager process that will handle the workers and their dynamic growth
        manager = HTTPManager(self.control, self.info)

        # select self
        with selectors.DefaultSelector() as selector:
            selector.register(self.info.socket, selectors.EVENT_READ)

            while not self.control.server_shutdown.value:
                # wait for connection
                for _connection in selector.select(self.info.poll_interval):
                    notified = False
                    while not notified and not self.control.server_shutdown.value:
                        try:
                            # try to signal workers
                            self.control.available.put(None, True, self.info.poll_interval / (self.control.processes.value + 1))
                            notified = True
                        except queue.Full:
                            pass

                    if self.control.server_shutdown.value:
                        break

        # wait for manager process to quit
        self.control.manager_shutdown.value = 1

        manager.process.join()

        self.control.manager_shutdown.value = 0


class HTTPServer:
    def __init__(self, address, routes, error_routes=None, keyfile=None, certfile=None, *, keepalive=5, timeout=20, backlog=5, num_processes=2, max_processes=6, max_queue=4, poll_interval=0.2, log=None, http_log=None):
        # fill in default argument values
        if error_routes is None:
            error_routes = {}

        # save server address
        self.address = address

        # make route dictionaries
        self.routes = collections.OrderedDict()
        self.error_routes = collections.OrderedDict()

        # compile the regex routes and add them
        for regex, handler in routes.items():
            self.routes[re.compile(r'^' + regex + r'$')] = handler
        for regex, handler in error_routes.items():
            self.error_routes[re.compile(r'^' + regex + r'$')] = handler

        # store constants
        self.keyfile = keyfile
        self.certfile = certfile
        self.using_tls = self.keyfile and self.certfile

        self.keepalive_timeout = keepalive
        self.request_timeout = timeout

        self.backlog = backlog

        self.num_processes = num_processes
        self.max_processes = max_processes
        self.max_queue = max_queue

        self.poll_interval = poll_interval

        # create the logs
        if log:
            self.log = log
        else:
            self.log = default_log

        if http_log:
            self.http_log = http_log
        else:
            self.http_log = default_http_log

        # selector process object
        self.selector = None

        # create manager (with SIGINT ignored)
        sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
        self.sync = multiprocessing.get_context(start_method).Manager()
        signal.signal(signal.SIGINT, sigint)

        # create process-ready server control object with manager
        self.control = HTTPServerControl(self.sync, self.backlog)

        # lock for atomic handling of resources
        self.res_lock = ResLock(self.sync)

        # prepare a TCP server
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.bind()
            self.activate()

            host, port = self.address
            self.log.info('Serving HTTP on ' + host + ':' + str(port))

            # prepare SSL
            if self.using_tls:
                self.log.info('HTTP socket encrypted with TLS')
        except BaseException:
            self.close()
            raise

        # create process-ready server info object
        self.info = HTTPServerInfo(self)

    def bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.address)

        # store back potentially different address
        self.address = self.socket.getsockname()[:2]

    def activate(self):
        self.socket.listen(self.backlog)
        self.socket.setblocking(False)

    def close(self, timeout=None):
        if self.is_running():
            self.stop(timeout)

        self.socket.close()

    def start(self):
        if self.is_running():
            return

        # create selector (with SIGINT ignored)
        sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
        self.selector = HTTPSelector(self.control, self.info)
        signal.signal(signal.SIGINT, sigint)

        self.log.info('HTTP server started')

    def stop(self, timeout=None):
        if not self.is_running():
            return

        self.shutdown()
        self.selector.process.join(timeout)

        self.control.server_shutdown.value = 0
        self.selector = None

        self.log.info('HTTP server stopped')

    def is_running(self):
        return bool(self.selector and self.selector.process.is_alive())

    def join(self, timeout=None):
        self.selector.process.join(timeout)

    def shutdown(self):
        self.control.server_shutdown.value = 1


# defaults
default_log = mklog('web')
default_http_log = mklog('http', access_log=True)
