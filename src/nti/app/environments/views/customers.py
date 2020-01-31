import datetime

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from zope import component
from zope.schema._bootstrapinterfaces import ConstraintNotSatisfied

from nti.app.environments.api.hubspotclient import get_hubspot_client

from nti.app.environments.models.interfaces import ICustomer
from nti.app.environments.models.interfaces import ICustomersContainer
from nti.app.environments.models.interfaces import checkEmailAddress

from nti.app.environments.auth import ACT_CREATE
from nti.app.environments.auth import ACT_DELETE
from nti.app.environments.auth import ACT_READ

from nti.app.environments.authentication import forget
from nti.app.environments.authentication import remember
from nti.app.environments.authentication import setup_challenge_for_customer
from nti.app.environments.authentication import validate_challenge_for_customer

from nti.externalization.interfaces import LocatedExternalDict

from nti.mailer.interfaces import ITemplatedMailer

from .base import BaseView
from .base import getOrCreateCustomer
from .base import createCustomer
from .utils import raise_json_error


@view_defaults(context=ICustomersContainer,
               request_method='POST')
class ChallengeView(BaseView):

    def _mailer(self):
        return component.getUtility(ITemplatedMailer, name='default')

    def _do_call(self, params, verify_url=False):
        name = self._get_value('name', params, required=True)
        email = self._get_value('email', params, required=True)
        organization = self._get_value('organization', params)

        # forget any user information we may have
        forget(self.request)

        try:
            customer = getOrCreateCustomer(self.context, email, name)
        except ConstraintNotSatisfied as e:
            raise_json_error(hexc.HTTPBadRequest,
                             'Invalid {}.'.format(e.field.__name__))

        # Setup the customer object to be challenged
        code = setup_challenge_for_customer(customer)
        code_prefix = code[:6]
        code_suffix = code[6:].upper()

        template_args = {
            'name': name,
            'email': email,
            'organization': organization,
            'code_suffix': code_suffix
        }

        if verify_url is True:
            url = self.request.resource_url(self.context,
                                            '@@verify_challenge',
                                            query={'email': email,
                                                   'name': name,
                                                   'organization': organization,
                                                   'code': code})
            template_args['url'] = url

        mailer = self._mailer()
        mailer.queue_simple_html_text_email("nti.app.environments:email_templates/verify_customer",
                                            subject="NextThought Confirmation Code: {}".format(code_suffix),
                                            recipients=[email],
                                            template_args=template_args,
                                            text_template_extension='.mak')
        return {'name': name,
                'email': email,
                'organization': organization,
                'code_prefix': code_prefix}

    @view_config(renderer='json',
                 name="challenge_customer")
    def challenge_customer(self):
        request = self.request
        result = self._do_call(request.params, verify_url=True)

        # redirect to verify page.
        request.session.flash(result['name'], 'name')
        request.session.flash(result['email'], 'email')
        request.session.flash(result['code_prefix'], 'code_prefix')
        location = request.resource_url(self.context, '@@email_challenge_verify')
        return {'redirect_uri': location}

    @view_config(renderer='rest',
             name="email_challenge")
    def email_challenge(self):
        data = self._do_call(self.body_params)

        result = LocatedExternalDict()
        result.__name__ = self.context.__name__
        result.__parent__ = self.context.__parent__
        result.update(data)
        return result


@view_defaults(context=ICustomersContainer,
               renderer='json',
               name="verify_challenge")
class ChallengerVerification(BaseView):

    @view_config(request_method='POST')
    def verify_from_form(self):
        self.do_verify(self.request.params)
        return {'redirect_uri': '/'}

    @view_config(request_method='GET')
    def verify_from_link(self):
        self.do_verify(self.request.params)
        return {'redirect_uri': '/'}

    def do_verify(self, params):
        email = self._get_value('email', params, required=True)
        code = self._get_value('code', params, required=True)
        name = self._get_value('name', params)
        organization = self._get_value('organization', params)

        # Get the customer
        customer = self.context.get(email)

        # This should exist
        if customer is None:
            raise_json_error(hexc.HTTPBadRequest,
                             'Bad request.')

        # Validate code against the challenge
        # This should raise if invalid
        if not validate_challenge_for_customer(customer, code):
            raise raise_json_error(hexc.HTTPBadRequest,
                                   "That code wasn't valid. Give it another go!")

        # remember the user
        remember(self.request, email)

        if name:
            customer.name = name

        if organization:
            customer.organization = organization

        customer.last_verified = datetime.datetime.utcnow()

        # See other the user to the create site form
        return {'email': email,
                'customer': customer}

    @view_config(renderer='rest',
                 request_method='POST',
                 name='email_challenge_verify')
    def email_verify_from_api(self):
        data = self.do_verify(self.body_params)

        result = LocatedExternalDict()
        result.__name__ = self.context.__name__
        result.__parent__ = self.context.__parent__
        result.update(data)
        return result


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


@view_config(renderer='rest',
             request_method='GET',
             context=ICustomersContainer,
             permission=ACT_READ)
class CustomersListView(BaseView):

    def __call__(self):
        return [customer for customer in self.context.values()]


@view_config(renderer='json',
             context=ICustomer,
             request_method='DELETE',
             permission=ACT_DELETE)
def deleteCustomerView(context, request):
    container = context.__parent__
    del container[context.__name__]
    return hexc.HTTPNoContent()


@view_defaults(renderer='json',
               context=ICustomersContainer,
               request_method='POST',
               permission=ACT_CREATE)
class CustomerCreationView(BaseView):

    @property
    def client(self):
        return get_hubspot_client()

    @view_config(name="hubspot")
    def with_hubspot(self):
        email = self._get_param('email')
        if not checkEmailAddress(email):
            raise_json_error(hexc.HTTPUnprocessableEntity,
                             'Invalid email.')

        customer = self.context.getCustomer(email)
        if customer is not None:
            raise_json_error(hexc.HTTPConflict,
                             "Existing customer: {}.".format(email))

        contact = self.client.fetch_contact_by_email(email)
        if not contact:
            raise_json_error(hexc.HTTPUnprocessableEntity,
                             "No hubspot contact found: {}.".format(email))

        if not contact['name']:
            raise_json_error(hexc.HTTPUnprocessableEntity,
                             "Name is missing on hubspot: {}.".format(email))

        customer = createCustomer(self.context,
                                  email=email,
                                  name=contact['name'],
                                  hs_contact_vid=contact['canonical-vid'])
        self.request.response.status = 201
        return {}
