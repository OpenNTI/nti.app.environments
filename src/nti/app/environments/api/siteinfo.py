import datetime
import time
import requests
import jwt

from requests import exceptions as rexc

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.event import notify

from nti.app.environments.api.interfaces import IBearerTokenFactory
from nti.app.environments.api.interfaces import ISiteUsageUpdater
from nti.app.environments.api.interfaces import AuthenticatedSessionRequiredException
from nti.app.environments.api.interfaces import MissingTargetException

from nti.app.environments.models.interfaces import ISetupStateSuccess
from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import SITE_STATUS_ACTIVE
from nti.app.environments.models.interfaces import ISiteUsage

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

    def make_url(self, target):
        """
        Make the url to fetch from the target. Target can be something
        with an href, or a string. If a string and it is not a fully qualified url
        it will be made one using the preferred hostname.
        """
        try:
            target = target.href
        except AttributeError:
            pass

        try:
            target = target['href']
        except (TypeError, KeyError):
            pass

        if not isinstance(target, str):
            raise ValueError('Target must be a string or have an href that is a string', target)

        if not target.startswith('http'):
            assert target[0] == '/'
            target = 'https://%s%s' % (self._preferred_hostname, target)

        return target

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

    def get(self, target, *args, **kwargs):
        url = self.make_url(target)
        logger.info('Requesting information from platform at url %s', url)
        return self.session.get(url, *args, **kwargs)


def _object_with_fields(iterable, default=None, **kwargs):
    """
    Returns the next item from the iterable that matches the fields provided as kwargs
    """
    def _matches(o, kvs):
        for k,v in kvs.items():
            if o[k] != v:
                return False
        return True

    return next((o for o in iterable if _matches(o, kwargs)), default)

def get_workspace(service, workspace):
    """
    Given a json object representing a service doc find the workspace with the given title.
    """
    return _object_with_fields(service['Items'], Title=workspace, Class='Workspace', default=None)

def get_collection(workspace, collection):
    """
    Given a json object representing a workspace, find the collection with the given title.
    """
    return _object_with_fields(workspace['Items'], Title=collection, Class='Collection', default=None)

def get_link(obj, rel):
    """
    Given a json object with a list of Links, find the link with the given rel.
    """
    return _object_with_fields(obj['Links'], rel=rel, default=None)

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

_INSTRUCTOR_ROLES = ('nti.roles.course_content_editor',
                     'nti.roles.course_instructor',
                     'nti.roles.course_ta')

class SiteUsageUpdater(object):

    def __init__(self, site, client):
        self.site = site
        self.client = client
        self.ping = self.client.dataserver_ping()

        if not self.ping['AuthenticatedUsername']:
            raise AuthenticatedSessionRequiredException('Updating site usage requires an authenticated admin exception')

    @Lazy
    def ds_site_id(self):
        return self.ping['Site']

    @Lazy
    def service(self):
        continue_link = get_link(self.ping, 'logon.continue')
        if not continue_link:
            raise MissingTargetException('Pong is missing the logon.continue link')
        resp = self.client.get(continue_link)
        resp.raise_for_status()
        return resp.json()

    @Lazy
    def user_count(self):
        global_workspace = get_workspace(self.service, 'Global')
        seat_limit_link = get_link(global_workspace, 'SeatLimit')
        if not seat_limit_link:
            raise MissingTargetException('Service missing SeatLimit link on the Global workspace')
        resp = self.client.get(seat_limit_link)
        resp.raise_for_status()
        return resp.json()['used_seats']

    @Lazy
    def course_audit_url(self):
        """
        This currently isn't exposed, probably for good reason
        since the data we are returning could be considered "in flux"
        """
        return '/dataserver2/++etc++hostsites/%s/++etc++site/Courses/@@AuditUsageInfo' % self.ds_site_id

    @Lazy
    def course_audit_info(self):
        try:
            resp = self.client.get(self.course_audit_url)
            resp.raise_for_status()
        except rexc.HTTPError as e:
            # This is a pretty new api, so if it 404s we just won't give this data
            if e.response.status_code == 404:
                logger.warn('When fetching AuditUsageInfo at %s a 404 was returned. Some usage info may be missing', self.course_audit_url)
                return None
            raise
        return resp.json()

    @Lazy
    def course_count(self):
        """
        The number of courses in the catalog. note this currently includes courses
        inherited from parent catalogs as well as the global catalog.
        """
        return self.course_audit_info['Total'] if self.course_audit_info else None

    @Lazy
    def site_admin_usernames(self):
        """
        The set of usernames which are site admins
        """
        site_admin_workspace = get_workspace(self.service, 'SiteAdmin')
        site_admins_link = get_link(site_admin_workspace, 'SiteAdmins')
        if not site_admins_link:
            raise MissingTargetException('Service missing SiteAdmins link on SiteAdmin workspace')

        # Currently this api doesn't page, this gets more complicated when it starts paging
        resp = self.client.get(site_admins_link, params={'deactivated': 'false'})
        resp.raise_for_status()
        return set(x['Username'] for x in resp.json()['Items'])

    @Lazy
    def site_instructor_usernames(self):
        """
        The set of usernames that have some sort of instructor role on any course in the site
        """
        if not self.course_audit_info:
            return None

        instructor_usernames = set()
        for catalog_id, usage_info in self.course_audit_info['Items'].items():
            roles = usage_info.get('roles', {})
            for role in roles:
                if role not in _INSTRUCTOR_ROLES:
                    continue
                instructor_usernames.update(roles[role])
        return instructor_usernames

    @Lazy
    def scorm_package_count(self):
        """
        Returns the number of scorm packages _available_ to this site.
        If scorm is disabled returns None
        """
        scorm_workspace = get_workspace(self.service, 'SCORM')
        if not scorm_workspace:
            return None
        instances = get_collection(scorm_workspace, 'SCORMInstances')
        if not instances:
            raise MissingTargetException('Service missing SCORMInstances collection')
        resp = self.client.get(instances, params={'batchStart': 0, 'batchSize': 1})
        resp.raise_for_status()
        return resp.json()['Total']


    def __call__(self):
        logger.info('Updating usage information for site %s', self.site)
        usage = ISiteUsage(self.site)
        usage.updateLastMod()
        usage.user_count = self.user_count
        usage.course_count = self.course_count
        usage.admin_usernames = frozenset(self.site_admin_usernames)
        usage.instructor_usernames = frozenset(self.site_instructor_usernames) if self.site_instructor_usernames is not None else None
        usage.scorm_package_count = self.scorm_package_count
        logger.info('Updated usage information for site %s', self.site)

        return usage

@interface.provider(ISiteUsageUpdater)
def update_site_usage_info(site, client):
    return SiteUsageUpdater(site, client)()
