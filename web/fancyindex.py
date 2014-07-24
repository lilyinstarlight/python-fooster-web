import os
import stat
import time

import functools

import web
import web.file

index_template = '''<!DOCTYPE html>
<html>
	<head>
		<title>Index of {dirname}</title>
		<style>
			#content, #index {{
				width: 100%;
				text-align: left;
			}}
		</style>{head}
	</head>
	<body>
		<div id="content">{preindex}
			<h1>Index of {dirname}</h1>
			<table id="index">
				<thead>
					<tr><th>Filename</th><th>Size</th><th>Last Modified</th></tr>
				</thead>
				<tbody>{entries}
				</tbody>
			</table>{postindex}
		</div>{postcontent}
	</body>
</html>
'''

index_entry = '''
					<tr><td><a href="{name}">{name}</a></td><td>{size}</td><td>{modified}</td></tr>'''

class CIString(str):
	def __add__(self, other):
		return self.__class__(str.__add__(self, other))

	def __lt__(self, other):
		self_l = self.lower()
		other_l = other.lower()

		if self_l != other_l:
			return str.__lt__(self_l, other_l)

		return str.__lt__(self, other)

	def __le__(self, other):
		return self == other or self < other

	def __gt__(self, other):
		return not self < other

	def __ge__(self, other):
		return self == other or self > other

@functools.total_ordering
class DirEntry(object):
	def __init__(self, dirname, filename, sortclass=CIString):
		self.dirname = sortclass(dirname)
		self.filename = sortclass(filename)

		self.path = os.path.join(dirname, filename)

		self.stat = os.stat(self.path)

		self.mode = self.stat.st_mode
		self.modified = time.localtime(self.stat.st_mtime)

		#For directories, add a / and specify no size
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
		#Compare parents if different
		if self.dirname != other.dirname:
			return self.dirname < other.dirname

		#Directories are always lower than files
		if self.is_dir != other.is_dir:
			return self.is_dir

		#Else sort by case independent filename
		return self.filename < other.filename

def listdir(dirname, root=False, sortclass=CIString):
	direntries = []

	if not root:
		direntries.append(DirEntry(dirname, '..', sortclass))

	for filename in os.listdir(dirname):
		direntries.append(DirEntry(dirname, filename, sortclass))

	direntries.sort()

	return direntries

def human_readable_size(size, fmt='{size:.2f} {unit}', units=[ 'B', 'KiB', 'MiB', 'GiB', 'TiB' ]):
	if size == None:
		return '-'

	for unit in units:
		if size < 896:
			return fmt.format(size=size, unit=unit)

		size /= 1024

	return fmt.format(size, units[-1:])

def human_readable_time(tme, fmt='%d-%b-%y %H:%M %Z'):
	return time.strftime(fmt, tme)

class FancyIndexHandler(web.file.FileHandler):
	head = ''
	preindex = ''
	postindex = ''
	postcontent = ''
	sortclass = CIString

	def index(self):
		#Magic for formatting index_template with a title and a joined list comprehension that formats index_entry for each entry in the directory
		return index_template.format(dirname=self.request.resource, head=self.head, preindex=self.preindex, postindex=self.postindex, postcontent=self.postcontent, entries=''.join(index_entry.format(name=str(direntry), size=human_readable_size(direntry.size), modified=human_readable_time(direntry.modified)) for direntry in listdir(self.filename, self.groups[0] == '/', self.sortclass)))

def new(local, remote='/', modify=False, head='', preindex='', postindex='', postcontent='', sortclass=CIString, handler=FancyIndexHandler):
	#Create a file handler with the custom arguments
	class GenFancyIndexHandler(handler):
		pass
	GenFancyIndexHandler.head = head
	GenFancyIndexHandler.preindex = preindex
	GenFancyIndexHandler.postindex = postindex
	GenFancyIndexHandler.postcontent = postcontent
	GenFancyIndexHandler.sortclass = sortclass

	return web.file.new(local, remote, dir_index=True, modify=modify, handler=GenFancyIndexHandler)

if __name__ == '__main__':
	from argparse import ArgumentParser

	parser = ArgumentParser(description='Quickly serve up local files over HTTP with a fancy directory index')
	parser.add_argument('--allow-modify', action='store_true', default=False, dest='modify', help='Allow file and directory modifications using PUT and DELETE methods')
	parser.add_argument('local_dir', help='Local directory to be served as the root')

	args = parser.parse_args()

	httpd = web.HTTPServer(('', 8080), new(args.local_dir, modify=args.modify))
	httpd.start()
