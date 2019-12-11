import json
import pytz
from dateutil import parser


def raise_json_error(factory, message, field=None):
    body = {'message': message} if not isinstance(message, dict) else message
    if field:
        body['field'] = field
    body = json.dumps(body)
    result = factory(message)
    result.text = body
    raise result


def find_iface(resource, iface):
    while resource is not None:
        if iface.providedBy(resource):
            return resource
        try:
            resource = resource.__parent__
        except AttributeError:
            resource = None
    return None


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
