import datetime

from zope import interface
from zope import component

from zope.cachedescriptors.property import Lazy

from zope.publisher.interfaces.browser import IBrowserRequest

from zope.traversing.browser.interfaces import IAbsoluteURL

from z3c.table import column
from z3c.table import header
from z3c.table import value
from z3c.table import table
from z3c.table import batch

from z3c.table.interfaces import ITable
from z3c.table.interfaces import IBatchProvider

from nti.app.environments.auth import ACT_DELETE

from nti.app.environments.models.interfaces import ITrialLicense
from nti.app.environments.models.interfaces import SITE_STATUS_ACTIVE

from nti.app.environments.utils import formatDateToLocal


@interface.implementer(IAbsoluteURL)
@component.adapter(ITable, IBrowserRequest)
class TrivialTableAbsoluteURL(object):
    """
    Needed to be able to produce the batching URLs.
    """
    def __init__( self, context, request ):
        self.context = context
        self.request = request

    def __call__( self ):
        return self.request.path


@interface.implementer(IBatchProvider)
class DefaultTableBatchProvider(batch.BatchProvider):

    _request_args = ['%(prefix)s-sortOn', '%(prefix)s-sortOrder', 'search']


class BaseTable(table.Table):

    cssClasses = {'table':'table',
                  'thead':'thead',
                  'tbody':'tbody',
                  'th':'th',
                  'tr':'tr',
                  'td':'td'}

    batchSize = 25
    startBatchingAt = 25

    batchProviderName = "default-batch"

    def batchRows(self):
        try:
            super(BaseTable, self).batchRows()
        except IndexError:
            self.batchStart = len(self.rows) - self.getBatchSize()
            super(BaseTable, self).batchRows()


def make_specific_table(tableClassName, container, request, **kwargs):
    the_table = tableClassName(container, IBrowserRequest(request), **kwargs)
    try:
        the_table.update()
    except IndexError:
        the_table.batchStart = len(the_table.rows) - the_table.getBatchSize()
        the_table.update()

    return the_table


class EmailColumn(column.LinkColumn):

    weight = 1
    header = 'Email'

    def getLinkURL(self, item):
        return self.request.route_url('admin', traverse=('customers', item.__name__, '@@details'))

    def getLinkContent(self, item):
        return item.email


class NameColumn(column.GetAttrColumn):
    weight = 2
    header = 'Name'
    attrName = 'name'

    def getValue(self, item):
        return item.name or ''

    def getSortKey(self, item):
        return self.getValue(item)


class HubSpotColumn(column.GetAttrColumn):

    weight = 3
    header = 'HubSpot'
    attrName = 'hubspot_contact'

    def getValue(self, item):
        hc = item.hubspot_contact
        return hc.contact_vid if hc else ''

    def getSortKey(self, item):
        return self.getValue(item)


class BaseDateColumn(column.GetAttrColumn):

    def getValue(self, item):
        value = getattr(item, self.attrName)
        return formatDateToLocal(value)

    def getSortKey(self, item):
        return self.getValue(item)


class CreatedColumn(BaseDateColumn):

    weight = 4
    header = 'Created'
    attrName = 'created'


class LastVerifiedColumn(BaseDateColumn):

    weight = 5
    header = 'LastVerified'
    attrName = 'last_verified'


class DeleteColumn(column.Column):

    weight = 7
    buttonTitle = 'Delete'
    cssClasses = {'td': 'nti_delete',
                  'th': 'nti_delete'}

    def renderCell(self, item):
        if self.request.has_permission(ACT_DELETE, item):
            template = """<button onclick="openDeletingModal('{url}', '{id}');">Delete</button>"""
            return  template.format(url=self.request.resource_url(item),
                                    id=item.__name__)
        return ''


class CustomersTable(BaseTable):

    @Lazy
    def _raw_values(self):
        return self.context.values()


class CustomerColumnHeader(header.SortingColumnHeader):

    _request_args = ['search']


class _FilterMixin(object):

    def _get_filter(self, name, params):
        value = params.get(name) or ''
        return value.strip()


class ValuesForCustomersTable(value.ValuesForContainer, _FilterMixin):

    def _predicate(self, item, email):
        return email in item.email.lower()

    @property
    def values(self):
        params = self.request.params
        email = self._get_filter('search', params)
        return self.context.values() if not email \
                         else [x for x in self.context.values() if self._predicate(x, email.lower())]


# Sites table

class BaseSitesTable(BaseTable, _FilterMixin):

    _raw_filter = None

    @Lazy
    def _raw_values(self):
        if self._raw_filter:
            return [x for x in self.context.values() if self._raw_filter(x)]
        return self.context.values()

    def _predicate(self, item, term):
        if term in item.id.lower():
            return True
        for dns in item.dns_names:
            if term in dns.lower():
                return True
        return False

    @property
    def values(self):
        params = self.request.params
        term = self._get_filter('search', params)
        return self._raw_values if not term else [x for x in self._raw_values if self._predicate(x, term.lower())]


class SitesTable(BaseSitesTable):

    def __init__(self, context, request, **kwargs):
        super(SitesTable, self).__init__(context, request)
        self._email = kwargs.get('email')

    @Lazy
    def _raw_filter(self):
        if self._email:
            return lambda x: x.owner and x.owner.email == self._email


class SiteColumnHeader(header.SortingColumnHeader):

    _request_args = ['search']


class SiteURLColumn(column.LinkColumn):

    weight = 0
    header = 'Site'
    attrName = 'dns_names'

    def getValue(self, obj):
        names = getattr(obj, self.attrName)
        return names[0] if names else ''

    def getSortKey(self, item):
        return self.getValue(item)

    def getLinkURL(self, item):
        return self.request.route_url('admin', traverse=('sites', item.__name__, '@@details'))

    def getLinkContent(self, item):
        return self.getValue(item)


class SiteLicenseColumn(column.GetAttrColumn):

    weight = 1
    header = 'License'
    attrName = 'license'

    def getValue(self, obj):
        return 'trial' if ITrialLicense.providedBy(obj.license) else 'enterprise'


class SiteStatusColumn(column.GetAttrColumn):
    
    weight = 2
    header = 'Status'
    attrName = 'status'


class SiteCreatedColumn(CreatedColumn):

    weight = 4


class SiteDeleteColumn(DeleteColumn):

    weight = 6


class DashboardTrialSitesTable(BaseSitesTable):

    def __init__(self, context, request):
        super(DashboardTrialSitesTable, self).__init__(context, request)
        self._current_time = datetime.datetime.utcnow()

    @Lazy
    def _raw_filter(self):
        return lambda x: ITrialLicense.providedBy(x.license) and x.status == SITE_STATUS_ACTIVE


class SiteAgeColumn(column.Column):

    weight = 6
    header = 'Site Age (days)'

    def renderCell(self, item):
        return (self.table._current_time - item.created).days


class DashboardRenewalsTable(BaseSitesTable):

    def __init__(self, context, request):
        super(DashboardRenewalsTable, self).__init__(context, request)
        self._current_time = datetime.datetime.utcnow()

    @Lazy
    def _raw_filter(self):
        return lambda x: x.status == SITE_STATUS_ACTIVE


class SiteURLAliasColumn(SiteURLColumn):

    weight = 1
    header = 'Site Alias'

    def getValue(self, obj):
        names = getattr(obj, self.attrName)
        return names[1] if len(names) > 1 else ''


class SiteRenewalDateColumn(column.Column):

    weight = 3
    header = 'License Renewal Date'

    def renderCell(self, item):
        value = item.license.end_date
        return formatDateToLocal(value)


class SiteDaysToRenewColumn(column.Column):

    weight = 4
    header = 'Days to Renewal'

    def renderCell(self, item):
        return (item.license.end_date - self.table._current_time).days
