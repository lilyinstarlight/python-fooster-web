#Module details
from .web import name, version

#Server details
from .web import server_version, http_version, http_encoding, default_encoding

#Constraints
from .web import max_line_size, max_headers, max_request_size, stream_chunk_size

#Runtime info
from .web import httpd, host, port

#Classes
from .web import HTTPError, HTTPHandler, HTTPErrorHandler, HTTPHeaders, HTTPLog

#Server methods
from .web import init, deinit, start, stop, is_running
