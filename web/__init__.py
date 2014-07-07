#Module details
from .web import name, version

#Server details
from .web import server_version, http_version, http_encoding, default_encoding

#Constraints
from .web import max_line_size, max_headers, max_request_size, stream_chunk_size

#Classes
from .web import HTTPServer, HTTPHandler, HTTPErrorHandler, HTTPError, HTTPHeaders, HTTPLog
