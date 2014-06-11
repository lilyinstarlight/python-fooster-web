import mimetypes
import os
import shutil

import web

_local = None
_remote = None
_dir_index = False
_modify = False

routes = {}

class FileHandler(web.HTTPHandler):
	def __init__(self, request, response, groups):
		web.HTTPHandler.__init__(self, request, response, groups)
		self.filename = _local + self.groups[0]

	def get_body(self):
		return False

	def do_get(self):
		try:
			if os.path.isdir(self.filename):
				#If necessary, redirect to add trailing slash
				if not self.filename.endswith('/'):
					self.response.headers.set('Location', self.request.resource + '/')

					return 307, ''

				#Check for index file
				index = self.filename + 'index.html'
				if os.path.exists(index) and os.path.isfile(index):
					file = open(index, 'rb')
					self.response.headers.set('Content-Type', 'text/html')
					self.response.headers.set('Content-Length', os.path.getsize(index))
					return 200, file
				elif _dir_index:
					#If no index and directory indexing enabled, return a list of what is in the directory
					return 200, '\n'.join(os.listdir(self.filename))
				else:
					raise web.HTTPError(403)
			else:
				file = open(self.filename, 'rb')

				#Guess MIME by extension
				self.response.headers.set('Content-Type', mimetypes.guess_type(self.filename)[0])

				#Get file size from metadata
				self.response.headers.set('Content-Length', os.path.getsize(self.filename))

				return 200, file
		except FileNotFoundError:
			raise web.HTTPError(404)
		except IOError:
			raise web.HTTPError(403)

	def do_put(self):
		if not _modify:
			raise web.HTTPError(403)

		try:
			#Make sure directories are there (including the given one if not given a file)
			os.makedirs(os.path.dirname(self.filename), exist_ok=True)

			#If not directory, open (possibly new) file and fill it with request body
			if not os.path.isdir(self.filename):
				with open(self.filename, 'wb') as file:
					bytes_left = int(self.request.headers.get('Content-Length', '0'))
					while True:
						chunk = self.request.rfile.read(min(bytes_left, web.stream_chunk_size))
						if not chunk:
							break
						bytes_left -= len(chunk)
						file.write(chunk)

			return 200, ''
		except IOError:
			raise web.HTTPError(403)

	def do_delete(self):
		if not _modify:
			raise web.HTTPError(403)

		try:
			if os.path.isdir(self.filename):
				#Recursively remove directory
				shutil.rmtree(self.filename)
			else:
				#Remove single file
				os.remove(self.filename)

			return 200, ''
		except FileNotFoundError:
			raise web.HTTPError(404)
		except IOError:
			raise web.HTTPError(403)

def init(local, remote='/', dir_index=False, modify=False):
	global _local, _remote, _dir_index, _modify, routes

	if not local.endswith('/'):
		local += '/'
	if not remote.endswith('/'):
		remote += '/'

	_local = local
	_remote = remote
	_dir_index = dir_index
	_modify = modify

	#If modification is allowed, get rid of max_request_size
	if _modify:
		web.max_request_size = None

	routes = { _remote + '(.*)': FileHandler }

if __name__ == "__main__":
	from argparse import ArgumentParser

	parser = ArgumentParser(description='Quickly serve up local files over HTTP')
	parser.add_argument('--no-index', action='store_false', default=True, dest='indexing', help='Disable directory listings')
	parser.add_argument('--allow-modify', action='store_true', default=False, dest='modify', help='Allow file and directory modifications using PUT and DELETE methods')
	parser.add_argument('local_dir', help='Local directory to be served as the root')

	args = parser.parse_args()

	init(args.local_dir, dir_index=args.indexing, modify=args.modify)

	web.init(('localhost', 8080), routes)
	web.start()
