from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from zope import component

from zope.event import notify

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

from nti.app.environments.models.events import CustomerVerifiedEvent

from nti.externalization.interfaces import LocatedExternalDict

from nti.mailer.interfaces import ITemplatedMailer

from .base import BaseView
from .base import getOrCreateCustomer
from .base import createCustomer
from .utils import raise_json_error

logger = __import__('logging').getLogger(__name__)

EMAIL_CHALLENGE_VIEW = 'email_challenge'
EMAIL_CHALLENGE_VERIFY_VIEW = 'email_challenge_verify'
RECOVERY_CHALLENGE_VIEW = 'recovery_challenge'
RECOVERY_CHALLENGE_VERIFY_VIEW = 'recovery_challenge_verify'


@view_config(renderer='rest',
             context=ICustomersContainer,
             request_method='POST',
             name=EMAIL_CHALLENGE_VIEW)
class EmailChallengeView(BaseView):

    _email_template = 'nti.app.environments:email_templates/verify_customer'
    _email_subtitle = 'Thank you for signing up for NextThought!'

    def _mailer(self):
        return component.getUtility(ITemplatedMailer, name='default')

    def _send_mail(self, template, subject, recipients, template_args):
        mailer = self._mailer()
        mailer.queue_simple_html_text_email(template,
                                            subject=subject,
                                            recipients=recipients,
                                            template_args=template_args,
                                            text_template_extension='.mak')

    def _get_or_create_customer(self, params):
        name = self._get_value('name', params, required=True)
        email = self._get_value('email', params, required=True)
        if not checkEmailAddress(email):
            raise_json_error(hexc.HTTPUnprocessableEntity,
                             'Invalid email.')

        organization = self._get_value('organization', params)
        try:
            return getOrCreateCustomer(self.context, email, name, organization)
        except ConstraintNotSatisfied as e:
            raise_json_error(hexc.HTTPBadRequest,
                             'Invalid {}.'.format(e.field.__name__))

    def _do_call(self, params):
        # forget any user information we may have
        forget(self.request)

        customer = self._get_or_create_customer(params)
        if customer is None:
            return None

        # Setup the customer object to be challenged
        code = setup_challenge_for_customer(customer)
        code_prefix = code[:6]
        code_suffix = code[6:].upper()

        template_args = {
            'name': customer.name,
            'email': customer.email,
            'organization': customer.organization,
            'code_suffix': code_suffix,
            'subtitle': self._email_subtitle
        }

        self._send_mail(self._email_template,
                        subject="NextThought Confirmation Code: {}".format(code_suffix),
                        recipients=[customer.email],
                        template_args=template_args)

        return {'name': customer.name,
                'email': customer.email,
                'organization': customer.organization,
                'code_prefix': code_prefix}

    def __call__(self):
        data = self._do_call(self.body_params)
        if data is None:
            return hexc.HTTPNoContent()

        result = LocatedExternalDict()
        result.__name__ = self.context.__name__
        result.__parent__ = self.context.__parent__
        result.update(data)
        return result


@view_config(renderer='rest',
             context=ICustomersContainer,
             request_method='POST',
             name=RECOVERY_CHALLENGE_VIEW)
class RecoveryEmailChallengeView(EmailChallengeView):

    _email_subtitle = 'Welcome back to NextThought!'

    def _get_or_create_customer(self, params):
        email = self._get_value('email', params, required=True)
        if not checkEmailAddress(email):
            raise_json_error(hexc.HTTPUnprocessableEntity,
                             'Invalid email.')

        customer = self.context.getCustomer(email)
        if customer is None:
            logger.info("Notifying user that account doesn't exist: %s.", email)
            self._send_mail('nti.app.environments:email_templates/customer_not_found',
                            subject="Your account is not found: {}".format(email),
                            recipients=[email],
                            template_args={'email': email,
                                           'app_link': self.request.application_url})
        return customer


@view_defaults(renderer='rest',
               context=ICustomersContainer,
               request_method='POST')
@view_config(name=EMAIL_CHALLENGE_VERIFY_VIEW)
@view_config(name=RECOVERY_CHALLENGE_VERIFY_VIEW)
class EmailChallengeVerifyView(BaseView):

    def do_verify(self, params):
        email = self._get_value('email', params, required=True)
        code = self._get_value('code', params, required=True)

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

        notify(CustomerVerifiedEvent(customer))

        # See other the user to the create site form
        return {'email': email,
                'customer': customer}

    def __call__(self):
        data = self.do_verify(self.body_params)

        result = LocatedExternalDict()
        result.__name__ = self.context.__name__
        result.__parent__ = self.context.__parent__
        result.update(data)
        return result


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
