# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE.txt in the project root for
# license information.
# -------------------------------------------------------------------------

# NOTE: These tests are heavily inspired from the httpx test suite: https://github.com/encode/httpx/tree/master/tests
# Thank you httpx for your wonderful tests!
import io
import pytest
import sys
import collections
from azure.core.rest import HttpRequest

@pytest.fixture
def assert_iterator_body():
    def _comparer(request, final_value):
        content = b"".join([p for p in request.content])
        assert content == final_value
    return _comparer

def test_request_repr():
    request = HttpRequest("GET", "http://example.org")
    assert repr(request) == "<HttpRequest [GET], url: 'http://example.org'>"

def test_no_content():
    request = HttpRequest("GET", "http://example.org")
    assert "Content-Length" not in request.headers

def test_content_length_header():
    request = HttpRequest("POST", "http://example.org", content=b"test 123")
    assert request.headers["Content-Length"] == "8"


def test_iterable_content(assert_iterator_body):
    class Content:
        def __iter__(self):
            yield b"test 123"  # pragma: nocover

    request = HttpRequest("POST", "http://example.org", content=Content())
    assert request.headers == {}
    assert_iterator_body(request, b"test 123")


def test_generator_with_transfer_encoding_header(assert_iterator_body):
    def content():
        yield b"test 123"  # pragma: nocover

    request = HttpRequest("POST", "http://example.org", content=content())
    assert request.headers == {}
    assert_iterator_body(request, b"test 123")


def test_generator_with_content_length_header(assert_iterator_body):
    def content():
        yield b"test 123"  # pragma: nocover

    headers = {"Content-Length": "8"}
    request = HttpRequest(
        "POST", "http://example.org", content=content(), headers=headers
    )
    assert request.headers == {"Content-Length": "8"}
    assert_iterator_body(request, b"test 123")


def test_url_encoded_data():
    request = HttpRequest("POST", "http://example.org", data={"test": "123"})

    assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert request.content == {'test': '123'}  # httpx makes this just b'test=123'. set_formdata_body is still keeping it as a dict


def test_json_encoded_data():
    request = HttpRequest("POST", "http://example.org", json={"test": 123})

    assert request.headers["Content-Type"] == "application/json"
    assert request.content == '{"test": 123}'


def test_headers():
    request = HttpRequest("POST", "http://example.org", json={"test": 123})

    assert request.headers == {
        "Content-Type": "application/json",
        "Content-Length": "13",
    }


def test_ignore_transfer_encoding_header_if_content_length_exists():
    """
    `Transfer-Encoding` should be ignored if `Content-Length` has been set explicitly.
    See https://github.com/encode/httpx/issues/1168
    """

    def streaming_body(data):
        yield data  # pragma: nocover

    data = streaming_body(b"abcd")

    headers = {"Content-Length": "4"}
    request = HttpRequest("POST", "http://example.org", data=data, headers=headers)
    assert "Transfer-Encoding" not in request.headers
    assert request.headers["Content-Length"] == "4"

def test_override_accept_encoding_header():
    headers = {"Accept-Encoding": "identity"}

    request = HttpRequest("GET", "http://example.org", headers=headers)
    assert request.headers["Accept-Encoding"] == "identity"

"""Test request body"""
def test_empty_content():
    request = HttpRequest("GET", "http://example.org")
    assert request.content is None

def test_string_content():
    request = HttpRequest("PUT", "http://example.org", content="Hello, world!")
    assert request.headers == {"Content-Length": "13", "Content-Type": "text/plain"}
    assert request.content == "Hello, world!"

    # Support 'data' for compat with requests.
    request = HttpRequest("PUT", "http://example.org", data="Hello, world!")

    assert request.headers == {"Content-Length": "13", "Content-Type": "text/plain"}
    assert request.content == "Hello, world!"

    # content length should not be set for GET requests

    request = HttpRequest("GET", "http://example.org", data="Hello, world!")

    assert request.headers == {"Content-Length": "13", "Content-Type": "text/plain"}
    assert request.content == "Hello, world!"

@pytest.mark.skipif(sys.version_info < (3, 0),
                    reason="In 2.7, b'' is the same as a string, so will have text/plain content type")
def test_bytes_content():
    request = HttpRequest("PUT", "http://example.org", content=b"Hello, world!")
    assert request.headers == {"Content-Length": "13"}
    assert request.content == b"Hello, world!"

    # Support 'data' for compat with requests.
    request = HttpRequest("PUT", "http://example.org", data=b"Hello, world!")

    assert request.headers == {"Content-Length": "13"}
    assert request.content == b"Hello, world!"

    # should still be set regardless of method

    request = HttpRequest("GET", "http://example.org", data=b"Hello, world!")

    assert request.headers == {"Content-Length": "13"}
    assert request.content == b"Hello, world!"

def test_iterator_content(assert_iterator_body):
    # NOTE: in httpx, content reads out the actual value. Don't do that (yet) in azure rest
    def hello_world():
        yield b"Hello, "
        yield b"world!"

    request = HttpRequest("POST", url="http://example.org", content=hello_world())
    assert isinstance(request.content, collections.Iterable)

    assert_iterator_body(request, b"Hello, world!")
    assert request.headers == {}

    # Support 'data' for compat with requests.
    request = HttpRequest("POST", url="http://example.org", data=hello_world())
    assert isinstance(request.content, collections.Iterable)

    assert_iterator_body(request, b"Hello, world!")
    assert request.headers == {}

    # transfer encoding should still be set for GET requests
    request = HttpRequest("GET", url="http://example.org", data=hello_world())
    assert isinstance(request.content, collections.Iterable)

    assert_iterator_body(request, b"Hello, world!")
    assert request.headers == {}


def test_json_content():
    request = HttpRequest("POST", url="http://example.org", json={"Hello": "world!"})

    assert request.headers == {
        "Content-Length": "19",
        "Content-Type": "application/json",
    }
    assert request.content == '{"Hello": "world!"}'

def test_urlencoded_content():
    # NOTE: not adding content length setting and content testing bc we're not adding content length in the rest code
    # that's dealt with later in the pipeline.
    request = HttpRequest("POST", url="http://example.org", data={"Hello": "world!"})
    assert request.headers == {
        "Content-Type": "application/x-www-form-urlencoded",
    }

@pytest.mark.parametrize(("key"), (1, 2.3, None))
def test_multipart_invalid_key(key):

    data = {key: "abc"}
    files = {"file": io.BytesIO(b"<file content>")}
    with pytest.raises(TypeError) as e:
        HttpRequest(
            url="http://localhost:8000/",
            method="POST",
            data=data,
            files=files,
        )
    assert "Invalid type for data name" in str(e.value)
    assert repr(key) in str(e.value)


@pytest.mark.skipif(sys.version_info < (3, 0),
                    reason="In 2.7, b'' is the same as a string, so check doesn't fail")
def test_multipart_invalid_key_binary_string():

    data = {b"abc": "abc"}
    files = {"file": io.BytesIO(b"<file content>")}
    with pytest.raises(TypeError) as e:
        HttpRequest(
            url="http://localhost:8000/",
            method="POST",
            data=data,
            files=files,
        )
    assert "Invalid type for data name" in str(e.value)
    assert repr(b"abc") in str(e.value)

@pytest.mark.parametrize(("value"), (object(), {"key": "value"}))
def test_multipart_invalid_value(value):

    data = {"text": value}
    files = {"file": io.BytesIO(b"<file content>")}
    with pytest.raises(TypeError) as e:
        HttpRequest("POST", "http://localhost:8000/", data=data, files=files)
    assert "Invalid type for data value" in str(e.value)

def test_empty_request():
    request = HttpRequest("POST", url="http://example.org", data={}, files={})

    assert request.headers == {}
    assert not request.content # in core, we don't convert urlencoded dict to bytes representation in content

def test_read_content(assert_iterator_body):
    def content():
        yield b"test 123"

    request = HttpRequest("POST", "http://example.org", content=content())
    assert_iterator_body(request, b"test 123")
    # in this case, request._data is what we end up passing to the requests transport
    assert isinstance(request._data, collections.Iterable)

def test_complicated_json(client):
    # thanks to Sean Kane for this test!
    input = {
        'EmptyByte': '',
        'EmptyUnicode': '',
        'SpacesOnlyByte': '   ',
        'SpacesOnlyUnicode': '   ',
        'SpacesBeforeByte': '   Text',
        'SpacesBeforeUnicode': '   Text',
        'SpacesAfterByte': 'Text   ',
        'SpacesAfterUnicode': 'Text   ',
        'SpacesBeforeAndAfterByte': '   Text   ',
        'SpacesBeforeAndAfterUnicode': '   Text   ',
        '啊齄丂狛': 'ꀕ',
        'RowKey': 'test2',
        '啊齄丂狛狜': 'hello',
        "singlequote": "a''''b",
        "doublequote": 'a""""b',
        "None": None,
    }
    request = HttpRequest("POST", "/basic/complicated-json", json=input)
    r = client.send_request(request)
    r.raise_for_status()

def test_use_custom_json_encoder():
    # this is to test we're using azure.core.serialization.AzureJSONEncoder
    # to serialize our JSON objects
    # since json can't serialize bytes by default but AzureJSONEncoder can,
    # we pass in bytes and check that they are serialized
    request = HttpRequest("GET", "/headers", json=bytearray("mybytes", "utf-8"))
    assert request.content == '"bXlieXRlcw=="'

# NOTE: For files, we don't allow list of tuples yet, just dict. Will uncomment when we add this capability
# def test_multipart_multiple_files_single_input_content():
#     files = [
#         ("file", io.BytesIO(b"<file content 1>")),
#         ("file", io.BytesIO(b"<file content 2>")),
#     ]
#     request = HttpRequest("POST", url="http://example.org", files=files)
#     assert request.headers == {
#         "Content-Length": "271",
#         "Content-Type": "multipart/form-data; boundary=+++",
#     }
#     assert request.content == b"".join(
#         [
#             b"--+++\r\n",
#             b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
#             b"Content-Type: application/octet-stream\r\n",
#             b"\r\n",
#             b"<file content 1>\r\n",
#             b"--+++\r\n",
#             b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
#             b"Content-Type: application/octet-stream\r\n",
#             b"\r\n",
#             b"<file content 2>\r\n",
#             b"--+++--\r\n",
#         ]
#     )