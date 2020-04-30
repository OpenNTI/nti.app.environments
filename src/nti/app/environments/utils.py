import datetime
import requests
import time
import jwt

from zope import component

from zope.event import notify

from nti.environments.management.interfaces import ICeleryApp
from nti.environments.management.interfaces import ISetupEnvironmentTask

from nti.app.environments.models.interfaces import ISetupStatePending
from nti.app.environments.models.interfaces import ISetupStateSuccess
from nti.app.environments.models.interfaces import SITE_STATUS_ACTIVE

from nti.app.environments.models.events import SiteSetupFinishedEvent
from nti.app.environments.models.events import SiteOwnerCompletedSetupEvent

from nti.app.environments.models.sites import SetupStateFailure
from nti.app.environments.models.sites import SetupStateSuccess

from nti.app.environments.interfaces import IOnboardingSettings

logger = __import__('logging').getLogger(__name__)


def query_setup_async_result(site, app_task=None):
    """
    Return the celery task async result or None
    """
    setup_state = site.setup_state

    # Finished already, return immediately
    if not ISetupStatePending.providedBy(setup_state):
        return None

    if app_task is None:
        app = component.getUtility(ICeleryApp)
        app_task = ISetupEnvironmentTask(app)

    assert setup_state.task_state

    async_result = app_task.restore_task(setup_state.task_state)

    if not async_result.ready():
        return None

    return async_result.result


def _create_setup_state(factory, pending_state):
    """
    Create a new end state based on pending state.
    """
    result = factory()
    result.start_time = pending_state.start_time
    result.end_time = datetime.datetime.utcnow()
    result.task_state = pending_state.task_state
    return result


def _mark_site_setup_finished(site, result):
    """
    Mark site finished once we get result from celery.
    """
    if isinstance(result, Exception):
        state = _create_setup_state(SetupStateFailure,
                                    site.setup_state)
        state.exception = result
    else:
        state = _create_setup_state(SetupStateSuccess,
                                    site.setup_state)
        state.site_info = result
        logger.info('Site setup complete (id=%s) (task_time=%.2f) (duration=%.2f) (successfully=True)',
                    site.id,
                    result.elapsed_time or -1,
                    state.elapsed_time or -1)

    # Overwrite with our new state
    site.setup_state = state
    notify(SiteSetupFinishedEvent(site))


def query_setup_state(sites, request=None, side_effects=True):
    """
    Query the sites setup state, return True if a site of pending state exists,
    and has celery result, or return False otherwise.
    """
    updated = 0
    app_task = ISetupEnvironmentTask(component.getUtility(ICeleryApp))

    for site in sites or ():
        result = query_setup_async_result(site, app_task)
        if result is None:
            continue

        _mark_site_setup_finished(site, result)

        updated += 1

    if request is not None and side_effects and updated > 0:
        request.environ['nti.request_had_transaction_side_effects'] = True

    return updated


def generate_jwt_token(username, realname=None, email=None,
                       secret=None, issuer=None, timeout=None):
    settings = component.getUtility(IOnboardingSettings)

    secret = settings.get('jwt_secret', '$Id$') if secret is None else secret
    issuer = settings.get('jwt_issuer', None) if issuer is None else issuer
    timeout=settings.get('jwt_timeout', 30) if timeout is None else timeout

    payload = {
        'login': username,
        'realname': realname,
        'email': email,
        'create': "true",
        "admin": "true",
        "iss": issuer
    }
    if timeout is not None:
        payload['exp'] = time.time() + float(timeout)

    jwt_token = jwt.encode(payload,
                           secret,
                           algorithm='HS256')
    return jwt_token.decode('utf8')


def fetch_site_invitation(host_name, invitation_code, adminUser='admin@nextthought.com'):
    url = 'https://{host}/dataserver2/Invitations/{code}'.format(host=host_name,
                                                                 code=invitation_code)
    jwt_token = generate_jwt_token(adminUser)
    try:
        return requests.get(url, params={'jwt': jwt_token})
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

        result['total'] += 1

        code = x.setup_state.site_info.admin_invitation_code

        resp = fetch_site_invitation(x.dns_names[0], code)
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
