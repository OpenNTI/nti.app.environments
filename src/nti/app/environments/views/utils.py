import json
import pytz
from dateutil import parser

from zope.schema._bootstrapinterfaces import ConstraintNotSatisfied
from zope.schema._bootstrapinterfaces import ValidationError


def raise_json_error(factory, error, field=None):
    if isinstance(error, ValidationError):
        if isinstance(error, ConstraintNotSatisfied):
            message = 'Invalid {}.'.format(error.args[1])
        else:
            message = error.args[0] if error.args else str(error)
    else:
        message = error

    body = {'message': message} if not isinstance(message, dict) else message
    if field:
        body['field'] = field
    body = json.dumps(body)
    result = factory(message)
    result.text = body
    raise result


def convertToUTC(dt, local_tz='US/Central'):
    local_date = pytz.timezone(local_tz).localize(dt)
    return local_date.astimezone(pytz.utc).replace(tzinfo=None)


def parseDate(strDate, local_tz='US/Central', safe=False, convert=True, ignoretz=True):
    """
    Parse local datetime and convert it to utc.
    """
    try:
        date = parser.parse(strDate, ignoretz=ignoretz)
        return convertToUTC(date, local_tz) if convert else date
    except ValueError as e:
        if safe:
            return None
        raise e


def formatDate(dt, _format='%Y-%m-%dT%H:%M:%SZ', default=''):
    return dt.strftime(_format) if dt else default


def formatDateToLocal(dt, _format='%Y-%m-%dT%H:%M:%S', default='', local_tz='US/Central'):
    if dt and local_tz:
        utc_date = pytz.utc.localize( dt )
        dt = utc_date.astimezone(pytz.timezone(local_tz))
    return formatDate(dt, _format=_format, default=default)
