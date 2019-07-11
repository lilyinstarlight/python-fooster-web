from fooster.web import web, form

import mock

import pytest


test_body = b'test'
test_chunks = b'a' * (web.max_line_size + 1)
test_encoded = b'test=t%C3%ABst&foo=bar&wow&such=dog'
test_binary = 'thisisatëst'.encode(web.default_encoding)

test_boundary = 'boundåry'

test_mime_empty = ('--' + test_boundary + '\r\nContent-Disposition: form-data; name="empty"; filename="empty"\r\n\r\n').encode(web.http_encoding)
test_mime_basic = ('--' + test_boundary + '\r\nContent-Disposition: form-data; name="body"\r\n\r\n').encode(web.http_encoding) + test_body
test_mime_bad = ('--' + test_boundary + '\r\nContent-Disposition: form-data; name="body"\r\nContent-Length: ' + str(len(test_body) + 1) + '\r\n\r\n').encode(web.http_encoding) + test_body
test_mime_chunks = ('--' + test_boundary + '\r\nContent-Disposition: form-data; name="body"\r\n\r\n').encode(web.http_encoding) + test_chunks
test_mime_too_long = ('--' + test_boundary + '\r\nContent-Disposition: form-data; name="body"\r\n\r\n').encode(web.http_encoding) + b'a' * (form.max_memory_size + web.max_line_size + 1)
test_mime_length = ('--' + test_boundary + '\r\nContent-Disposition: form-data; name="body"\r\nContent-Length: ' + str(len(test_body)) + '\r\n\r\n').encode(web.http_encoding) + test_body
test_mime_no_disposition = ('--' + test_boundary + '\r\n\r\n').encode(web.http_encoding) + test_body
test_mime_bad_disposition = ('--' + test_boundary + '\r\nContent-Disposition: bad-data; name="body"\r\n\r\n').encode(web.http_encoding) + test_body
test_mime_bad_length = ('--' + test_boundary + '\r\nContent-Disposition: form-data; name="body"\r\nContent-Length: "bad"\r\n\r\n').encode(web.http_encoding) + test_body

test_mime_filename = ('--' + test_boundary + '\r\nContent-Disposition: form-data; name="binary"; filename="binary"\r\nContent-Type: application/octet-stream\r\nContent-Length: ' + str(len(test_binary)) + '\r\n\r\n').encode(web.http_encoding) + test_binary
test_mime_filename_bad = ('--' + test_boundary + '\r\nContent-Disposition: form-data; name="binary_attached"; filename="binary"\r\nContent-Type: application/octet-stream\r\nContent-Length: ' + str(len(test_binary) + 1) + '\r\n\r\n').encode(web.http_encoding) + test_binary
test_mime_filename_bad_type = ('--' + test_boundary + '\r\nContent-Disposition: form-data; name="binary"; filename="binary"\r\nContent-Type: ;\r\nContent-Length: ' + str(len(test_binary)) + '\r\n\r\n').encode(web.http_encoding) + test_binary
test_mime_filename_no_length = ('--' + test_boundary + '\r\nContent-Disposition: form-data; name="binary"; filename="binary"\r\nContent-Type: application/octet-stream\r\n\r\n').encode(web.http_encoding) + test_binary
test_mime_filename_too_long = ('--' + test_boundary + '\r\nContent-Disposition: form-data; name="binary"; filename="binary"\r\nContent-Type: application/octet-stream\r\n\r\n').encode(web.http_encoding) + b'a' * (form.max_file_size + web.max_line_size + 1)

test_mime_utf8 = ('--' + test_boundary + '\r\nContent-Disposition: form-data; name="binary_utf8"\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n').encode(web.http_encoding) + test_binary

test_mime_extra = ('--' + test_boundary + '\r\nContent-Disposition: form-data; name="binary_utf8"\r\nContent-Type: text/plain; charset=utf-8\r\nMIME-Version: 1.0\r\nHeader: Value\r\n\r\n').encode(web.http_encoding) + test_binary

test_separator = '\r\n'.encode(web.http_encoding)
test_end = ('--' + test_boundary + '--\r\n').encode(web.http_encoding)


class EchoHandler(form.FormHandler):
    def do_get(self):
        return 204, ''

    def do_post(self):
        return 200, self.request.body


def test_form_get():
    request = mock.MockHTTPRequest(None, ('', 0), None, method='GET', handler=EchoHandler)

    response = request.handler.respond()

    assert response[0] == 204
    assert response[1] == ''


def test_form_post():
    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_body, method='POST', handler=EchoHandler)

    response = request.handler.respond()

    assert request.body == test_body

    assert response[0] == 200
    assert response[1] == test_body


def test_form_urlencoded():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'application/x-www-form-urlencoded')

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_encoded, headers=request_headers, method='POST', handler=EchoHandler)

    request.handler.respond()

    assert request.body['test'] == 'tëst'
    assert request.body['foo'] == 'bar'
    assert request.body['wow'] == ''
    assert request.body['such'] == 'dog'


def test_form_urlencoded_bad():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'application/x-www-form-urlencoded')

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_encoded + 'å'.encode(web.default_encoding), headers=request_headers, method='POST', handler=EchoHandler)

    request.handler.respond()

    assert request.body['test'] == 'tëst'
    assert request.body['foo'] == 'bar'
    assert request.body['wow'] == ''
    assert request.body['such'] == 'dogå'


def test_form_multipart_basic():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_basic + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    request.handler.respond()

    assert request.body['body'] == test_body.decode()


def test_form_multipart_bad():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_bad + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    with pytest.raises(web.HTTPError) as error:
        request.handler.respond()

    assert error.value.code == 400


def test_form_multipart_chunks():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_chunks + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    request.handler.respond()

    assert request.body['body'] == test_chunks.decode()


def test_form_multipart_basic_too_long():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_too_long + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    with pytest.raises(web.HTTPError) as error:
        request.handler.respond()

    assert error.value.code == 413


def test_form_multipart_basic_length():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_length + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    request.handler.respond()

    assert request.body['body'] == test_body.decode()


def test_form_multipart_expect():
    request_headers = web.HTTPHeaders()
    request_headers.set('Expect', '100-continue')
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_basic + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    request.handler.respond()

    assert request.body['body'] == test_body.decode()


def test_form_multipart_bad_mime():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Length', str(len(test_mime_basic + test_separator + test_end) + 1))
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_basic + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    with pytest.raises(web.HTTPError) as error:
        request.handler.respond()

    assert error.value.code == 400


def test_form_multipart_bad_mime_length():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Length', '"bad"')
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_basic + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    with pytest.raises(web.HTTPError) as error:
        request.handler.respond()

    assert error.value.code == 400


def test_form_multipart_too_long():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Length', str(form.max_multipart_fragments * form.max_file_size + 1))
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_basic + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    with pytest.raises(web.HTTPError) as error:
        request.handler.respond()

    assert error.value.code == 413


def test_form_multipart_bad_boundary():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'multipart/form-data; boundary=a' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_basic + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    with pytest.raises(web.HTTPError) as error:
        request.handler.respond()

    assert error.value.code == 400


def test_form_multipart_too_many():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=(test_mime_basic + test_separator) * (form.max_multipart_fragments + 1) + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    with pytest.raises(web.HTTPError) as error:
        request.handler.respond()

    assert error.value.code == 413


def test_form_multipart_no_disposition():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_no_disposition + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    with pytest.raises(web.HTTPError) as error:
        request.handler.respond()

    assert error.value.code == 400


def test_form_multipart_bad_disposition():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_bad_disposition + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    with pytest.raises(web.HTTPError) as error:
        request.handler.respond()

    assert error.value.code == 400


def test_form_multipart_bad_length():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_bad_length + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    with pytest.raises(web.HTTPError) as error:
        request.handler.respond()

    assert error.value.code == 400


def test_form_multipart_bad_read():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_empty, headers=request_headers, method='POST', handler=EchoHandler)

    with pytest.raises(web.HTTPError) as error:
        request.handler.respond()

    assert error.value.code == 500


def test_form_multipart_filename():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_filename + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    request.handler.respond()

    assert request.body['binary']['filename'] == 'binary'
    assert request.body['binary']['type'] == 'application/octet-stream'
    assert request.body['binary']['length'] == len(test_binary)
    assert request.body['binary']['file'].read() == test_binary


def test_form_multipart_filename_no_length():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_filename_no_length + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    request.handler.respond()

    assert request.body['binary']['filename'] == 'binary'
    assert request.body['binary']['type'] == 'application/octet-stream'
    assert request.body['binary']['length'] == len(test_binary)
    assert request.body['binary']['file'].read() == test_binary


def test_form_multipart_filename_too_long():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_filename_too_long + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    with pytest.raises(web.HTTPError) as error:
        request.handler.respond()

    assert error.value.code == 413


def test_form_multipart_filename_bad():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_filename_bad + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    with pytest.raises(web.HTTPError) as error:
        request.handler.respond()

    assert error.value.code == 400


def test_form_multipart_filename_bad_type():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_filename_bad_type + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    request.handler.respond()

    assert request.body['binary']['filename'] == 'binary'
    assert request.body['binary']['type'] == 'text/plain'
    assert request.body['binary']['length'] == len(test_binary)
    assert request.body['binary']['file'].read() == test_binary


def test_form_multipart_utf8():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_utf8 + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    request.handler.respond()

    assert request.body['binary_utf8'] == test_binary.decode()


def test_form_multipart_extra():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_extra + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    request.handler.respond()

    assert request.body['binary_utf8'] == test_binary.decode()


def test_form_multipart_multi():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Type', 'multipart/form-data; boundary=' + test_boundary)

    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_mime_basic + test_separator + test_mime_filename + test_separator + test_mime_utf8 + test_separator + test_end, headers=request_headers, method='POST', handler=EchoHandler)

    request.handler.respond()

    assert request.body['body'] == test_body.decode()

    assert request.body['binary']['filename'] == 'binary'
    assert request.body['binary']['type'] == 'application/octet-stream'
    assert request.body['binary']['length'] == len(test_binary)
    assert request.body['binary']['file'].read() == test_binary

    assert request.body['binary_utf8'] == test_binary.decode()
