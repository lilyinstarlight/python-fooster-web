import mimetypes
import os
import re
import shutil

import web

routes = {}

class FileHandler(web.HTTPHandler):
	filename = None

	def __init__(self, request, response, groups):
		web.HTTPHandler.__init__(self, request, response, groups)
		if not self.filename:
			self.filename = self.local + self.groups[0]

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
				elif self.dir_index:
					#If no index and directory indexing enabled, return a list of what is in the directory separated by newlines
					return 200, ''.join(file + '\n' for file in os.listdir(self.filename))
				else:
					raise web.HTTPError(403)
			else:
				file = open(self.filename, 'rb')

				#Get file size from metadata
				size = os.path.getsize(self.filename)
				length = size

				#HTTP status that changes if partial data is sent
				status = 200

				#Handle range header and modify file pointer and content length as necessary
				range_header = self.request.headers.get('Range')
				if range_header:
					range_match = re.match('bytes=(\d+)-(\d+)?', range_header)
					if range_match:
						groups = range_match.groups()

						#Get lower and upper bounds
						lower = int(groups[0])
						if groups[1]:
							upper = int(groups[1])
						else:
							upper = size - 1

						#Sanity checks
						if upper < size and upper >= lower:
							file.seek(lower)
							self.response.headers.set('Content-Range', 'bytes ' + str(lower) + '-' + str(upper) + '/' + str(size))
							length = upper - lower + 1
							status = 206

				self.response.headers.set('Content-Length', str(length))

				#Tell client we allow selecting ranges of bytes
				self.response.headers.set('Accept-Ranges', 'bytes')

				#Guess MIME by extension
				self.response.headers.set('Content-Type', mimetypes.guess_type(self.filename)[0])

				return status, file
		except FileNotFoundError:
			raise web.HTTPError(404)
		except IOError:
			raise web.HTTPError(403)

class ModifyFileHandler(FileHandler):
	def do_put(self):
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

			return 204, ''
		except IOError:
			raise web.HTTPError(403)

	def do_delete(self):
		try:
			if os.path.isdir(self.filename):
				#Recursively remove directory
				shutil.rmtree(self.filename)
			else:
				#Remove single file
				os.remove(self.filename)

			return 204, ''
		except FileNotFoundError:
			raise web.HTTPError(404)
		except IOError:
			raise web.HTTPError(403)

def init(local, remote='/', dir_index=False, modify=False):
	global routes

	#Set the appropriate handler if modification is allowed
	if modify:
		handler = ModifyFileHandler
	else:
		handler = FileHandler

	#Remove trailing slashes if necessary
	if local.endswith('/'):
		local = local[:-1]
	if remote.endswith('/'):
		remote = remote[:-1]

	handler.local = local
	handler.remote = remote
	handler.dir_index = dir_index

	routes.update({ remote + '(.*)': handler })

if __name__ == "__main__":
	from argparse import ArgumentParser

	parser = ArgumentParser(description='Quickly serve up local files over HTTP')
	parser.add_argument('--no-index', action='store_false', default=True, dest='indexing', help='Disable directory listings')
	parser.add_argument('--allow-modify', action='store_true', default=False, dest='modify', help='Allow file and directory modifications using PUT and DELETE methods')
	parser.add_argument('local_dir', help='Local directory to be served as the root')

	args = parser.parse_args()

	init(args.local_dir, dir_index=args.indexing, modify=args.modify)

	web.init(('', 8080), routes)
	web.start()
