import os
import hashlib
import requests

from pyramid import httpexceptions as hexc

from pyramid.security import remember
from pyramid.security import forget

from pyramid.view import view_config

from six.moves import urllib_parse

from zope import component

from nti.app.environments.interfaces import IOnboardingSettings

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

        headers = remember(request, email)
        request.session['login.realname'] = profile.get('name') or 'Unknown Name'
        success = request.session.get('google.success') or _DEFAULT_SUCCESS_URL
        return hexc.HTTPFound(location=success, headers=headers)

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


@view_config(request_method='GET',
             name=LOGOUT_VIEW)
def logout(context, request):
    request.session.invalidate()
    headers = forget(request)
    url = urllib_parse.urljoin(request.application_url, LOGIN_VIEW)
    return hexc.HTTPFound(location=url,
                          headers=headers)
