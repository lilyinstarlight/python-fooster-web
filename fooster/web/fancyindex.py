import html
import os
import stat
import time
import urllib.parse

import functools

from fooster import web
import fooster.web.file

index_template = '''<!DOCTYPE html>
<html>
    <head>
        <title>Index of {dirname}</title>
        <style>
            #content, #index {{ width: 100%; text-align: left; }}
            .filename {{ width: 55%; }}
            .size {{ width: 20%; }}
            .modified {{ width: 25%; }}
        </style>{head}
    </head>
    <body>{precontent}
        <div id="content">{preindex}
            <h1>Index of {dirname}</h1>
            <table id="index">
                <thead>
                    <tr><th class="filename">Filename</th><th class="size">Size</th><th class="modified">Last Modified</th></tr>
                </thead>
                <tbody>{entries}
                </tbody>
            </table>{postindex}
        </div>{postcontent}
    </body>
</html>
'''

index_entry = '''
                    <tr><td class="filename"><a href="{url}">{name}</a></td><td class="size">{size}</td><td class="modified">{modified}</td></tr>'''

index_content_type = 'text/html; charset=utf-8'


@functools.total_ordering
class DirEntry:
    def __init__(self, dirname, filename):
        self.dirname = dirname
        self.filename = filename

        self.dirname_l = dirname.lower()
        self.filename_l = filename.lower()

        self.path = os.path.join(dirname, filename)

        self.stat = os.stat(self.path)

        self.mode = self.stat.st_mode
        self.modified = time.localtime(self.stat.st_mtime)

        # for directories, add a / and specify no size
        if stat.S_ISDIR(self.mode):
            self.is_dir = True
            self.filename += '/'
            self.size = None
        else:
            self.is_dir = False
            self.size = self.stat.st_size

    def __repr__(self):
        return '<' + self.__class__.__name__ + ' (' + self.dirname + ') \'' + self.filename + '\'>'

    def __str__(self):
        return self.filename

    def __eq__(self, other):
        return self.path == other.path

    def __lt__(self, other):
        # compare parents if different
        if self.dirname != other.dirname:
            # if lower case names are different, compare them
            if self.dirname_l != other.dirname_l:
                return self.dirname_l < other.dirname_l

            # if nothing else, sort by dirname
            return self.dirname < other.dirname

        # directories are always less
        if self.is_dir != other.is_dir:
            return self.is_dir

        # if lower case names are different, compare them
        if self.filename_l != other.filename_l:
            return self.filename_l < other.filename_l

        # if nothing else, sort by filename
        return self.filename < other.filename


def listdir(dirname, root=False, sortclass=DirEntry):
    direntries = []

    if not root:
        direntries.append(sortclass(dirname, '..'))

    for filename in os.listdir(dirname):
        direntries.append(sortclass(dirname, filename))

    direntries.sort()

    return direntries


def human_readable_size(size, fmt='{size:.2f} {unit}', units=['B', 'KiB', 'MiB', 'GiB', 'TiB']):
    if size is None:
        return '-'

    # go up until the next to last unit and if the size still doesn't
    # get small enough, just print it
    for unit in units[:-1]:
        if size < 896:
            return fmt.format(size=size, unit=unit)

        size /= 1024

    return fmt.format(size=size, unit=units[-1])


def human_readable_time(tme, fmt='%d-%b-%Y %H:%M %Z'):
    return time.strftime(fmt, tme)


class FancyIndexHandler(fooster.web.file.FileHandler):
    head = ''
    precontent = ''
    preindex = ''
    postindex = ''
    postcontent = ''
    sortclass = DirEntry
    index_template = index_template
    index_entry = index_entry
    index_entry_join = ''
    index_content_type = index_content_type

    def index(self):
        self.response.headers.set('Content-Type', self.index_content_type)

        # magic for formatting index_template with the unquoted resource as a title and a joined list comprehension that formats index_entry for each entry in the directory
        return self.index_template.format(dirname=html.escape(urllib.parse.unquote(self.groups['path'])), head=self.head, precontent=self.precontent, preindex=self.preindex, postindex=self.postindex, postcontent=self.postcontent, entries=self.index_entry_join.join(self.index_entry.format(url=urllib.parse.quote(str(direntry)), name=html.escape(str(direntry)), size=human_readable_size(direntry.size), modified=human_readable_time(direntry.modified)) for direntry in listdir(self.filename, self.groups['path'] == '/', self.sortclass)))


def new(local, remote='', modify=False, head='', precontent='', preindex='', postindex='', postcontent='', sortclass=DirEntry, index_template=index_template, index_entry=index_entry, index_entry_join='', index_content_type=index_content_type, handler=FancyIndexHandler):
    # create a file handler with the custom arguments
    class GenFancyIndexHandler(handler):
        pass

    GenFancyIndexHandler.head = head
    GenFancyIndexHandler.precontent = precontent
    GenFancyIndexHandler.preindex = preindex
    GenFancyIndexHandler.postindex = postindex
    GenFancyIndexHandler.postcontent = postcontent

    GenFancyIndexHandler.sortclass = sortclass

    GenFancyIndexHandler.index_template = index_template
    GenFancyIndexHandler.index_entry = index_entry
    GenFancyIndexHandler.index_entry_join = index_entry_join
    GenFancyIndexHandler.index_content_type = index_content_type

    return fooster.web.file.new(local, remote, dir_index=True, modify=modify, handler=GenFancyIndexHandler)


if __name__ == '__main__':
    import signal

    from argparse import ArgumentParser

    parser = ArgumentParser(description='quickly serve up local files over HTTP with a fancy directory index')
    parser.add_argument('-a', '--address', default='', dest='address', help='address to serve HTTP on (default: \'\')')
    parser.add_argument('-p', '--port', default=8000, type=int, dest='port', help='port to serve HTTP on (default: 8000)')
    parser.add_argument('--allow-modify', action='store_true', default=False, dest='modify', help='allow file and directory modifications using PUT and DELETE methods')
    parser.add_argument('local_dir', help='local directory to serve over HTTP')

    args = parser.parse_args()

    httpd = web.HTTPServer((args.address, args.port), new(args.local_dir, modify=args.modify))
    httpd.start()

    signal.signal(signal.SIGINT, lambda signum, frame: httpd.close())

    httpd.join()
