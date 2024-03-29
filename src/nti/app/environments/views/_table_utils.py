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

from nti.app.environments.auth import ACT_DELETE, ACT_UPDATE

from nti.app.environments.models.interfaces import ITrialLicense
from nti.app.environments.models.interfaces import IDedicatedEnvironment
from nti.app.environments.models.interfaces import IRestrictedLicense
from nti.app.environments.models.interfaces import ISiteUsage
from nti.app.environments.models.interfaces import SITE_STATUS_ACTIVE
from nti.app.environments.models.interfaces import SITE_STATUS_OPTIONS

from nti.app.environments.stripe.interfaces import IStripeSubscription

from nti.app.environments.common import formatDateToLocal


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

    _request_args = ['%(prefix)s-sortOn', '%(prefix)s-sortOrder', 'search', 'role_name', 'filterBy']


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

    @Lazy
    def _raw_values(self):
        return self.context.values()


def make_specific_table(tableClassName, container, request, **kwargs):
    the_table = tableClassName(container, IBrowserRequest(request), **kwargs)
    try:
        the_table.update()
    except IndexError:
        the_table.batchStart = len(the_table.rows) - the_table.getBatchSize()
        the_table.update()

    return the_table

class DefaultColumnHeader(header.SortingColumnHeader):

    _request_args = ['search']


class EmailColumn(column.LinkColumn):

    weight = 1
    header = 'Email'

    def getLinkURL(self, item):
        return self.request.resource_url(item, '@@details')

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

    def _get_value(self, item):
        return getattr(item, self.attrName)

    def getValue(self, item):
        value = self._get_value(item)
        return formatDateToLocal(value, '%Y-%m-%d') if value is not None else ''

    def getSortKey(self, item):
        value = self._get_value(item)
        return formatDateToLocal(value) if value is not None else ''


class LastVerifiedColumn(BaseDateColumn):

    weight = 4
    header = 'LastVerified'
    attrName = 'last_verified'


class CreatedColumn(BaseDateColumn):

    weight = 5
    header = 'Created Time'
    attrName = 'createdTime'


class LastModifiedColumn(BaseDateColumn):

    weight = 6
    header = 'Last Modified'
    attrName = 'lastModified'


class DeleteColumn(column.Column):

    weight = 7
    buttonTitle = 'Delete'
    cssClasses = {'td': 'nti_delete',
                  'th': 'nti_delete'}

    def _has_permission(self, item):
        return self.request.has_permission(ACT_DELETE, item)

    def renderCell(self, item):
        if self._has_permission(item):
            template = """<button onclick="openDeletingModal('{url}', '{id}');">Delete</button>"""
            return  template.format(url=self.request.resource_url(item),
                                    id=item.__name__)
        return ''


class CustomersTable(BaseTable):
    pass


class CustomerColumnHeader(header.SortingColumnHeader):

    _request_args = ['search']


class _FilterMixin(object):

    def _get_filter(self, name, params, lowercase=True):
        value = params[name].strip() if params.get(name) else ''
        if lowercase and value:
            value = value.lower()
        return value

    def _get_filter_by(self, params, _allow_fields=(), _normalize={}, _filter={}):
        value = self._get_filter('filterBy', params, False)
        if value:
            value = value.split(";")
            value = [x.split("=") for x in value]
            result = []
            for x in value:
                if len(x) >= 2 and x[0] in _allow_fields and x[1]:
                    filter_name = x[0]
                    filter_value = _normalize[filter_name](x[1]) if _normalize.get(filter_name) else x[1]
                    filter_func = _filter[filter_name]
                    result.append((filter_name, filter_value, filter_func))
            return result or None
        return value or None

    def _apply_filter_by(self, item, filterBy):
        for _name, value, _filter in filterBy or ():
            if not _filter(item, value):
                return False
        return True


class ValuesForCustomersTable(value.ValuesForContainer, _FilterMixin):

    def _predicate(self, item, term):
        """
        Search on email, name and hubspot id.
        """
        if term in item.email.lower() \
            or (item.name and term in item.name.lower()) \
            or (item.hubspot_contact and term in item.hubspot_contact.contact_vid):
            return True
        return False

    @property
    def values(self):
        params = self.request.params
        term = self._get_filter('search', params)
        return self.context.values() if not term else [x for x in self.context.values() if self._predicate(x, term)]


# Sites table

class BaseSitesTable(BaseTable, _FilterMixin):

    _raw_filter = None

    @Lazy
    def _raw_values(self):
        if self._raw_filter:
            return [x for x in self.context.values() if self._raw_filter(x)]
        return [x for x in self.context.values()]

    def _predicate(self, item, term):
        if term in item.id.lower():
            return True
        for dns in item.dns_names:
            if term in dns.lower():
                return True
        return False

    def _normalize_setup_state(self, state):
        if state:
            state = state.split(',')
            state = [x for x in state if x in ('pending', 'failed', 'success', 'none')]
        return state

    def _normalize_status(self, status):
        if status:
            status = status.split(',')
            status = [x for x in status if x in SITE_STATUS_OPTIONS]
        return status

    def _normalize_license_type(self, license_type):
        if license_type:
            license_type = license_type.split(',')
            license_type = [x for x in license_type if x in ('trial', 'starter', 'growth', 'enterprise', 'none')]
        return license_type

    def _filter_by_setup_state(self, item, state):
        current = 'none' if not item.setup_state else item.setup_state.state_name
        return current in state

    def _filter_by_status(self, item, status):
        return item.status in status

    def _filter_by_license_type(self, item, license_type):
        current = 'none'
        try:
            current = item.license.license_name
        except AttributeError:
            pass
        return current.lower() in license_type

    @property
    def values(self):
        params = self.request.params
        term = self._get_filter('search', params)
        filterBy = self._get_filter_by(params,
                                       _allow_fields=('setup_state', 'status', 'license_type'),
                                       _normalize={'setup_state': self._normalize_setup_state,
                                                   'license_type': self._normalize_license_type,
                                                   'status': self._normalize_status},
                                       _filter={'setup_state': self._filter_by_setup_state,
                                                'license_type': self._filter_by_license_type,
                                                'status': self._filter_by_status})

        result = self._raw_values
        if filterBy:
            result = [x for x in result if self._apply_filter_by(x, filterBy)]
        if term:
            result = [x for x in result if self._predicate(x, term)]
        return result


class SitesTable(BaseSitesTable):

    def __init__(self, context, request, **kwargs):
        super(SitesTable, self).__init__(context, request)
        self._email = kwargs.get('email')

    @Lazy
    def _raw_filter(self):
        if self._email:
            return lambda x: x.owner and x.owner.email == self._email


class SiteColumnHeader(header.SortingColumnHeader):

    _request_args = ['search', 'filterBy']


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
        return self.request.resource_url(item, '@@details')

    def getLinkContent(self, item):
        return self.getValue(item)

class SiteOwnerColumn(EmailColumn):

    weight = 1
    header = 'Owner'

    def getLinkURL(self, item):
        return super(SiteOwnerColumn, self).getLinkURL(item.owner)

    def getLinkContent(self, item):
        return super(SiteOwnerColumn, self).getLinkContent(item.owner)

class SiteBillingColumn(column.LinkColumn):

    weight = 2
    header = 'Billing'
    attrName = 'billing'

    def getValue(self, obj):
        sub = IStripeSubscription(obj, None)
        return sub.id if sub and sub.id else ''

    def getSortKey(self, item):
        return self.getValue(item)

    def getLinkURL(self, item):
        sub = self.getValue(item)
        return f'https://dashboard.stripe.com/subscriptions/{sub}' if sub else ''

    def getLinkContent(self, item):
        return self.getValue(item)


class SiteLicenseColumn(column.GetAttrColumn):

    weight = 1
    header = 'License'
    attrName = 'license'

    def getValue(self, obj):
        license_dn = [obj.license.license_name]

        if IRestrictedLicense.providedBy(obj.license):
            license_dn.append(obj.license.frequency)

        return ' - '.join(license_dn)


class SiteStatusColumn(column.GetAttrColumn):

    weight = 2
    header = 'Status'
    attrName = 'status'


class SiteSetupStateColumn(column.GetAttrColumn):

    weight = 3
    header = 'Setup State'
    attrName = 'setup_state'

    def getValue(self, obj):
        return obj.setup_state.state_name if obj.setup_state else ''

class SiteUsageAttrColumn(column.GetAttrColumn):

    weight = 5

    def getValue(self, obj):
        res = super(SiteUsageAttrColumn, self).getValue(ISiteUsage(obj))
        if res is None:
            return ''
        return res

    def getSortKey(self, item):
        try:
            return int(self.getValue(item))
        except ValueError:
            return -1


class SiteUsageAdminColumn(SiteUsageAttrColumn):

    attrName = 'admin_count'

    header = 'Admins'


    def renderCell(self, item):
        usage = ISiteUsage(item).admin_count
        try:
            limit = item.license.seats
        except AttributeError:
            limit = '∞'
        return f'{usage} / {limit}'

class SiteUsageInstructorColumn(SiteUsageAttrColumn):

    attrName = 'instructor_count'

    header = 'Instructors'

    def renderCell(self, item):
        usage = ISiteUsage(item).instructor_count
        try:
            limit = item.license.additional_instructor_seats
        except AttributeError:
            limit = '∞'

        if limit == None:
            limit = 0
        
        return f'{usage} / {limit}'

class SiteUsageScormColumn(SiteUsageAttrColumn):

    attrName = 'scorm_package_count'

    header = 'Scorm'

    weight = 7

    def renderCell(self, item):
        usage = ISiteUsage(item).scorm_package_count or 0
        try:
            limit = item.license.max_scorm_packages
        except AttributeError:
            limit = '∞'

        if limit == None:
            limit = 0
        
        return f'{usage} / {limit}'

class SiteLicenseAlertColumn(column.Column):

    weight = 10

    def renderCell(self, item):
        alerts = self.table.alerts
        issues = alerts[item.id]['Issues']
        return '<br/>'.join(issues)

    def renderHeadCell(self):
        return 'Issues'


class SiteCreatedColumn(CreatedColumn):

    weight = 8


class SiteLicenseEndDateColumn(BaseDateColumn):

    weight = 9
    header = 'End Date'

    def _get_value(self, item):
        return getattr(item.license, 'end_date', None)


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


class DashboardTrialSiteLicenseEndDateColumn(SiteLicenseEndDateColumn):

    weight = 7


class DashboardRenewalsTable(BaseSitesTable):

    def __init__(self, context, request):
        super(DashboardRenewalsTable, self).__init__(context, request)
        self._current_time = datetime.datetime.utcnow()

    @Lazy
    def _raw_filter(self):
        return lambda x: bool(not ITrialLicense.providedBy(x.license) \
                              and x.status == SITE_STATUS_ACTIVE)


class DashboardLicenseAuditTable(BaseSitesTable):

    def __init__(self, context, request, alerts={}):
        super(DashboardLicenseAuditTable, self).__init__(context, request)
        self.alerts = alerts

    @Lazy
    def _raw_values(self):
        return [self.context[k] for k in self.alerts]


class SiteURLAliasColumn(SiteURLColumn):

    weight = 1
    header = 'Site Alias'

    def getValue(self, obj):
        names = getattr(obj, self.attrName)
        return names[1] if len(names) > 1 else ''


class SiteRenewalDateColumn(BaseDateColumn):

    weight = 3
    header = 'License Renewal Date'

    def _get_value(self, item):
        return getattr(item.license, 'end_date', None)


class SiteDaysToRenewColumn(column.Column):

    weight = 4
    header = 'Days to Renewal'

    def renderCell(self, item):
        license = item.license
        return (license.end_date - self.table._current_time).days if license.end_date else ''

    def getSortKey(self, item):
        rendered = self.renderCell(item)
        return rendered or -1


class RolePrincipalsTable(BaseTable, _FilterMixin):

    def _predicate(self, item, email):
        return email in item.lower()

    @property
    def values(self):
        params = self.request.params
        email = self._get_filter('search', params)
        return self.context if not email else [x for x in self.context if self._predicate(x, email)]


class RolePricipalsColumnHeader(header.SortingColumnHeader):

    _request_args = ['search', 'role_name']


class PrincipalColumn(column.Column):

    weight = 0
    header = 'Email'

    def renderCell(self, item):
        return item or ''

class PrincipalDeleteColumn(column.Column):

    weight = 2
    cssClasses = {'td': 'nti_delete',
                  'th': 'nti_delete'}

    def renderCell(self, item):
        role_name = self.request.params['role_name'] or ''
        template = """<button onclick="openDeletingModal('{url}', '{email}');">Delete</button>"""
        return  template.format(url=self.request.route_url('roles', traverse=('@@remove',), _query=(('role_name', role_name),
                                                                                                    ('email', item))),
                                email=item)


class HostsTable(BaseTable, _FilterMixin):

    def _predicate(self, item, term):
        return term in item.id.lower() or term in item.host_name.lower()

    @property
    def values(self):
        params = self.request.params
        term = self._get_filter('search', params)
        return self.context.values() if not term else [x for x in self.context.values() if self._predicate(x, term)]


class HostNameColumn(column.LinkColumn):

    weight = 0
    header = 'Host'
    attrName = 'host_name'

    cssClasses = {'td': 'host'}

    def getValue(self, obj):
        return getattr(obj, self.attrName)

    def getSortKey(self, item):
        return self.getValue(item)

    def getLinkURL(self, item):
        return self.request.resource_url(item, '@@details')

    def getLinkContent(self, item):
        return self.getValue(item)


class HostCapacityColumn(column.GetAttrColumn):

    weight = 1
    header = 'Capacity'
    attrName = 'capacity'

    cssClasses = {'td': 'capacity'}

    def renderCell(self, item):
        return getattr(item, self.attrName) or 0


class HostCurrentLoadColumn(column.GetAttrColumn):

    weight = 2
    header = 'Current Load'
    attrName = 'current_load'

    def renderCell(self, item):
        return getattr(item, self.attrName) or 0


class HostCreatedColumn(CreatedColumn):

    weight = 3


class HostLastModifiedColumn(LastModifiedColumn):

    weight = 4


class HostDeleteColumn(DeleteColumn):

    weight = 5

    def _has_edit_permission(self, item):
        return self.request.has_permission(ACT_UPDATE, item)

    def _has_delete_permission(self, item):
        return super(HostDeleteColumn, self)._has_permission(item) and item.current_load == 0

    def renderCell(self, item):
        content = ''
        url=self.request.resource_url(item)
        if self._has_edit_permission(item):
            content += """<button onclick="openEditingModal(this,'{url}');">Edit</button>""".format(url=url)
        if self._has_delete_permission(item):
            content += """<button onclick="openDeletingModal('{url}', '{name}');" style="margin-left: 5px;">Delete</button>""".format(url=url,name=item.host_name)
        return content


# sites table running on host.


class SitesForHostTable(SitesTable):

    def __init__(self, context, request, **kwargs):
        super(SitesForHostTable, self).__init__(context, request)
        self._host = kwargs.get('host')

    @Lazy
    def _raw_filter(self):
        if self._host:
            return lambda x: IDedicatedEnvironment.providedBy(x.environment) and x.environment.host == self._host


class SiteHostLoadColumn(column.GetAttrColumn):

    weight = 8
    header = 'Load'

    def getValue(self, obj):
        return obj.environment.load_factor
