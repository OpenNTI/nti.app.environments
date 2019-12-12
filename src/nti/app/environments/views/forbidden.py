from pyramid.view import forbidden_view_config
from .base import BaseTemplateView


@forbidden_view_config(renderer='../templates/forbidden.pt')
class ForbiddenView(BaseTemplateView):

    def __call__(self):
        if not self.request.authenticated_userid:
            self.request.response.status_code = 401
            return {"message": "401 unauthorized."}
        else:
            self.request.response.status_code = 403
            return {"message": '403 forbidden.'}
