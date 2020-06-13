import os
import hashlib
import requests

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from six.moves import urllib_parse

from zope import component

from nti.mailer.interfaces import ITemplatedMailer

from nti.externalization.interfaces import LocatedExternalDict

from nti.app.environments.authentication import forget
from nti.app.environments.authentication import remember
from nti.app.environments.authentication import setup_challenge_for_customer
from nti.app.environments.authentication import validate_challenge_for_customer

from nti.app.environments.interfaces import IOnboardingSettings
from nti.app.environments.interfaces import IOTPGenerator

from nti.app.environments.models.interfaces import IOnboardingRoot
from nti.app.environments.models.interfaces import checkEmailAddress

from nti.app.environments.models.utils import get_customers_folder

from .base import BaseView
from .customers import EmailChallengeView
from .customers import EmailChallengeVerifyView
from .utils import raise_json_error

logger = __import__('logging').getLogger(__name__)


OPENID_CONFIGURATION = None
DISCOVERY_DOC_URL = 'https://accounts.google.com/.well-known/openid-configuration'
DEFAULT_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
DEFAULT_TOKEN_URL = 'https://oauth2.googleapis.com/token'
DEFAULT_USERINFO_URL = 'https://openidconnect.googleapis.com/v1/userinfo'

LOGIN_VIEW = 'login'
LOGON_GOOGLE_VIEW = 'logon.google'
LOGON_GOOGLE_OAUTH2_VIEW = 'logon.google.oauth2'
LOGOUT_VIEW = 'logout'


def _get_google_hosted_domain():
    return 'nextthought.com'


def get_openid_configuration():
    global OPENID_CONFIGURATION
    if not OPENID_CONFIGURATION:
        s = requests.get(DISCOVERY_DOC_URL)
        OPENID_CONFIGURATION = s.json() if s.status_code == 200 else {}
    return OPENID_CONFIGURATION


def _get_redirect_uri(request):
    return urllib_parse.urljoin(request.application_url, LOGON_GOOGLE_OAUTH2_VIEW)


_DEFAULT_SUCCESS_URL = '/onboarding'

def _success_url(request):
    return request.params.get('success') or _DEFAULT_SUCCESS_URL

@view_config(request_method='GET',
             name=LOGON_GOOGLE_VIEW)
def google_oauth1(context, request):
    success = _success_url(request)
    if request.authenticated_userid:
        return hexc.HTTPFound(location=success, headers=request.response.headers)

    # Google oauth2 reference
    # https://developers.google.com/identity/protocols/OpenIDConnect
    state = hashlib.sha256(os.urandom(1024)).hexdigest()
    request.session['google.state'] = state
    request.session['google.success'] = success

    settings = component.getUtility(IOnboardingSettings)

    params = {
        "state" : state,
        "response_type" : "code",
        "scope" : "openid email profile",
        "client_id" : settings['google_client_id'],
        "redirect_uri" : _get_redirect_uri(request)
    }

    hosted_domain = _get_google_hosted_domain()
    if hosted_domain:
        params['hd'] = hosted_domain

    config = get_openid_configuration()
    auth_url = config.get("authorization_endpoint", DEFAULT_AUTH_URL)

    auth_url = '%s?%s' % (auth_url, urllib_parse.urlencode(params))
    response = hexc.HTTPSeeOther(location=auth_url)
    return response


@view_config(request_method='GET',
             name=LOGON_GOOGLE_OAUTH2_VIEW)
def google_oauth2(context, request):
    params = request.params

    state = params.get('state')
    if not state or state != request.session.get('google.state'):
        raise hexc.HTTPBadRequest("state doesn't match.")

    code = params.get('code')
    if not code:
        raise hexc.HTTPBadRequest("code can not be empty.")

    # Exchange code for access token and ID token
    config = get_openid_configuration()
    token_url = config.get('token_endpoint', DEFAULT_TOKEN_URL)

    settings = component.getUtility(IOnboardingSettings)

    try:
        data = {'code': code,
                'client_id': settings['google_client_id'],
                'grant_type': 'authorization_code',
                'client_secret': settings['google_client_secret'],
                'redirect_uri': _get_redirect_uri(request)}
        response = requests.post(token_url, data)
        if response.status_code != 200:
            raise hexc.HTTPUnprocessableEntity("Invalid response while getting access token.")

        data = response.json()
        if 'access_token' not in data:
            raise hexc.HTTPUnprocessableEntity("Could not find access token.")

        if 'id_token' not in data:
            raise hexc.HTTPUnprocessableEntity('Could not find id token.')

        # TODO(Optional):Validate id token

        access_token = data['access_token']
        userinfo_url = config.get('userinfo_endpoint', DEFAULT_USERINFO_URL)
        response = requests.get(userinfo_url, params={ "access_token": access_token})
        if response.status_code != 200:
            raise hexc.HTTPUnprocessableEntity('Invalid access token.')

        profile = response.json()

        # Make sure only NextThought user could login.
        email = profile['email']
        hosted_domain = _get_google_hosted_domain()
        if hosted_domain:
            domain = email.split('@')[1]
            if domain != hosted_domain:
                raise hexc.HTTPUnprocessableEntity('Invalid domain')

        remember(request, email)
        request.session['login.realname'] = profile.get('name') or 'Unknown Name'
        success = request.session.get('google.success') or _DEFAULT_SUCCESS_URL
        return hexc.HTTPFound(location=success, headers=request.response.headers)

    except Exception as e:
        logger.exception('Failed to login with google')
        raise hexc.HTTPUnprocessableEntity(str(e))


@view_config(renderer='../templates/login.pt',
             request_method='GET',
             name=LOGIN_VIEW)
def login(context, request):
    success = _success_url(request)
    if request.authenticated_userid:
        return hexc.HTTPFound(location=success, headers=request.response.headers)
    return {'rel_logon': urllib_parse.urljoin(request.application_url, LOGON_GOOGLE_VIEW),
            'success': success}

@view_config(context=IOnboardingRoot,
             request_method='POST',
             name='login.email',
             renderer='rest')
class LoginWithEmailView(EmailChallengeView):

    _email_template = 'nti.app.environments:email_templates/login_with_email'

    def _do_call(self, params):        
        forget(self.request)

        email = self._get_value('email', params, None)
        if not email or not checkEmailAddress(email):
            raise_json_error(hexc.HTTPUnprocessableEntity, 'Invalid Email.')

        # *Important* Note the care taken here to keep the flows
        # as close to possible whether or not we have a customer.
        # We don't want don't the response to vary in data or
        # other noticible ways (ideally even in timing) or this becomes a method
        # to farm valid customer emails.

        customers = get_customers_folder(request=self.request)
        try:
            customer = customers[email]
        except:
            customer = None

        if customer:
            code = setup_challenge_for_customer(customer)
        else:
            otp = component.getUtility(IOTPGenerator)
            code = otp.generate_passphrase()

        code_prefix = code[:6]
        code_suffix = code[6:].upper()

        template_args = {
            'email': email,
            'code_suffix': code_suffix,
            'app_link': None
        }

        if customer is None:
            self._send_mail('nti.app.environments:email_templates/customer_not_found',
                            subject=f'Your account was not found: {email}',
                            recipients=[email],
                            template_args=template_args)
        else:
            self._send_mail('nti.app.environments:email_templates/login_with_email',
                            subject=self._email_subject(code_suffix),
                            recipients=[customer.email],
                            template_args=template_args)

        return {'email': email,
                'code_prefix': code_prefix}

@view_config(context=IOnboardingRoot,
             renderer='rest',
             request_method='POST',
             name='login.email.verify')
class LoginWithEmailVerifyView(EmailChallengeVerifyView):

    @property
    def customers(self):
        return get_customers_folder(request=self.request)

    def __call__(self):
        return self.verify_from_api()


@view_config(request_method='GET',
             name=LOGOUT_VIEW)
def logout(context, request):
    request.session.invalidate()
    forget(request)
    url = urllib_parse.urljoin(request.application_url, LOGIN_VIEW)
    return hexc.HTTPFound(location=url, headers=request.response.headers)
