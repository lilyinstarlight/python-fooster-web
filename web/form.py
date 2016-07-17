import io
import os
import re
import tempfile
import urllib.parse

import web


max_multipart_fragments = 64
max_memory_size = 1048576  # 1 MB
max_file_size = 20971520 # 20 MB


class FormMixIn:
    def decode(self, body):
        content_type = self.request.headers.get('Content-Type')
        if content_type is not None and content_type.lower() == 'application/x-www-form-urlencoded':
            return urllib.parse.parse_qs(body)

        return super().decode(body)

    def get_body(self):
        return super().get_body() and not self.form

    def respond(self):
        # only try to read form if it is wanted
        if super().get_body():
            content_type = self.request.headers.get('Content-Type')

            # check content type for being multipart
            if content_type is not None:
                content_type = content_type.lower()

                content_match = re.match('multipart/form-data;\s*boundary=(.+)', content_type)
                if content_match:
                    self.form = True

                    # send a 100 continue if expected
                    if self.request.headers.get('Expect') == '100-continue':
                        self.check_continue()
                        self.response.wfile.write((web.http_version + ' 100 ' + web.status_messages[100] + '\r\n\r\n').encode(web.http_encoding))
                        self.response.wfile.flush()

                    # get boundary
                    boundary = '--' + content_match.groups()[0]
                    end = boundary + '--'

                    # add newlines
                    boundary += '\r\n'
                    end += '\r\n'

                    # http encode the boundaries
                    boundary = boundary.encode(web.http_encoding)
                    end = end.encode(web.http_encoding)

                    # eat first boundary
                    check = self.request.rfile.readline(len(boundary))
                    if check != boundary:
                        raise web.HTTPError(400)

                    # keep track of multipart fragments
                    fragments = 0

                    # create body dictionary
                    self.request.body = {}

                    # iterate over every field object
                    while True:
                        # make sure we do not parse too many fragments
                        if fragments >= max_multipart_fragments:
                            raise web.HTTPError(413)

                        # store its headers
                        headers = web.HTTPHeaders()

                        while True:
                            line = self.request.rfile.readline(web.max_line_size + 1).decode(web.http_encoding)

                            # hit end of headers
                            if line == '\r\n':
                                break

                            headers.add(line)

                        # get disposition
                        disposition = headers.get('Content-Disposition')

                        # avoid bad requests
                        if disposition is None:
                            raise web.HTTPError(400)

                        # parse disposition
                        disposition_match = re.match('form-data;\s*name="(.+)"(?:;\s*filename="(.+)")', disposition)
                        if not disposition_match:
                            raise web.HTTPError(400)
                        disposition_groups = disposition_match.groups()

                        name = disposition_groups[0]

                        # parse length
                        length = int(headers.get('Content-Length', '0'))

                        # store default mime and charset
                        mime = 'text/plain'
                        charset = web.default_encoding

                        # parse type
                        field_type = headers.get('Content-Type')
                        if field_type:
                            type_match = re.match('(.+);\s*charset=(.+)', field_type)
                            if type_match:
                                type_groups = type_match.groups()

                                mime = type_groups[0]
                                charset = type_groups[1]

                        # check if it is a file
                        if len(disposition_groups) == 2:
                            # get filename
                            filename = disposition_groups[0]

                            # store a spooled file
                            tmp = tempfile.SpooledTemporaryFile(max_memory_size + 2)

                            # iterate over all of the chunks
                            while True:
                                # read a chunk
                                chunk = self.request.rfile.readline(web.max_line_size + 2)

                                # if chunk is a boundary
                                if chunk == boundary or chunk == end:
                                    # remove '\r\n' from file and reset it back to the beginning
                                    tmp.seek(-2, io.SEEK_CUR)
                                    tmp.truncate()
                                    tmp.seek(0)

                                    # set value as a dictionary
                                    value = {'filename': filename, 'type': field_type, 'length': tmp.tell(), 'file': tmp}

                                    break

                                # be sure file does not get too big
                                if tmp.tell() > max_file_size:
                                    raise web.HTTPError(413)

                                # write chunk
                                tmp.write(chunk)

                            # check that lengths match
                            if length and value['length'] != length:
                                raise web.HTTPError(400)
                        else:
                            # content is a field
                            value = b''

                            # iterate over all of the chunks
                            while True:
                                # read a chunk
                                chunk = self.request.rfile.readline(web.max_line_size + 2)

                                # if chunk is a boundary
                                if chunk == boundary or chunk == end:
                                    # remove '\r\n' and decode value
                                    value = value[:-2].decode(charset)

                                    break

                                # be sure value does not get too big
                                if len(value) > max_memory_size:
                                    raise web.HTTPError(413)

                                # store chunk
                                value += chunk

                            # check that lengths match
                            if length and len(value) != length:
                                raise web.HTTPError(400)

                        # store value
                        self.request.body[name] = value

                        # increment fragments
                        fragments += 1

                        # stop if we hit the end
                        if chunk == end:
                            break
                else:
                    self.form = False

        return super().respond()


class FormHandler(FormMixIn, web.HTTPHandler):
    pass
