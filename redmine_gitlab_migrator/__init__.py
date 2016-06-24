import logging

import requests

log = logging.getLogger(__name__)


class APIClient:
    def __init__(self, api_key):
        self.api_key = api_key

    def get_auth_headers(self):
        """ Method to be overloaded by child classes

        :return: a dict with auth headers set
        """
        return {}

    def add_auth_headers(self, kwargs):
        _kwargs = kwargs.copy()
        headers = kwargs.get('headers', {})
        headers.update(self.get_auth_headers())
        _kwargs['headers'] = headers
        return _kwargs

    def _req(self, func, *args, **kwargs):
        log.debug('HTTP REQUEST {} {} {}'.format(
            func, args, kwargs))
        kwargs = self.add_auth_headers(kwargs)
        resp = func(*args, **kwargs)
        resp.raise_for_status()
        return resp

    def _req_json(self, func, *args, **kwargs):
        resp = self._req(func, *args, **kwargs)
        ret = resp.json()
        log.debug('HTTP RESPONSE {}'.format(ret))
        return ret
 
    def get(self, *args, **kwargs):
        return self._req_json(requests.get, *args, **kwargs)

    def post(self, *args, **kwargs):
        return self._req_json(requests.post, *args, **kwargs)

    def put(self, *args, **kwargs):
        return self._req_json(requests.put, *args, **kwargs)

    def get_paginated(self, *args, **kwargs):
        resp = self._req(requests.get, *args, **kwargs)
        content = resp.json()
 
        log.debug('HTTP RESPONSE {}'.format(content))

        link_next = None
        link_prev = None
 
        if "next" in resp.links:
            link_next = resp.links["next"]["url"]

        if "prev" in resp.links:
            link_prev = resp.links["prev"]["url"]
 
        return [content, link_next, link_prev]


class Project:
    def __init__(self, url, client):
        self.public_url = url.strip('/')  # normalize URL
        self.api = client

        self._url_match = self.REGEX_PROJECT_URL.match(self.public_url)
        if self._url_match is None:
            raise ValueError(
                '{} is not a valid project URL'.format(url))
