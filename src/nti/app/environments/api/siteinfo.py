import datetime
import time
import requests
import jwt

from zope import component
from zope import interface

from zope.event import notify

from nti.app.environments.api.interfaces import IBearerTokenFactory

from nti.app.environments.models.interfaces import ISetupStateSuccess
from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import SITE_STATUS_ACTIVE

from nti.app.environments.models.events import SiteOwnerCompletedSetupEvent

from nti.app.environments.interfaces import IOnboardingSettings

logger = __import__('logging').getLogger(__name__)

SITE_URL = 'https://{host_name}'
SITE_INFO_TPL = 'https://{host_name}/dataserver2/SiteBrand'
SITE_DATASERVER_PING_TPL = 'https://{host_name}/dataserver2/logon.ping'
SITE_LOGO_TPL = 'https://{host_name}{uri}'
SITE_INVITATION_TPL = 'https://{host_name}/dataserver2/Invitations/{code}'

_default_timeout_marker = object()

@interface.implementer(IBearerTokenFactory)
class BearerTokenFactory(object):

    algorithm = 'HS256'

    def __init__(self, secret, issuer, default_ttl=None):
        self.secret = secret
        self.issuer = issuer
        self.default_ttl = default_ttl

    def make_bearer_token(self, username, realname=None, email=None, ttl=_default_timeout_marker):

        payload = {
           'login': username,
           'realname': realname,
           'email': email,
           'create': "true",
           "admin": "true",
           "iss": self.issuer
        }

        # TODO should we even allow not having an expiration time?
        if ttl is not None:
            ttl = self.default_ttl if ttl is _default_timeout_marker else ttl
            payload['exp'] = time.time() + float(ttl)

        jwt_token = jwt.encode(payload,
                               self.secret,
                               algorithm=self.algorithm)
        return jwt_token.decode('utf8')

@component.adapter(ILMSSite)
def _bearer_factory_for_site(unused_site):
    """
    Create an IBearerTokenFactory for the site. Right
    now this isn't dependent on the site, but it's easy
    to imagine it being dependent on the site in the future
    """
    settings = component.getUtility(IOnboardingSettings)
    return BearerTokenFactory(settings.get('jwt_secret', '$Id$'),
                              settings.get('jwt_issuer', None),
                              settings.get('jwt_timeout', 30))

class NTClient(object):

    def __init__(self, site, bearer=None):
        self.site = site
        self.session = requests.Session()
        if bearer is not None:
            self.session.headers.update({'Authorization': f'Bearer {bearer}'})

    @property
    def _preferred_hostname(self):
        return self.site.dns_names[0]

    def _logo_url(self, resp):
        assets = resp['assets']
        login_logo = assets.get('login_logo') if assets else None
        return login_logo['href'] if login_logo else None

    def fetch_site_info(self):
        host_name = self._preferred_hostname
        try:
            logger.info("Fetching site info: {}.".format(host_name))
            url = SITE_INFO_TPL.format(host_name=host_name)
            resp = self.session.get(url, timeout=(5, 5))
            if resp.status_code != 200:
                logger.warn("Bad request. status code: %s.", resp.status_code)
                return None

            resp = resp.json()
            uri = self._logo_url(resp)
            logo_url = SITE_LOGO_TPL.format(host_name=host_name,uri=uri) if uri else None
            return {'logo_url': logo_url,
                    'brand_name': resp['brand_name'],
                    'site_url': SITE_URL.format(host_name=host_name)}
        except requests.exceptions.ConnectionError:
            logger.warn("Unknown site host: %s.", host_name)
            return None
        except requests.exceptions.ReadTimeout:
            logger.warn("Caught read timeout.")
            return None
        except ValueError:
            logger.warn("Bad json data from site host: %s.", host_name)
            return None

    def dataserver_ping(self):
        host_name = self._preferred_hostname
        try:
            logger.info("Performing dataserver2 logon.ping for: {}.".format(host_name))
            url = SITE_DATASERVER_PING_TPL.format(host_name=host_name)
            resp = self.session.get(url, timeout=(5, 5))
            if resp.status_code != 200:
                logger.warn("Bad request. status code: %s.", resp.status_code)
                return None

            return resp.json()
        except requests.exceptions.ConnectionError:
            logger.warn("Unknown site host: %s.", host_name)
            return None
        except requests.exceptions.ReadTimeout:
            logger.warn("Caught read timeout.")
            return None
        except ValueError:
            logger.warn("Bad json data from site host: %s.", host_name)
            return None

    def fetch_site_invitation(self, invitation_code):
        host_name = self._preferred_hostname
        url = SITE_INVITATION_TPL.format(host_name=host_name,
                                         code=invitation_code)
        try:
            return self.session.get(url)
        except requests.exceptions.ConnectionError:
            logger.warning("%s is offline?", host_name)
            return None

def query_invitation_status(sites):
    """
    Query all successfully setup sites and update the invitation status.
    """
    result = {'total': 0, 'accepted': 0, 'pending': 0,
              'expired': 0,'cancelled': 0, 'unknown': 0}

    for x in sites or ():
        if not ISetupStateSuccess.providedBy(x.setup_state) \
            or x.setup_state.invite_accepted_date \
            or not x.setup_state.invitation_active \
            or not x.setup_state.site_info.admin_invitation_code\
            or x.status != SITE_STATUS_ACTIVE:
            continue

        # TODO Use an onboarding specific user here?
        token_generator = IBearerTokenFactory(x)
        jwt = token_generator.make_bearer_token('admin@nextthought.com')

        nt_client = NTClient(x)

        result['total'] += 1

        code = x.setup_state.site_info.admin_invitation_code

        resp = nt_client.fetch_site_invitation(code)
        if resp is None:
            result['unknown'] += 1
            continue

        if resp.status_code == 404:
            logger.warning("Invitation (%s) was cancelled?", code)
            x.setup_state.invitation_active =False
            result['cancelled'] += 1
            continue

        if resp.status_code != 200:
            # This shouldn't happen, status code may like 401 ,403.
            logger.warning("%s error with invitation code (%s).", resp.status_code, code)
            result['unknown'] += 1
            continue

        body = resp.json()

        if 'acceptedTime' not in body:
            logger.warning('acceptedTime not in invitation info (%s)', body)

        acceptedTime = body.get('acceptedTime')
        if acceptedTime is not None:
            x.setup_state.invite_accepted_date = datetime.datetime.utcfromtimestamp(acceptedTime)
            notify(SiteOwnerCompletedSetupEvent(x))
            result['accepted'] += 1
            continue

        isExpired = bool(body.get('expiryTime') and body['expiryTime'] <= time.time())
        if isExpired:
            x.setup_state.invitation_active =False
            result['expired'] += 1
            continue

        result['pending'] += 1

    return result
