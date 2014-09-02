web.py
======
web.py is a small, thread-pooled web server utilizing the built-in Python socketserver. It is designed from the ground up to be well structured, to conform to the HTTP/1.1 standard, and to allow for easy creation of a RESTful interface.

[![Build Status](http://img.shields.io/travis/fkmclane/web.py.svg)](https://travis-ci.org/fkmclane/web.py) [![Coverage Status](https://img.shields.io/coveralls/fkmclane/web.py.svg)](https://coveralls.io/r/fkmclane/web.py)

Usage
-----
Below is a basic example that stores data via a PUT method and retreives data via a GET method on any resource. If a resource has not been set, it returns a 404 error.

```python
import web

saved = {}

class Handler(web.HTTPHandler):
	def do_get(self):
		body = saved.get(self.groups[0])

		if not body:
			raise web.HTTPError(404)

		return 200, body

	def do_put(self):
		saved[self.groups[0]] = self.request.body

		return 201, 'Created'

routes = { '/(.*)': Handler }

httpd = web.HTTPServer(('localhost', 8080), routes)
httpd.start()
```

Examples and more information are available at the [wiki](https://github.com/fkmclane/web.py/wiki).

FAQs
---
### What is REST? ###
REST, short for Representational State Transfer, is an ideology for creating web services that are represented and manipulated by HTTP methods and resources. For example, to create simple, RESTful image service one would first focus on the resource `/images`. It would be a collection that, when `GET /images` is called, would return a list of images and metadata using some agreed upon format. To post an image to the service, one could `POST /images` with a body containing the image data and the request would return the newly created image's resource, `/images/001`. To subsequently retrieve this image, one would need to `GET /images/001`. To modify the image, one would `PUT /images/001` with a body containing the new image data. To remove the image from the service, one would `DELETE /images/001`.

### How is this web server thingy RESTful then? ###
The server itself isn't RESTful and doesn't have to be used in a RESTful fashion, but it makes it easy to do so. To create the above example for an image service, a single class would be created, extending from `web.HTTPHandler`, that would route resources matching the regex `/images(/.*)`. It would define the `do_get`, `do_post`, `do_put`, and `do_delete` methods and use the matched data to respond in a simple `return <code>, <response>` format. If there is a problem anywhere, then the class would simply need to `raise web.HTTPError(<code>, [message])` with the appropriate HTTP code and an optional message. web.py takes care of all of the dirty work of communication, parsing, and error handling.

### Python methods are nice, but what if I also have a set of static files I want to serve up? ###
web.py comes with an extension, file.py, that allows one to serve a local directory at a specified remote resource.

### Does it support SSL? ###
Why yes it does! It is as simple as dropping in a key and certificate file and referencing them on server creation.

### Can I change the logging to fit my program? ###
web.py supports anything that is compatible with HTTPLog.

### What if I don't care about REST and just want a quick, easy Python HTTP server? ###
It is possible by only implementing the `do_get` method, however, I would recommend using [CherryPy](http://www.cherrypy.org/) instead.

### Why reinvent the wheel when there are plenty of projects that do something similar? ###
Partly for the fun of it, but also to create something that can easily be dropped in to a project and does not rely on anything but the standard library.
