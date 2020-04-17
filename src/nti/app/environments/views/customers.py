from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from six.moves import urllib_parse

from urllib.parse import urljoin

from zope import component

from zope.event import notify

from zope.container.interfaces import InvalidItemType

from zope.schema._bootstrapinterfaces import ConstraintNotSatisfied

from nti.app.environments.models.interfaces import ICustomer
from nti.app.environments.models.interfaces import ICustomersContainer
from nti.app.environments.models.interfaces import checkEmailAddress

from nti.app.environments.auth import ACT_CREATE
from nti.app.environments.auth import ACT_DELETE
from nti.app.environments.auth import ACT_READ

from nti.app.environments.authentication import forget, validate_auth_token
from nti.app.environments.authentication import remember
from nti.app.environments.authentication import setup_challenge_for_customer
from nti.app.environments.authentication import validate_challenge_for_customer

from nti.app.environments.models.events import CustomerVerifiedEvent

from nti.app.environments.views import AUTH_TOKEN_VIEW

from nti.externalization.interfaces import LocatedExternalDict

from nti.mailer.interfaces import ITemplatedMailer

from .base import BaseView
from .base import getOrCreateCustomer
from .base import createCustomer
from .base import ObjectCreateUpdateViewMixin
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

    def _email_subject(self, code_suffix):
        return "NextThought Confirmation Code: {}".format(code_suffix)

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
        phone = self._get_value('phone', params, required=True)
        if not checkEmailAddress(email):
            raise_json_error(hexc.HTTPUnprocessableEntity,
                             'Invalid email.')

        organization = self._get_value('organization', params)
        try:
            return getOrCreateCustomer(self.context,
                                       email=email,
                                       name=name,
                                       phone=phone,
                                       organization=organization)
        except ConstraintNotSatisfied as e:
            raise_json_error(hexc.HTTPBadRequest,
                             'Invalid {}.'.format(e.field.__name__))

    def _do_call(self, params, _generate_verify_url=None):
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
            'code_suffix': code_suffix
        }

        if _generate_verify_url:
            template_args['verify_url'] = _generate_verify_url(customer.email, code)

        self._send_mail(self._email_template,
                        subject=self._email_subject(code_suffix),
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

    _email_template = 'nti.app.environments:email_templates/verify_recovery'

    def _email_subject(self, code_suffix):
        return 'Welcome back to NextThought!'

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

    def _generate_verify_url(self, email, code):
        return self.request.resource_url(self.context,
                                         '@@' + RECOVERY_CHALLENGE_VERIFY_VIEW,
                                         query={'email': email,
                                                'code': code})

    def __call__(self):
        self._do_call(self.body_params, _generate_verify_url=self._generate_verify_url)
        return hexc.HTTPNoContent()


class RecoveryChallengeFailed(ValueError):
    pass


@view_defaults(renderer='rest',
               context=ICustomersContainer)
class EmailChallengeVerifyView(BaseView):

    def do_verify(self, params):
        email = self._get_value('email', params, required=True)
        code = self._get_value('code', params, required=True)

        # Get the customer
        customer = self.context.get(email)

        # This should exist
        if customer is None:
            raise RecoveryChallengeFailed(u'This link is no longer valid. Please enter your email again.')

        # Validate code against the challenge
        # This should raise if invalid
        if not validate_challenge_for_customer(customer, code):
            raise RecoveryChallengeFailed(u"That code wasn't valid. Give it another go!")

        # remember the user
        remember(self.request, email)

        notify(CustomerVerifiedEvent(customer))

        # See other the user to the create site form
        return {'email': email,
                'customer': customer}

    def _get_recovery_error_url(self):
        recovery_url = urljoin(self.request.application_url, 'recover')
        parsed = urllib_parse.urlparse(recovery_url)
        parsed = list(parsed)
        query = parsed[4]
        error = u'This link is no longer valid. Please enter your email again.'
        if query:
            query = query + '&error=' + urllib_parse.quote(error)
        else:
            query = 'error=' + urllib_parse.quote(error)
        parsed[4] = query
        return urllib_parse.urlunparse(parsed)

    @view_config(name=EMAIL_CHALLENGE_VERIFY_VIEW, request_method='GET')
    @view_config(name=RECOVERY_CHALLENGE_VERIFY_VIEW, request_method='GET')
    def verify_from_link(self):
        params = self.request.params
        try:
            self.do_verify(params)
        except RecoveryChallengeFailed:
            forget(self.request)
            recovery_url = self._get_recovery_error_url()
            return hexc.HTTPFound(location=recovery_url,
                                  headers=self.request.response.headers)

        # we have side effects
        self.request.environ['nti.request_had_transaction_side_effects'] = True

        # once verified, redirect to home page.
        return hexc.HTTPFound(location=self.request.application_url,
                              headers=self.request.response.headers)

    @view_config(name=EMAIL_CHALLENGE_VERIFY_VIEW, request_method='POST')
    @view_config(name=RECOVERY_CHALLENGE_VERIFY_VIEW, request_method='POST')
    def verify_from_api(self):
        try:
            data = self.do_verify(self.body_params)
        except RecoveryChallengeFailed as e:
            forget(self.request)
            raise raise_json_error(hexc.HTTPBadRequest,
                                   e.args[0])

        result = LocatedExternalDict()
        result.__name__ = self.context.__name__
        result.__parent__ = self.context.__parent__
        result.update(data)
        return result

    def __call__(self):
        self._do_call(self.body_params, _generate_verify_url=self._generate_verify_url)
        return hexc.HTTPNoContent()


@view_config(renderer='rest',
             name=AUTH_TOKEN_VIEW,
             request_method='GET',
             context=ICustomer)
class CustomerAuthTokenVerifyView(BaseView):
    """
    An authentication view that validates the customer's auth token for a site.
    This endpoint is accessed via the link we generate for the "Set My Password"
    email during site setup.

    On success, this will authenticate the user and redirect them to the success
    url (the app site). This will occur regardless of the current user's auth
    status.

    On failure, if the token does not exist or if expired, we will we send
    the user to the app recovery page.
    """


    def __call__(self):
        params = self.request.params
        site_id = self._get_value('site', params, required=True)
        success_url = self._get_value('success', params, required=True)
        token_val = self._get_value('token', params, required=True)
        if validate_auth_token(self.context, token_val, site_id):
            # Validated, authenticate and forward.
            forget(self.request)
            remember(self.request, self.context.email)
            result = hexc.HTTPFound(location=success_url,
                                    headers=self.request.response.headers)
        else:
            forget(self.request)
            # Invalid or expired, send to recovery app page.
            recovery_url = urljoin(self.request.application_url, 'recover')
            result = hexc.HTTPFound(location=recovery_url,
                                    headers=self.request.response.headers)
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


@view_defaults(renderer='rest',
               context=ICustomersContainer,
               request_method='POST',
               permission=ACT_CREATE)
class CustomerCreationView(BaseView, ObjectCreateUpdateViewMixin):

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

        if self._hubspot_client is None:
            raise_json_error(hexc.HTTPUnprocessableEntity,
                             "No hubspot support is available.")

        contact = self._hubspot_client.fetch_contact_by_email(email)
        if not contact:
            raise_json_error(hexc.HTTPUnprocessableEntity,
                             "No hubspot contact found: {}.".format(email))

        if not contact['name']:
            raise_json_error(hexc.HTTPUnprocessableEntity,
                             "Name is missing on hubspot: {}.".format(email))

        customer = createCustomer(self.context,
                                  email=email,
                                  name=contact['name'],
                                  phone=contact['phone'],
                                  hs_contact_vid=contact['canonical-vid'])
        self.request.response.status = 201
        return customer

    @view_config()
    def create(self):
        # Used for QA testing for now,
        # we don't bind customers created here with HubSpot,
        # and no CustomerVerifiedEvent should be fired.
        try:
            customer = self.createObjectWithExternal()
            self.context.addCustomer(customer)
            self.request.response.status = 201
            logger.info("%s created a new customer, email: %s.",
                        self.request.authenticated_userid,
                        customer.email)
            return customer
        except InvalidItemType:
            raise_json_error(hexc.HTTPUnprocessableEntity, "Invalid customer type.")
        except KeyError as err:
            raise_json_error(hexc.HTTPConflict,
                             "Existing customer: {}.".format(str(err)))
