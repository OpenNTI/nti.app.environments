import json
import datetime

from zope.schema._bootstrapinterfaces import ConstraintNotSatisfied
from zope.schema._bootstrapinterfaces import RequiredMissing
from zope.schema._bootstrapinterfaces import SchemaNotProvided
from zope.schema._bootstrapinterfaces import ValidationError
from zope.schema._bootstrapinterfaces import WrongContainedType

from zope import component

from zope.event import notify

from zope.schema.interfaces import NotUnique

from nti.environments.management.dns import is_dns_name_available as _is_dns_name_available

from nti.environments.management.interfaces import ICeleryApp
from nti.environments.management.interfaces import ISetupEnvironmentTask

from nti.app.environments.models.interfaces import ISetupStatePending

from nti.app.environments.models.events import SiteSetupFinishedEvent

from nti.app.environments.models.sites import SetupStateFailure
from nti.app.environments.models.sites import SetupStateSuccess

from nti.app.environments.models.utils import get_sites_folder

logger = __import__('logging').getLogger(__name__)


def raise_json_error(factory, error, field=None):
    if isinstance(error, ValidationError):
        if isinstance(error, ConstraintNotSatisfied):
            message = 'Invalid {}.'.format(error.args[1])

        elif isinstance(error, SchemaNotProvided):
            message = "Invalid {}.".format(error.args[0].__name__)

        elif isinstance(error, WrongContainedType) \
            and error.args[0] \
            and isinstance(error.args[0][0], RequiredMissing):
            message = 'Missing field: {}.'.format(error.args[1])

        elif isinstance(error, RequiredMissing):
            message = 'Missing field: {}.'.format(error.args[0])

        elif isinstance(error, NotUnique):
            message = "Existing duplicated {} for {}.".format(error.args[1], error.args[2])

        else:
            message = error.args[0] if error.args else str(error)
    else:
        message = str(error)

    body = {'message': message} if not isinstance(message, dict) else message
    if field:
        body['field'] = field
    body = json.dumps(body)
    result = factory(message)
    result.text = body
    raise result


def is_dns_name_available(dns_name, sites_folder=None):
    """
    A domain is available if a) there are know sites that use the domain
    and b) there isn't a dns reservation for it.
    """
    sites_folder = get_sites_folder() if sites_folder is None else sites_folder
    for site in sites_folder.values():
        dns_names = site.dns_names or ()
        if dns_name in dns_names:
            return False
    return _is_dns_name_available(dns_name)


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


def query_setup_state(sites, request, side_effects=True):
    """
    Query the sites setup state, return True if a site of pending state exists,
    and has celery result, or return False otherwise.
    """
    updated = False
    app_task = ISetupEnvironmentTask(component.getUtility(ICeleryApp))

    for site in sites or ():
        result = query_setup_async_result(site, app_task)
        if result is None:
            continue

        _mark_site_setup_finished(site, result)

        if updated is False:
            updated = True

    if side_effects and updated:
        request.environ['nti.request_had_transaction_side_effects'] = True

    return updated
