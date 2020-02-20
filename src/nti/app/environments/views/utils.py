import json

from zope.schema._bootstrapinterfaces import ConstraintNotSatisfied
from zope.schema._bootstrapinterfaces import RequiredMissing
from zope.schema._bootstrapinterfaces import SchemaNotProvided
from zope.schema._bootstrapinterfaces import ValidationError
from zope.schema._bootstrapinterfaces import WrongContainedType

from zope.schema.interfaces import NotUnique

from nti.environments.management.dns import is_dns_name_available as _is_dns_name_available

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
