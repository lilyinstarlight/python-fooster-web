import binascii
import collections
import io
import logging
import multiprocessing
import os
import queue
import re
import selectors
import signal
import shutil
import socket
import socketserver
import ssl
import sys
import tempfile
import time
import urllib.parse


# module details
name = 'fooster-web'
version = '0.3rc5'

# server details
server_version = name + '/' + version
http_version = ['HTTP/1.0', 'HTTP/1.1']
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
    413: 'Payload Too Large',
    414: 'URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Range Not Satisfiable',
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


def mktime(timeval, tzname='GMT'):
    return time.strftime('%a, %d %b %Y %H:%M:%S {}'.format(tzname), timeval)


class ResLock:
    class LockProxy:
        def __init__(self, dir, resource):
            self.dir = dir
            self.resource = resource

            # base64 encode resource to avoid invalid characters
            self.path = os.path.join(self.dir, binascii.hexlify(self.resource.encode(default_encoding)).decode())

            self.readers_file = os.path.join(self.path, 'readers')
            self.processes_file = os.path.join(self.path, 'processes')
            self.request_file = os.path.join(self.path, 'request')

            self.write_file = os.path.join(self.path, 'write.lock')

            # set default values if lock does not exist
            if not os.path.exists(self.path):
                os.mkdir(self.path)
                self.readers = 0
                self.processes = 0

        @property
        def readers(self):
            with open(self.readers_file, 'r') as file:
                return int(file.read())

        @readers.setter
        def readers(self, value):
            with open(self.readers_file, 'w') as file:
                file.write(str(value))

        @property
        def processes(self):
            with open(self.processes_file, 'r') as file:
                return int(file.read())

        @processes.setter
        def processes(self, value):
            with open(self.processes_file, 'w') as file:
                file.write(str(value))

        @property
        def request(self):
            try:
                with open(self.request_file, 'r') as file:
                    return int(file.read())
            except FileNotFoundError:
                return None

        @request.setter
        def request(self, value):
            with open(self.request_file, 'w') as file:
                file.write(str(value))

        def clean(self):
            os.unlink(self.readers_file)
            os.unlink(self.processes_file)
            os.unlink(self.request_file)
            os.rmdir(self.path)

        def acquire(self):
            try:
                os.close(os.open(self.write_file, os.O_CREAT | os.O_EXCL | os.O_RDWR))

                return True
            except FileExistsError:
                return False

        def release(self):
            os.unlink(self.write_file)

    def __init__(self, sync):
        self.sync = sync

        self.lock = self.sync.Lock()
        self.requests = self.sync.dict()

        self.id = os.getpid()

        self.dir = tempfile.mkdtemp()
        self.delay = 0.05

    def acquire(self, request, resource, nonatomic):
        request_id = id(request)

        with self.lock:
            # proxy a resource lock
            res_lock = ResLock.LockProxy(self.dir, resource)

            request_lock = res_lock.request

            # set request if none
            if res_lock.request is None:
                res_lock.request = request_id

                try:
                    # repropagate list
                    tmp = self.requests[self.id]
                    tmp.append(request_id)
                    self.requests[self.id] = tmp
                except KeyError:
                    self.requests[self.id] = [request_id]

            # increment processes using lock
            res_lock.processes += 1

            # re-enter if we own the request and the same request holds the lock
            if request_lock and request_lock == request_id and self.id in self.requests and request_id in self.requests[self.id]:
                return True

            # if a read or write
            if nonatomic:
                # acquire write lock
                locked = res_lock.acquire()
                if not locked:
                    # bail if lock failed
                    res_lock.processes -= 1
                    return False

                # update readers
                res_lock.readers += 1

                # release write lock
                res_lock.release()
            else:
                # acquire write lock
                locked = res_lock.acquire()
                if not locked:
                    res_lock.processes -= 1
                    return False

                # wait for readers
                while res_lock.readers > 0:
                    self.lock.release()
                    time.sleep(self.delay)
                    self.lock.acquire()

                # update controlling request
                res_lock.request = request_id

        return True

    def release(self, resource, nonatomic, last=True):
        with self.lock:
            # proxy a resource lock
            res_lock = ResLock.LockProxy(self.dir, resource)

            if res_lock.readers <= 0 and res_lock.processes <= 0:
                raise RuntimeError('release unlocked lock')

            # decrement process unless this is the only one left but not the last
            if last or res_lock.processes > 1:
                res_lock.processes -= 1

            # if all of the processes are done
            if res_lock.processes == 0:
                # clean up request id
                for id in list(self.requests.keys()):
                    # remove request from appropriate list
                    if res_lock.request in self.requests[id]:
                        # repropagate list
                        tmp = self.requests[id]
                        tmp.remove(res_lock.request)
                        self.requests[id] = tmp

                    # remove id if necessary
                    if len(self.requests[id]) == 0:
                        del self.requests[id]

                release = True
            else:
                release = False

            if nonatomic:
                # decrement this reader
                res_lock.readers -= 1
            else:
                # release write if necessary
                if release:
                    res_lock.release()

            # clean up lock if done with
            if res_lock.readers <= 0 and res_lock.processes <= 0:
                res_lock.clean()

    def clean(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class HTTPLogFilter(logging.Filter):
    def filter(self, record):
        record.host, record.request, record.code, record.size, record.ident, record.authuser = record.msg

        return True


class HTTPLogFormatter(logging.Formatter):
    def __init__(self, fmt='{host} {ident} {authuser} [{asctime}] "{request}" {code} {size}', datefmt='%d/%b/%Y:%H:%M:%S %z', style='{', **kwargs):
        logging.Formatter.__init__(self, fmt, datefmt, style, **kwargs)


class HTTPHeaders:
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

    def __getitem__(self, key):
        return self.headers[key.lower()]

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


class HTTPHandler:
    nonatomic = ['options', 'head', 'get']

    def __init__(self, request, response, groups):
        self.server = request.server
        self.request = request
        self.response = response
        self.method = self.request.method.lower()
        self.groups = groups

    def encode(self, body):
        return body

    def decode(self, body):
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
            error_headers.set('Allow', ','.join(method.upper() for method in self.methods()))
            raise HTTPError(405, headers=error_headers)

        # get the body for the method if wanted
        if self.get_body():
            try:
                body_length = int(self.request.headers.get('Content-Length', '0'))
            except ValueError:
                raise HTTPError(400)

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


class HTTPResponse:
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

            locked = False

            try:
                # try to get the resource, locking if atomic
                locked = self.server.res_lock.acquire(self.request, self.request.resource, nonatomic)

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
                    except ConnectionError:
                        # bail on socket error
                        raise HTTPError(408)

                    return False

                # get the raw response
                raw_response = self.request.handler.respond()
            except Exception as error:
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
                self.server.res_lock.release(self.request.resource, nonatomic)

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
        except Exception:
            # catch the most general errors and tell the client with the least likelihood of throwing another exception
            status = 500
            status_msg = status_messages[status]
            response = (str(status) + ' - ' + status_msg + '\n').encode(default_encoding)
            self.headers = HTTPHeaders()
            self.headers.set('Content-Length', str(len(response)))

            self.server.log.exception('Severe Server Error')

        # remove keepalive on errors
        if status >= 400:
            self.request.keepalive = False

        # set a few necessary headers (that should not be changed)
        if not self.request.keepalive:
            self.headers.set('Connection', 'close')
        self.headers.set('Server', server_version)
        self.headers.set('Date', mktime(time.gmtime()))

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
        except Exception:
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
        except Exception:
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
                self.resource = urllib.parse.unquote(resource)
            # HTTP Status 400
            except ValueError:
                raise HTTPError(400)

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
        except Exception as error:
            self.handler = DummyHandler(self, self.response, (), error)
        finally:
            # we finished listening and handling early errors and so let a response class now finish up the job of talking
            return self.response.handle()

    def close(self):
        self.rfile.close()
        self.response.close()


class HTTPServer(socketserver.TCPServer):
    allow_reuse_address = True

    def __init__(self, address, routes, error_routes={}, keyfile=None, certfile=None, keepalive=5, timeout=20, num_processes=2, max_processes=6, max_queue=4, poll_interval=0.2, log=None, http_log=None, sync=None):
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

        self.using_tls = keyfile and certfile

        self.keepalive_timeout = keepalive
        self.request_timeout = timeout

        self.num_processes = num_processes
        self.max_processes = max_processes
        self.max_queue = max_queue

        self.poll_interval = poll_interval

        # create manager and namespaces
        if sync:
            self.sync = sync
        else:
            # ignore SIGINT in manager
            orig_sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
            self.sync = multiprocessing.Manager()
            signal.signal(signal.SIGINT, orig_sigint)

        self.namespace = self.sync.Namespace()

        # processes and flags
        self.server_process = None
        self.namespace.server_shutdown = False
        self.namespace.manager_shutdown = False
        self.namespace.worker_shutdown = None

        # request queue for worker processes
        self.requests_lock = self.sync.Lock()
        self.requests = self.sync.Value('Q', 0)
        self.cur_processes_lock = self.sync.Lock()
        self.cur_processes = self.sync.Value('Q', 0)

        # lock for atomic handling of resources
        self.res_lock = ResLock(self.sync)

        # create the logs
        if log:
            self.log = log
        else:
            self.log = logging.getLogger('web')

            handler = logging.StreamHandler(sys.stderr)
            self.log.addHandler(handler)
            self.log.setLevel(logging.WARNING)

        if http_log:
            self.http_log = http_log
        else:
            self.http_log = logging.getLogger('http')

            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(HTTPLogFormatter())
            self.http_log.addHandler(handler)
            self.http_log.addFilter(HTTPLogFilter())
            self.http_log.setLevel(logging.INFO)

        # prepare a TCPServer
        socketserver.TCPServer.__init__(self, address, None)

        # prepare SSL
        if self.keyfile and self.certfile:
            self.socket = ssl.wrap_socket(self.socket, keyfile, certfile, server_side=True)
            self.log.info('Socket encrypted with TLS')

    def close(self, timeout=None):
        if self.is_running():
            self.stop(timeout)

        self.server_close()

    def start(self):
        if self.is_running():
            return

        self.server_process = multiprocessing.Process(target=self.serve_forever, name='http-server')
        self.server_process.start()

        self.log.info('Server started')

    def stop(self, timeout=None):
        if not self.is_running():
            return

        self.shutdown()
        self.server_process.join(timeout)

        self.namespace.server_shutdown = False
        self.server_process = None

        self.log.info('Server stopped')

    def is_running(self):
        return bool(self.server_process and self.server_process.is_alive())

    def join(self, timeout=None):
        self.server_process.join(timeout)

    def server_bind(self):
        socketserver.TCPServer.server_bind(self)

        host, port = self.server_address[:2]
        self.log.info('Serving HTTP on ' + host + ':' + str(port))

    def process_request(self, connection, client_address):
        # create a new HTTPRequest and put it on the queue (handler, keepalive, initial_timeout, handled)
        self.request_queue.put((HTTPRequest(connection, client_address, self, self.request_timeout), (self.keepalive_timeout is not None), None, True))

    def handle_error(self, connection, client_address):
        self.log.exception('Connection Error')

    def serve_forever(self):
        # ignore SIGINT
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        # set socket to non-blocking
        self.socket.setblocking(False)

        # create condition to signal ready connections
        self.connection_ready = self.sync.Condition()

        # create the worker manager process that will handle the workers and their dynamic growth
        self.manager_process = multiprocessing.Process(target=self.manager, name='http-manager')
        self.manager_process.start()

        # select self
        with selectors.DefaultSelector() as selector:
            selector.register(self, selectors.EVENT_READ)

            while not self.namespace.server_shutdown:
                # wait for connection
                for connection in selector.select(self.poll_interval):
                    notified = False
                    while not notified:
                        try:
                            # try to notify workers
                            with self.connection_ready:
                                self.connection_ready.notify()
                            notified = True
                        except RuntimeError:
                            time.sleep(self.poll_interval / (self.cur_processes.value + 1))

        # wait for manager process to quit
        self.namespace.manager_shutdown = True
        self.manager_process.join()

        self.namespace.manager_shutdown = False
        self.manager_process = None

        # clean up resource lock
        self.res_lock.clean()

    def shutdown(self):
        self.namespace.server_shutdown = True

    def manager(self):
        try:
            # create each worker process and store it in a list
            self.worker_processes = []
            with self.cur_processes_lock:
                self.cur_processes.value = 0
            for i in range(self.num_processes):
                process = multiprocessing.Process(target=self.worker, name='http-worker', args=(i,))
                self.worker_processes.append(process)
                with self.cur_processes_lock:
                    self.cur_processes.value += 1
                process.start()

            # manage the workers and queue
            while not self.namespace.manager_shutdown:
                # make sure all processes are alive and restart dead ones
                for i, process in enumerate(self.worker_processes):
                    if not process.is_alive():
                        self.log.warning('Worker ' + str(i) + ' died and another is starting in its place')
                        process = multiprocessing.Process(target=self.worker, name='http-worker', args=(i,))
                        self.worker_processes[i] = process
                        process.start()

                # if dynamic scaling enabled
                if self.max_queue:
                    # if we hit the max queue size, increase processes if not at max or max is None
                    if self.requests.value >= self.max_queue and (not self.max_processes or len(self.worker_processes) < self.max_processes):
                        process = multiprocessing.Process(target=self.worker, name='http-worker', args=(len(self.worker_processes),))
                        self.worker_processes.append(process)
                        with self.cur_processes_lock:
                            self.cur_processes.value += 1
                        process.start()
                    # if we are above normal process size, stop one if queue is free again
                    elif len(self.worker_processes) > self.num_processes and self.requests.value == 0:
                        self.namespace.worker_shutdown = len(self.worker_processes) - 1
                        self.worker_processes.pop().join()
                        with self.cur_processes_lock:
                            self.cur_processes.value -= 1
                        self.namespace.worker_shutdown = None

                time.sleep(self.poll_interval)
        finally:
            # tell all workers to shutdown
            self.namespace.worker_shutdown = -1

            # wait for each worker process to quit
            for process in self.worker_processes:
                process.join()

            self.namespace.worker_shutdown = None
            self.worker_processes = None
            with self.cur_processes_lock:
                self.cur_processes.value = 0

    def worker(self, num, request_queue=None):
        # create local queue for parsed requests
        self.request_queue = request_queue if request_queue is not None else queue.Queue()

        # loop over selector
        while self.namespace.worker_shutdown != -1 and self.namespace.worker_shutdown != num:
            # wait for ready connection
            with self.connection_ready:
                if self.connection_ready.wait(self.poll_interval if self.request_queue.empty() else 0):
                    try:
                        # get the request
                        request, client_address = self.get_request()
                    except BlockingIOError:
                        # ignore lack of request
                        request, client_address = None, None
                    except OSError:
                        # bail on socket error
                        return
                else:
                    # ignore lack of request
                    request, client_address = None, None

            # verify and process request
            if request:
                if self.verify_request(request, client_address):
                    try:
                        self.process_request(request, client_address)

                        with self.requests_lock:
                            self.requests.value += 1
                    except Exception:
                        self.handle_error(request, client_address)
                        self.shutdown_request(request)
                else:
                    self.shutdown_request(request)

            try:
                # get next request
                handler, keepalive, initial_timeout, handled = self.request_queue.get_nowait()
            except queue.Empty:
                # continue loop to check for shutdown and try again
                continue

            # if this request not previously handled, wait a bit for resource to become free
            if not handled:
                time.sleep(self.poll_interval)

            # handle request
            try:
                handled = handler.handle(keepalive, initial_timeout)
            except Exception:
                handled = True
                handler.keepalive = False
                self.log.exception('Request Handling Error')

            if not handled:
                # finish handling later
                self.request_queue.put((handler, keepalive, initial_timeout, False))

                with self.requests_lock:
                    self.requests.value += 1
            elif handler.keepalive:
                # handle again later
                self.request_queue.put((handler, keepalive, self.keepalive_timeout, True))

                with self.requests_lock:
                    self.requests.value += 1
            else:
                # close handler and request
                handler.close()
                self.shutdown_request(handler.connection)

            # mark task as done
            self.request_queue.task_done()

            with self.requests_lock:
                self.requests.value -= 1
