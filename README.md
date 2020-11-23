fooster-web
===========

fooster-web is a small, process-pooled web server utilizing the built-in Python socketserver. It is designed from the ground up to be well structured, to conform to the HTTP/1.1 standard, and to allow for easy creation of a RESTful interface.

[![Build Status](https://img.shields.io/github/workflow/status/lilyinstarlight/python-fooster-web/Tox)](https://github.com/lilyinstarlight/python-fooster-web/actions?query=workflow%3ATox) [![Coverage Status](https://img.shields.io/codecov/c/github/lilyinstarlight/python-fooster-web)](https://codecov.io/github/lilyinstarlight/python-fooster-web)


Usage
-----

Below is a basic example that stores data via a PUT method and retrieves data via a GET method on any resource. If a resource has not been set, it returns a 404 error.

```python
import fooster.db

import fooster.web


data = fooster.db.Database('data.db', ['path', 'body'])


class Handler(fooster.web.HTTPHandler):
    def do_get(self):
        try:
            return 200, data[self.groups['path']].body
        except KeyError:
            raise fooster.web.HTTPError(404)

    def do_put(self):
        data[self.groups['path']] = data.Entry(self.request.body.decode())

        return 200, 'Accepted\n'

    def do_delete(self):
        try:
            del data[self.groups['path']]
        except KeyError:
            raise fooster.web.HTTPError(404)

        return 200, 'Deleted\n'


routes = {r'/(?P<path>.*)': Handler}


if __name__ == '__main__':
    import signal

    httpd = fooster.web.HTTPServer(('localhost', 8000), routes)

    httpd.start()

    signal.signal(signal.SIGINT, lambda signum, frame: httpd.close())

    httpd.join()
```

Examples and more information are available at the [wiki](https://github.com/lilyinstarlight/python-fooster-web/wiki).
