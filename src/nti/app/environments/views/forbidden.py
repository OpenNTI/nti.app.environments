from pyramid import httpexceptions as hexc

from pyramid.view import forbidden_view_config

from nti.app.environments.views.base import BaseTemplateView


@forbidden_view_config(renderer='../templates/forbidden.pt')
class ForbiddenView(BaseTemplateView):

    def __call__(self):
        if not self.request.authenticated_userid:
            self.request.response.status_code = 401
            success = self.request.url.split(self.request.application_url)[1]
            return hexc.HTTPFound(location='/login?success={}'.format(success))
        else:
            self.request.response.status_code = 403
            return {"message": '403 forbidden.'}
