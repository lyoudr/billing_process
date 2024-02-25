from http import HTTPStatus

class CustomException(Exception):
    def __init__(
            self, 
            code=HTTPStatus.BAD_REQUEST, 
            error_code: int = None, 
            error_msg: str = None
        ):
        self.code = code
        self.error_code = error_code 
        self.error_msg = error_msg 
        super().__init__(self.error_msg)