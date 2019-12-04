from pyramid import httpexceptions as hexc
from .utils import raise_json_error


class BaseView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def _get_param(self, name, params=None, required=True):
        params = self.request.params if params is None else params
        value = params.get(name)
        value = value.strip() if value else None
        if not value and required:
            raise_json_error(hexc.HTTPBadRequest, 'Bad request')
        return value
