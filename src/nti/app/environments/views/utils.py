import json

from zope.schema._bootstrapinterfaces import ConstraintNotSatisfied
from zope.schema._bootstrapinterfaces import RequiredMissing
from zope.schema._bootstrapinterfaces import SchemaNotProvided
from zope.schema._bootstrapinterfaces import ValidationError
from zope.schema._bootstrapinterfaces import WrongContainedType


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
