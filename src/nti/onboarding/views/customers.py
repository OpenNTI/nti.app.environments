import datetime

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from zope import component

from ..models.interfaces import ICustomersContainer

from nti.mailer.interfaces import ITemplatedMailer

from ..authentication import forget
from ..authentication import remember
from ..authentication import setup_challenge_for_customer
from ..authentication import validate_challenge_for_customer
from ..models.customers import PersistentCustomer
    

@view_config(context=ICustomersContainer,
             renderer='json',
             request_method='POST',
             name="challenge_customer")
def challenge_view(context, request):
    email = request.params.get('email')
    name = request.params.get('name')
    
    # forget any user information we may have
    forget(request)

    # Get or create the customer
    # TODO we need to abstract this away, particularily the
    # creation.
    try:
        customer = context[email]
    except KeyError:
        customer = PersistentCustomer()
        customer.email = email
        customer.__name__ = email
        customer.created = datetime.datetime.now()
        context[customer.__name__] = customer

    # Setup the customer object to be challenged
    code = setup_challenge_for_customer(customer)

    url = request.resource_url(context,
                               '@@verify_challenge',
                               query={'email': email,
                                      'name': name,
                                      'code': code})

    # Send the email challenging the user
    resp = {'code_prefix': code[:6],
            'code': code[6:],
            'url': url}
    return resp


@view_defaults(context=ICustomersContainer,
               renderer='json',
               name="verify_challenge")
class ChallengerVerification(object):

    def __init__(self, context, request):
        self.request = request
        self.context = context

    @view_config(request_method='POST')
    def verify_from_form(self):
        return self.do_verify(self.request, self.context)

    @view_config(request_method='GET')
    def verify_from_link(self):
        return self.do_verify(self.request, self.context)
    
    def do_verify(self, request, context):
        email = request.params.get('email')
        name = request.params.get('name')
        code = request.params.get('code')

        # Get the customer
        customer = context[email]

        # This should exist
        if customer is None:
            raise hexc.HTTPBadRequest()

        # Validate code against the challenge
        # This should raise if invalid
        if not validate_challenge_for_customer(customer, code):
            return hexc.HTTPBadRequest('Bad Challenge')

        # remember the user
        remember(request, email)

        if name:
            customer.name = name
            customer.last_verified = datetime.datetime.utcnow()
        
        # See other the user to the create site form
        return hexc.HTTPSeeOther('/foo', headers=request.response.headers)

        
    
