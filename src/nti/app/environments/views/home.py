from pyramid.view import view_config

from ..models.interfaces import IOnboardingRoot
from .base import BaseTemplateView


@view_config(context=IOnboardingRoot, renderer='../templates/home.pt')
class HomeView(BaseTemplateView):

    def __call__(self):
        return {'username': self.request.authenticated_userid,
                'realname': self.request.session.get('login.realname')}
