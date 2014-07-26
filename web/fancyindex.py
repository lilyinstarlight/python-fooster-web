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

@functools.total_ordering
class DirEntry(object):
	def __init__(self, dirname, filename):
		self.dirname = dirname
		self.filename = filename

		self.dirname_l = dirname.lower()
		self.filename_l = filename.lower()

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
			#If lower case names are different, compare them
			if self.dirname_l != other.dirname_l:
				return self.dirname_l < other.dirname_l

			#If nothing else, sort by dirname
			return self.dirname < other.dirname

		#Directories are always less
		if self.is_dir != other.is_dir:
			return self.is_dir

		#If lower case names are different, compare them
		if self.filename_l != other.filename_l:
			return self.filename_l < other.filename_l

		#If nothing else, sort by filename
		return self.filename < other.filename

def listdir(dirname, root=False, sortclass=DirEntry):
	direntries = []

	if not root:
		direntries.append(sortclass(dirname, '..'))

	for filename in os.listdir(dirname):
		direntries.append(sortclass(dirname, filename))

	direntries.sort()

	return direntries

def human_readable_size(size, fmt='{size:.2f} {unit}', units=[ 'B', 'KiB', 'MiB', 'GiB', 'TiB' ]):
	if size == None:
		return '-'

	#Go up until the next to last unit and if the size still doesn't get small enough, just print it
	for unit in units[:-1]:
		if size < 896:
			return fmt.format(size=size, unit=unit)

		size /= 1024

	return fmt.format(size=size, unit=units[-1])

def human_readable_time(tme, fmt='%d-%b-%Y %H:%M %Z'):
	return time.strftime(fmt, tme)

class FancyIndexHandler(web.file.FileHandler):
	head = ''
	preindex = ''
	postindex = ''
	postcontent = ''
	sortclass = DirEntry
	index_template = index_template
	index_entry = index_entry
	index_entry_join = ''

	def index(self):
		#Magic for formatting index_template with a title and a joined list comprehension that formats index_entry for each entry in the directory
		return self.index_template.format(dirname=self.request.resource, head=self.head, preindex=self.preindex, postindex=self.postindex, postcontent=self.postcontent, entries=self.index_entry_join.join(self.index_entry.format(name=str(direntry), size=human_readable_size(direntry.size), modified=human_readable_time(direntry.modified)) for direntry in listdir(self.filename, self.groups[0] == '/', self.sortclass)))

def new(local, remote='/', modify=False, head='', preindex='', postindex='', postcontent='', sortclass=DirEntry, index_template=index_template, index_entry=index_entry, index_entry_join='', handler=FancyIndexHandler):
	#Create a file handler with the custom arguments
	class GenFancyIndexHandler(handler):
		pass

	GenFancyIndexHandler.head = head
	GenFancyIndexHandler.preindex = preindex
	GenFancyIndexHandler.postindex = postindex
	GenFancyIndexHandler.postcontent = postcontent

	GenFancyIndexHandler.sortclass = sortclass

	GenFancyIndexHandler.index_template = index_template
	GenFancyIndexHandler.index_entry = index_entry
	GenFancyIndexHandler.index_entry_join = index_entry_join

	return web.file.new(local, remote, dir_index=True, modify=modify, handler=GenFancyIndexHandler)

if __name__ == '__main__':
	from argparse import ArgumentParser

	parser = ArgumentParser(description='Quickly serve up local files over HTTP with a fancy directory index')
	parser.add_argument('--allow-modify', action='store_true', default=False, dest='modify', help='Allow file and directory modifications using PUT and DELETE methods')
	parser.add_argument('local_dir', help='Local directory to be served as the root')

	args = parser.parse_args()

	httpd = web.HTTPServer(('', 8080), new(args.local_dir, modify=args.modify))
	httpd.start()
