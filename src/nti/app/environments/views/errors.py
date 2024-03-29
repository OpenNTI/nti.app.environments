from pyramid import httpexceptions as hexc

from pyramid.url import urlencode

from pyramid.view import forbidden_view_config
from pyramid.view import notfound_view_config

from nti.app.environments.views.base import BaseTemplateView

from nti.app.environments.views.interfaces import IEndUserBrowserRequest

SUB_MESSAGES = {
    404: 'It looks like you stumbled on something that does not exist.',
    403: 'It looks like you stumbled on something you do not have access to.',
    401: 'Unauthorized'
}

@notfound_view_config(renderer='../templates/error.pt')
class ErrorView(BaseTemplateView):

    def __call__(self):
        status_code = self.context.status_code
        self.request.response.status = status_code
        return {
            "message": self.context.status,
            "subtext": SUB_MESSAGES.get(status_code, '')
        }


def is_browser_request(request):
    # Simply checking if the request is coming from browser or not.
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return False

    useragent = request.environ.get('HTTP_USER_AGENT', '').lower()
    if 'httpie' in useragent:
        return False

    return True


@forbidden_view_config(renderer='../templates/error.pt')
class ForbiddenView(ErrorView):

    def _build_login_url(self, return_url):
        params = urlencode({'success': return_url})
        return f'/login?{params}'

    def __call__(self):
        if not self.request.authenticated_userid:
            if not is_browser_request(self.request):
                self.context.status_code = 401
                return super(ForbiddenView, self).__call__()

            self.request.response.status_code = self.context.status_code
            success = self.request.path_qs
            location = self._build_login_url(success)
            
            return hexc.HTTPFound(location=location)
        else:
            return super(ForbiddenView, self).__call__()


@forbidden_view_config(renderer='../templates/error.pt',
                       request_type=IEndUserBrowserRequest)
class EndUserForbiddenView(ForbiddenView):
    
    def _build_login_url(self, return_url):
        params = urlencode({'return': return_url})
        return f'/email-auth?{params}'
