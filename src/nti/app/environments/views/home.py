from pyramid.view import view_config

from zope import component

from ..models.interfaces import IOnboardingRoot


def is_admin(username):
    return username and username.endswith('@nextthought.com')


@view_config(context=IOnboardingRoot, renderer='../templates/home.pt')
def my_view(context, request):
    return {'username': request.authenticated_userid,
            'logged_in': bool(request.authenticated_userid),
            'is_admin': is_admin(request.authenticated_userid)}
