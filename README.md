fooster-web
===========

fooster-web is a small, process-pooled web server utilizing the built-in Python socketserver. It is designed from the ground up to be well structured, to conform to the HTTP/1.1 standard, and to allow for easy creation of a RESTful interface.

[![Build Status](http://img.shields.io/travis/fkmclane/python-fooster-web.svg)](https://travis-ci.org/fkmclane/python-fooster-web) [![Coverage Status](https://img.shields.io/codecov/c/github/fkmclane/python-fooster-web.svg)](https://codecov.io/github/fkmclane/python-fooster-web)


Usage
-----

Below is a basic example that stores data via a PUT method and retrieves data via a GET method on any resource. If a resource has not been set, it returns a 404 error.

```python
import multiprocessing

import fooster.web


sync = multiprocessing.Manager()
saved = sync.dict()


class Handler(fooster.web.HTTPHandler):
	def do_get(self):
		try:
			return 200, saved[self.groups['path']]
		except KeyError:
			raise fooster.web.HTTPError(404)

	def do_put(self):
		saved[self.groups['path']] = self.request.body

		return 200, 'Accepted'

	def do_delete(self):
		try:
			del saved[self.groups['path']]
		except KeyError:
			raise fooster.web.HTTPError(404)

		return 200, 'Deleted'


routes = { r'/(?P<path>.*)': Handler }

httpd = fooster.web.HTTPServer(('localhost', 8000), routes, sync=sync)
httpd.start()

httpd.join()
```

Examples and more information are available at the [wiki](https://github.com/fkmclane/python-fooster-web/wiki).
