import collections
import mimetypes
import os
import re
import shutil
import urllib.parse

from fooster import web


def normpath(path):
    # special case for empty path
    if not path:
        return ''

    old_path = path.split('/')
    new_path = collections.deque()

    for entry in old_path:
        # ignore empty paths - A//B -> A/B
        if not entry:
            continue
        # ignore dots - A/./B -> A/B
        elif entry == '.':
            continue
        # go back a level by popping the last directory off (if there is one) - A/foo/../B -> A/B
        elif entry == '..':
            if len(new_path) > 0:
                new_path.pop()
        else:
            new_path.append(entry)

    # special case for leading slashes
    if old_path[0] == '':
        new_path.appendleft('')

    # special case for trailing slashes
    if old_path[-1] == '':
        new_path.append('')

    # special case for single slash left
    norm = '/'.join(new_path)
    if not norm:
        norm = '/'

    return norm


class FileHandler(web.HTTPHandler):
    filename = None
    index_files = []
    dir_index = False

    def index(self):
        # magic for stringing together everything in the directory with a newline and adding a / at the end for directories
        return ''.join(filename + '/\n' if os.path.isdir(os.path.join(self.filename, filename)) else filename + '\n' for filename in os.listdir(self.filename))

    def get_body(self):
        return False

    def do_get(self):
        if '\x00' in self.filename:
            raise web.HTTPError(400)

        try:
            if os.path.isdir(self.filename):
                # if necessary, redirect to add trailing slash
                if not self.filename.endswith('/'):
                    self.response.headers.set('Location', self.request.resource + '/')

                    return 307, ''

                # check for index file
                index = None
                for index_file in self.index_files:
                    if os.path.exists(self.filename + index_file) and os.path.isfile(self.filename + index_file):
                        index = self.filename + index_file
                        break

                if index:
                    # return index file
                    indexfile = open(index, 'rb')
                    self.response.headers.set('Content-Length', str(os.path.getsize(index)))

                    mime = mimetypes.guess_type(index)[0]
                    if mime:
                        self.response.headers.set('Content-Type', mime)

                    return 200, indexfile
                elif self.dir_index:
                    # if no index and directory indexing enabled, send a generated one
                    return 200, self.index()
                else:
                    raise web.HTTPError(403)
            else:
                file = open(self.filename, 'rb')

                # get file size from metadata
                size = os.path.getsize(self.filename)
                length = size

                # HTTP status that changes if partial data is sent
                status = 200

                # handle range header and modify file pointer and content length as necessary
                range_header = self.request.headers.get('Range')
                if range_header:
                    range_match = re.match(r'bytes=(\d+)-(\d+)?', range_header)
                    if range_match:
                        # get lower and upper bounds
                        lower = int(range_match.group(1))
                        if range_match.group(2):
                            upper = int(range_match.group(2))
                        else:
                            upper = size - 1

                        # sanity checks
                        if upper < size and upper >= lower:
                            file.seek(lower)
                            self.response.headers.set('Content-Range', 'bytes ' + str(lower) + '-' + str(upper) + '/' + str(size))
                            length = upper - lower + 1
                            status = 206

                self.response.headers.set('Content-Length', str(length))

                # tell client we allow selecting ranges of bytes
                self.response.headers.set('Accept-Ranges', 'bytes')

                # guess MIME by extension
                mime = mimetypes.guess_type(self.filename)[0]
                if mime:
                    self.response.headers.set('Content-Type', mime)

                return status, file
        except FileNotFoundError:
            raise web.HTTPError(404)
        except NotADirectoryError:
            raise web.HTTPError(404)
        except OSError:
            raise web.HTTPError(403)


class PathMixIn:
    local = ''
    remote = ''

    pathstr = None

    def respond(self):
        if self.pathstr is None:
            self.pathstr = self.groups['path'] if 'path' in self.groups else ''

        self.path = urllib.parse.unquote(self.pathstr)

        norm_request = normpath(self.path)
        if not self.path or self.path != norm_request:
            if not norm_request:
                norm_request = '/'

            self.response.headers.set('Location', self.remote.rstrip('/') + urllib.parse.quote(norm_request))

            return 307, ''

        self.filename = self.local.rstrip('/') + self.path

        return super().respond()


class PathHandler(PathMixIn, FileHandler):
    pass


class ModifyMixIn:
    def do_put(self):
        if '\x00' in self.filename:
            raise web.HTTPError(400)

        try:
            # make sure directories are there (including the given one if not given a file)
            os.makedirs(os.path.dirname(self.filename), exist_ok=True)

            # send a 100 continue if expected
            if self.request.headers.get('Expect') == '100-continue':
                self.check_continue()
                self.response.wfile.write((web.http_version[-1] + ' 100 ' + web.status_messages[100] + '\r\n\r\n').encode(web.http_encoding))
                self.response.wfile.flush()

            # open (possibly new) file and fill it with request body
            with open(self.filename, 'wb') as file:
                bytes_left = int(self.request.headers.get('Content-Length', '0'))
                while True:
                    chunk = self.request.rfile.read(min(bytes_left, web.stream_chunk_size))
                    if not chunk:
                        break
                    bytes_left -= len(chunk)
                    file.write(chunk)

            return 204, ''
        except OSError:
            raise web.HTTPError(403)


class DeleteMixIn:
    def do_delete(self):
        if '\x00' in self.filename:
            raise web.HTTPError(400)

        try:
            if os.path.isdir(self.filename):
                # recursively remove directory
                shutil.rmtree(self.filename)
            else:
                # remove single file
                os.remove(self.filename)

            return 204, ''
        except FileNotFoundError:
            raise web.HTTPError(404)
        except OSError:
            raise web.HTTPError(403)


class ModifyFileHandler(ModifyMixIn, DeleteMixIn, FileHandler):
    pass


class ModifyPathHandler(ModifyMixIn, DeleteMixIn, PathHandler):
    pass


def new(local, remote='', *, index_files=None, dir_index=False, modify=False, handler=None):
    # set the appropriate defaults depending on arguments supplied
    if not handler:
        if modify:
            handler = ModifyPathHandler
        else:
            handler = PathHandler

    if index_files is None:
        index_files = ['index.html'] if dir_index else []

    # create a file handler with the custom arguments
    class GenPathHandler(handler):
        pass

    GenPathHandler.local = local.rstrip('/')
    GenPathHandler.remote = remote.rstrip('/')
    GenPathHandler.index_files = index_files
    GenPathHandler.dir_index = dir_index

    return {remote.rstrip('/') + r'(?P<path>|/[^?#]*)(?P<query>[?#].*)?': GenPathHandler}


if __name__ == '__main__':
    import signal

    from argparse import ArgumentParser

    parser = ArgumentParser(description='quickly serve up local files over HTTP')
    parser.add_argument('-a', '--address', default='', dest='address', help='address to serve HTTP on (default: \'\')')
    parser.add_argument('-p', '--port', default=8000, type=int, dest='port', help='port to serve HTTP on (default: 8000)')
    parser.add_argument('--no-index', action='store_false', default=True, dest='indexing', help='disable directory listings')
    parser.add_argument('--allow-modify', action='store_true', default=False, dest='modify', help='allow file and directory modifications using PUT and DELETE methods')
    parser.add_argument('local_dir', nargs='?', default='.', help='local directory to serve over HTTP (default: \'.\')')

    args = parser.parse_args()

    httpd = web.HTTPServer((args.address, args.port), new(args.local_dir, dir_index=args.indexing, modify=args.modify))
    httpd.start()

    signal.signal(signal.SIGINT, lambda signum, frame: httpd.close())

    httpd.join()
