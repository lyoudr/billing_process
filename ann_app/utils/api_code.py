from enum import Enum
from http import HTTPStatus


class ApiCode(Enum):
    SUCCESS = (
        HTTPStatus.OK
    )

    def __init__(self, http_status_code):
        self._http_status_code_ = http_status_code

    def __str__(self):
        return str(self.value)

    @property
    def http_status_code(self):
        return self._http_status_code_