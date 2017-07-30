web.py
======
web.py is a small, process-pooled web server utilizing the built-in Python socketserver. It is designed from the ground up to be well structured, to conform to the HTTP/1.1 standard, and to allow for easy creation of a RESTful interface.

[![Build Status](http://img.shields.io/travis/fkmclane/web.py.svg)](https://travis-ci.org/fkmclane/web.py) [![Coverage Status](https://img.shields.io/coveralls/fkmclane/web.py.svg)](https://coveralls.io/r/fkmclane/web.py)


Usage
-----
Below is a basic example that stores data via a PUT method and retreives data via a GET method on any resource. If a resource has not been set, it returns a 404 error.

```python
import multiprocessing

import web


sync = multiprocessing.Manager()
saved = sync.dict()


class Handler(web.HTTPHandler):
	def do_get(self):
		try:
			return 200, saved[self.groups[0]]
		except KeyError:
			raise web.HTTPError(404)

	def do_put(self):
		saved[self.groups[0]] = self.request.body

		return 200, 'Accepted'

	def do_delete(self):
		try:
			del saved[self.groups[0]]
		except KeyError:
			raise web.HTTPError(404)

		return 200, 'Deleted'


routes = { '/(.*)': Handler }

httpd = web.HTTPServer(('localhost', 8080), routes, sync=sync)
httpd.start()

httpd.join()
```

Examples and more information are available at the [wiki](https://github.com/fkmclane/web.py/wiki).


FAQs
---
### What is REST? ###
REST, short for Representational State Transfer, is an ideology for creating web services made up of stateless requests represented and manipulated by HTTP methods and resources. It allows for scalable APIs that are consistent with no side effects for the client. A more complete description is available at the [REST API Tutorial](http://www.restapitutorial.com/lessons/whatisrest.html).

### How is this web server RESTful then? ###
The server itself isn't RESTful and doesn't have to be used in a RESTful fashion, but it makes it easy to do so. HTTP resources (represented by regular expressions) are implemented as Python objects which have `do_<method>` methods that correspond to HTTP methods on the resource. The server automatically handles ordering and concurrent requests and supports output of status code and one of strings, bytes, or I/O streams. Additionally, it will soon have extensions that automatically convert Python objects to JSON and add an authentication layer among other things.

### Python methods are nice, but what if I also have a set of static files I want to serve up? ###
web.py comes with an extension, file.py, that allows one to serve a local directory at a specified remote resource.

### Does it support SSL? ###
Why yes it does! It is as simple as dropping in a key and certificate file and referencing them on server creation.

### What if I don't care about REST and just want a quick, easy Python HTTP server? ###
It is possible by only implementing the `do_get` method of static resources, however, I would recommend using [CherryPy](http://www.cherrypy.org/) instead.

### Why reinvent the wheel when there are plenty of projects that do something similar? ###
Partly for the fun of it, but also to create something that can easily be dropped in to a project and does not rely on anything but the standard library.
