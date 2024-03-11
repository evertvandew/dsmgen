""" Stub for the Brython ajax module """

from dataclasses import dataclass
from typing import Callable, Optional, Any, List
from xml.etree import ElementTree
import requests
import json

DO_NOT_SIMULATE = False
server_base = ''


class rest_call:
    def __exec__(self, *args, **kwargs):
        pass


@dataclass
class Response:
    status: int
    text: Optional[str] = None
    json: Optional[Any] = None
    xml: Optional[Any] = None
    read: Optional[Callable] = None

@dataclass
class ExpectedResponse:
    url: str
    method: str
    get_response: Optional[Callable] = None # A function to be called to check the request & determine the response
    check_request: Optional[Callable] = None # A function that is called to check the request. No return value expected.
    response: Optional[Response] = None
    reuse: bool = False                # If True, the response will always be the same.

expected_responses: List[ExpectedResponse] = []
unexpected_requests: List[ExpectedResponse] = []


def clear_expected_response():
    global expected_responses, unexpected_requests
    expected_responses = []
    unexpected_requests = []

def determine_response(url, method, kwargs):
    if DO_NOT_SIMULATE:
        func = {'get': requests.get, 'post': requests.post, 'delete': requests.delete, 'put': requests.put}[method.lower()]
        r = func(server_base+url, data=kwargs)
        response = Response(r.status_code, r.text)
        if r.status_code < 300:
            response.json = r.json()
    else:
        index = None
        for i, r in enumerate(expected_responses):
            if r.url == url and r.method == method:
                index = i
                break
        if index is None:
            response = Response(408)  # Timeout return code
            unexpected_requests.append(ExpectedResponse(url=url, method=method, response=Response(408, kwargs)))
        else:
            expected = expected_responses[index]
            if expected.check_request:
                expected.check_request(url, method, kwargs)
            if not expected.reuse:
                expected_responses.pop(index)
            if expected.get_response:
                response = expected.get_response(url, method, kwargs)
            else:
                response = expected.response
    if cb := kwargs.get('oncomplete'):
        cb(response)

def get(url, **kwargs):
    return determine_response(url, 'get', kwargs)
def post(url, **kwargs):
    return determine_response(url, 'post', kwargs)

def put(url, **kwargs):
    return determine_response(url, 'put', kwargs)

def delete(url, **kwargs):
    return determine_response(url, 'delete', kwargs)


def add_expected_response(url, method, response: Optional[Response]=None, get_response: Optional[Callable]=None,
                          reuse=False, check_request: Optional[Callable]=None):
    expected_responses.append(ExpectedResponse(url, method, get_response, check_request, response, reuse))


def remove_expected_reponse(url: str, method: str):
    index = None
    for i, r in enumerate(expected_responses):
        if r.url == url and r.method.lower() == method.lower():
            index = i
            break
    if index is not None:
        expected_responses.pop(index)
