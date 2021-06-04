import os
from typing import Optional, Tuple, Dict
import requests

from . import IDriver, register_driver


@register_driver
class RemoteDriver(IDriver):
    _DRIVER_NAME = 'remote'
    _OPTION_URL = 'URL'
    _OPTION_USERNAME = 'USERNAME'
    _OPTION_PASSWORD = 'PASSWORD'

    def __init__(self,
                 url: str,
                 auth: Optional[Tuple[str, str]] = None):
        self.url = url
        self.auth = auth

    @classmethod
    def name(cls):
        return cls._DRIVER_NAME

    @classmethod
    def from_options(cls, options: Dict[str, str]):
        kwargs = {}
        if cls._OPTION_URL not in options:
            raise Exception(f'Missing "{cls._OPTION_URL}" in remote drivers options')
        kwargs['url'] = options[cls._OPTION_URL]
        # TODO: auth
        # TODO: support username and password from file
        return cls(**kwargs)

    def put_file(self, file_path: str, dest_path: str):
        with open(file_path, 'rb') as f:
            res = requests.put(os.path.join(self.url, dest_path),
                               auth=self.auth, data=f)
        if not res.ok:
            raise Exception('Failed to put "%s" to remote. Reason: %s' % (file_path, res.reason))

    def fetch_file_from_remote(self, file_path) -> bytes:
        res = requests.get(os.path.join(self.url, file_path), auth=self.auth)
        if not res.ok:
            if res.status_code == 404:
                raise FileNotFoundError(file_path)
            raise Exception('Failed to fetch "%s" from remote. Reason: %s' % (file_path, res.reason))
        return res.content
