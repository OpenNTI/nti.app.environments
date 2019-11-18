from pyramid.view import view_config

from zope import component

from ..models.interfaces import IOnboardingRoot


@view_config(context=IOnboardingRoot, renderer='../templates/mytemplate.pt')
def my_view(context, request):
    return {'project': 'NTI Onboarding'}
