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

def check_expected_response():
    global expected_responses, unexpected_requests
    if expected_responses:
        print(f"There are unconsumed responses: {expected_responses}")
    if unexpected_requests:
        print(f"There are unexpected requests: {unexpected_requests}")
    try:
        assert not expected_responses and not unexpected_requests
    finally:
        clear_expected_response()

def determine_response(url, method, kwargs):
    if DO_NOT_SIMULATE:
        func = {'get': requests.get, 'post': requests.post, 'delete': requests.delete, 'put': requests.put}[method.lower()]
        r = func(server_base+url, json=kwargs)
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
    return response

def get(url, mode='text', oncomplete=None, blocking=False, **kwargs):
    response = determine_response(url, 'get', kwargs)
    if oncomplete:
        oncomplete(response)
    return response

def post(url, mode='text', oncomplete=None, blocking=False, data=None, **kwargs):
    if data and isinstance(data, str):
        data = json.loads(data)
    response = determine_response(url, 'post', data)
    if oncomplete:
        oncomplete(response)
    return response
def put(url, mode='text', oncomplete=None, blocking=False, data=None, **kwargs):
    response = determine_response(url, 'put', **data)
    if oncomplete:
        oncomplete(response)
    return response
def delete(url, mode='text', oncomplete=None, blocking=False, **kwargs):
    response = determine_response(url, 'delete', kwargs)
    if oncomplete:
        oncomplete(response)
    return response

def add_expected_response(url, method, response: Optional[Response]=None, get_response: Optional[Callable]=None,
                          reuse=False, check_request: Optional[Callable]=None, expect_values=None):
    if expect_values:
        def check_func(url, method, kwargs):
            #data = json.loads(kwargs['data'])
            data = kwargs
            for k, v in expect_values.items():
                assert data.get(k, None) == v, f"Expected {v} for key {k}, got {kwargs.get(k, None)}"
        check_request = check_func

    expected_responses.append(ExpectedResponse(url, method, get_response, check_request, response, reuse))


def remove_expected_reponse(url: str, method: str):
    index = None
    for i, r in enumerate(expected_responses):
        if r.url == url and r.method.lower() == method.lower():
            index = i
            break
    if index is not None:
        expected_responses.pop(index)
