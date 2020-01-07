import calendar
import datetime
import pytz

from dateutil import parser


def find_iface(resource, iface):
    while resource is not None:
        if iface.providedBy(resource):
            return resource
        try:
            resource = resource.__parent__
        except AttributeError:
            resource = None
    return None


def convertToUTC(dt, local_tz='US/Central', toTimeStamp=False):
    local_date = pytz.timezone(local_tz).localize(dt)
    dt = local_date.astimezone(pytz.utc).replace(tzinfo=None)
    return calendar.timegm(dt.utctimetuple()) if toTimeStamp else dt


def parseDate(strDate, local_tz='US/Central', safe=False, convert=True, ignoretz=True, toTimeStamp=False):
    """
    Parse local datetime and convert it to utc.
    """
    try:
        date = parser.parse(strDate, ignoretz=ignoretz)
        date = convertToUTC(date, local_tz) if convert else date
        return calendar.timegm(date.utctimetuple()) if toTimeStamp else date
    except ValueError as e:
        if safe:
            return None
        raise e


def formatDate(dt, _format='%Y-%m-%dT%H:%M:%SZ', default=''):
    return dt.strftime(_format) if dt else default


def formatDateToLocal(dt, _format='%Y-%m-%d %H:%M:%S', default='', local_tz='US/Central'):
    if isinstance(dt, (float, int)):
        dt = datetime.datetime.utcfromtimestamp(dt)

    if dt and local_tz:
        utc_date = pytz.utc.localize( dt )
        dt = utc_date.astimezone(pytz.timezone(local_tz))
    return formatDate(dt, _format=_format, default=default)
