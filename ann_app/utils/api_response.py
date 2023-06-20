from .api_code import ApiCode


def gen_api_response(api_code: ApiCode, data: dict = None):
    body = {
        "info": {
            "code": api_code.value
        }, 
        "data": data
    }
    return body, api_code.http_status_code