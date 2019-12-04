import datetime

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from zope import component
from zope.schema._bootstrapinterfaces import ConstraintNotSatisfied

from ..models.interfaces import ICustomersContainer

from nti.mailer.interfaces import ITemplatedMailer

from ..authentication import forget
from ..authentication import remember
from ..authentication import setup_challenge_for_customer
from ..authentication import validate_challenge_for_customer
from ..models.customers import PersistentCustomer

from .base import BaseView
from .utils import raise_json_error

import nti.app.environments as app_pkg


def getOrCreateCustomer(container, email):
    try:
        customer = container[email]
    except KeyError:
        customer = PersistentCustomer()
        customer.email = email
        customer.__name__ = email
        customer.created = datetime.datetime.now()
        container[customer.__name__] = customer
    return customer


@view_config(context=ICustomersContainer,
             renderer='json',
             request_method='POST',
             name="challenge_customer")
class ChallengeView(BaseView):

    def __call__(self):
        request = self.request
        params = request.params
        email = self._get_param('email', params)
        name = self._get_param('name', params)

        # forget any user information we may have
        forget(request)

        try:
            customer = getOrCreateCustomer(self.context, email)
        except ConstraintNotSatisfied as e:
            raise_json_error(hexc.HTTPBadRequest, 'Invalid {}'.format(e.field.__name__))

        # Setup the customer object to be challenged
        code = setup_challenge_for_customer(customer)
        url = request.resource_url(self.context,
                                   '@@verify_challenge',
                                   query={'email': email,
                                          'name': name,
                                          'code': code})

        code_prefix = code[:6]
        code = "{} - {}".format(code[6:9], code[9:]).upper()

        # Send the email challenging the user
        template_args = {
            'name': name,
            'code': code,
            'url': url
        }
        mailer = component.getUtility(ITemplatedMailer, name='default')
        mailer.queue_simple_html_text_email("nti.app.environments:email_templates/verify_customer",
                                            subject="NextThought verification code: {}".format(code),
                                            recipients=[email],
                                            template_args=template_args,
                                            text_template_extension='.mak')

        # redirect to verify page.
        request.session.flash(name, 'name')
        request.session.flash(email, 'email')
        request.session.flash(code_prefix, 'code_prefix')
        location = request.resource_url(self.context, '@@email_challenge_verify')
        return {'redirect_uri': location}


@view_defaults(context=ICustomersContainer,
               renderer='json',
               name="verify_challenge")
class ChallengerVerification(BaseView):

    @view_config(request_method='POST')
    def verify_from_form(self):
        return self.do_verify(self.request, self.context)

    @view_config(request_method='GET')
    def verify_from_link(self):
        return self.do_verify(self.request, self.context)

    def do_verify(self, request, context):
        params = request.params
        email = self._get_param('email', params)
        code = self._get_param('code', params)
        name = self._get_param('name', params, False)

        # Get the customer
        customer = context.get(email)

        # This should exist
        if customer is None:
            raise_json_error(hexc.HTTPBadRequest,
                             'Bad request')

        # Validate code against the challenge
        # This should raise if invalid
        if not validate_challenge_for_customer(customer, code):
            raise raise_json_error(hexc.HTTPBadRequest,
                                   "That code wasn't valid. Give it another go!")

        # remember the user
        remember(request, email)

        if name:
            customer.name = name
            customer.last_verified = datetime.datetime.utcnow()

        # See other the user to the create site form
        return {'redirect_uri': '/'}


@view_config(context=ICustomersContainer,
             renderer='../templates/email_challenge.pt',
             request_method='GET',
             name="email_challenge")
class EmailChallengeView(BaseView):

    def __call__(self):
        url = self.request.resource_url(self.context,
                                        '@@challenge_customer')
        return {'url': url}


@view_config(context=ICustomersContainer,
             renderer='../templates/email_challenge_verify.pt',
             request_method='GET',
             name="email_challenge_verify")
class EmailChallengeVerifyView(BaseView):

    def _get_flash_value(self, name):
        value = self.request.session.pop_flash(name)
        return value[0] if value else None

    def __call__(self):
        name = self._get_flash_value('name')
        email = self._get_flash_value('email')
        code_prefix = self._get_flash_value('code_prefix')
        if not name or not email or not code_prefix:
            raise hexc.HTTPFound(location=self.request.resource_url(self.context, '@@email_challenge'))

        url = self.request.resource_url(self.context, '@@verify_challenge')
        return {'name': name,
                'email': email,
                'code_prefix': code_prefix,
                'url': url}
