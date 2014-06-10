web.py
======
web.py is a small, threading web server utilizing the built-in Python socketserver. It is designed from the ground up to be well structured and threaded, to conform to HTTP standard, and, most importantly, to allow for easy creation of a RESTful interface.

FAQs
---
### What is REST? ###
REST, short for Representational State Transfer, is an ideology for creating web services that are represented and manipulated by components using HTTP methods and resources. For example, to create simple, RESTful image service one would first focus on the resource `/images`. It would be a collection that when `GET /images` is called, it would return a list of images and metadata using some agreed upon format. To post an image to the service, one could `POST /images` with a body containing the image data and the resource would return the newly created image's resource, `/images/001`. To subsequently retrieve this image, one would need to `GET /images/001`. To modify the image, one would `PUT /images/001` with a body containing the new image data. To remove the image from the service, one would `DELETE /images/001`.

### How is this web server thingy RESTful then? ###
The server itself isn't RESTful and doesn't have to be used in a RESTful fashion, but it makes it easy to do so. To create the above example for an image service, a single class would be created, extending from `web.HTTPHandler`, that would route resources matching the regex `/images(/.*)`. It would define the `do_get`, `do_post`, `do_put`, and `do_delete` methods and use the matched data to respond in a simple `return <code>, <response>` format. If there is a problem anywhere, then the class would simply need to `raise web.HTTPError(<code>, [message])` with the appropriate HTTP code and an optional message. web.py takes care of all of the dirty work of communication, parsing, and error handling.

### What if I just want to use it as a quick, easy Python HTTP server? ###
It works just as well for that, too! Make a class and only implement the `do_get` method with the data you need and `return 200, <data>`.

### Python methods are nice, but what if I also have a set of static files I want to serve up? ###
web.py comes with an extension, file.py, that you simply specify the local directory and the remote resource and add its routes to your list.

### Why reinvent the wheel when there are plenty of projects that do something similar? ###
Partly for the fun of it, but also to create something that can easily be dropped in to a project and does not rely on anything but the standard library.

### Does it support SSL? ###
Why yes it does! It is as simple as dropping in a key and certificate file and referencing them on server creation.

### Can I change the logs to fit in my program? ###
Yes; it supports changing out anything that is compatible with HTTPLog.

Notes
-----
* Do not allow unauthorized people access to an atomic method as they will then have the power to prevent access to that resource for short periods of time. If necessary, this can also be prevented by returning false for this method in get_body. If this solution is not possible or not desired, the effects of the resource locking can be mitigated by setting timeout and keepalive to small values.

Documentation coming soon!
