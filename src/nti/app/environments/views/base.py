from pyramid import httpexceptions as hexc
from .utils import raise_json_error

from nti.app.environments.auth import is_admin


class BaseView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def _get_param(self, name, params=None, required=True):
        params = self.request.params if params is None else params
        value = params.get(name)
        value = value.strip() if value else None
        if not value and required:
            raise_json_error(hexc.HTTPBadRequest, 'Missing required {}'.format(name))
        return value


class BaseTemplateView(BaseView):

    logged_in = None
    is_admin = None

    def __init__(self, context, request):
        super(BaseTemplateView, self).__init__(context, request)
        if self.request.authenticated_userid:
            self.logged_in = True
            self.is_admin = is_admin(self.request.authenticated_userid)
