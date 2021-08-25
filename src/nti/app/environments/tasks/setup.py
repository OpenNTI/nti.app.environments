import datetime

from zope import component

from zope.event import notify

from zope.lifecycleevent import modified

from nti.environments.management.interfaces import ICeleryApp
from nti.environments.management.interfaces import ISetupEnvironmentTask

from nti.app.environments.models.interfaces import ISetupStatePending
from nti.app.environments.models.interfaces import ISetupStateSuccess
from nti.app.environments.models.interfaces import SITE_STATUS_ACTIVE
from nti.app.environments.models.interfaces import SITE_STATUS_PENDING

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

    # Interacting with the site almost always requires an accurate state
    # state and an appropriate ds id, so do that here, rather than in a subscriber on
    # ILMSSiteSetupFinished. That let's those subscribers rely on the
    # state being complete. This used to happen in a ILMSSiteSetupFinished subscriber
    # which creates ordering issues.

    if ISetupStateSuccess.providedBy(site.setup_state):
        changed = False
        if site.status == SITE_STATUS_PENDING:
            site.status = SITE_STATUS_ACTIVE
            changed = True

        setup_info = site.setup_state.site_info
            
        # TODO At this point this should never be set, right?
        if not site.ds_site_id and setup_info.ds_site_id:
            logger.info('Updating ds_site_id for %s to %s', site, setup_info.ds_site_id)
            site.ds_site_id = setup_info.ds_site_id
            changed = True

        if changed:
            modified(site)

    logger.info('Notifying setup finished for %s', site)
    
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

