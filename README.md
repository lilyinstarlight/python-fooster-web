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
			del saved[self.groups[0]]
		except KeyError:
			raise fooster.web.HTTPError(404)

		return 200, 'Deleted'


routes = { '/(?P<path>.*)': Handler }

httpd = fooster.web.HTTPServer(('localhost', 8080), routes, sync=sync)
httpd.start()

httpd.join()
```

Examples and more information are available at the [wiki](https://github.com/fkmclane/python-fooster-web/wiki).


FAQs
---
### What is REST? ###
REST, short for Representational State Transfer, is an ideology for creating web services made up of stateless requests represented and manipulated by HTTP methods and resources. It allows for scalable APIs that are consistent with no side effects for the client. A more complete description is available at the [REST API Tutorial](http://www.restapitutorial.com/lessons/whatisrest.html).

### How is this web server RESTful then? ###
The server itself isn't RESTful and doesn't have to be used in a RESTful fashion, but it makes it easy to do so. HTTP resources (represented by regular expressions) are implemented as Python objects which have `do_<method>` methods that correspond to HTTP methods on the resource. The server automatically handles ordering and concurrent requests and supports output of status code and one of strings, bytes, or I/O streams. It has extensions for automatic JSON input/output, authentication, and query and form parsing. It will soon have other goodies such as API discovery with HATEOAS, PATCH transactions, and resource update queueing. Stretch goals are currently to support DAV and do some rigorous production testing.

### Python methods are nice, but what if I also have a set of static files I want to serve up? ###
fooster-web comes with an extension, file.py, that allows one to serve a local directory at a specified remote resource.

### Does it support TLS? ###
Why yes it does! It is as simple as dropping in a key and certificate file and referencing them on server creation.

### What if I don't care about REST and just want a quick, easy Python HTTP server? ###
I would recommend using [CherryPy](http://www.cherrypy.org/) instead.

### Why reinvent the wheel when there are plenty of projects that do something similar? ###
For the fun of it. If you want something reliable, featureful, and not a personal research project use [CherryPy](http://www.cherrypy.org/).
