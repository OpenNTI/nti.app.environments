from pyramid.view import view_config

from zope import component

from ..models.interfaces import ICustomersContainer

from nti.mailer.interfaces import ITemplatedMailer


@view_config(context=ICustomersContainer,
             renderer='json',
             request_method='POST')
def my_view(context, request):
    email = request.params['email']
    name = request.params['name']
    code = request.params.get('code', None)

    if code is None:
        mailer = component.getUtility(ITemplatedMailer)
    
    return {'email': email, 'sent_email': (code is None)}
