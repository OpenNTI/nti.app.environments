from zope import interface
from zope import component

from zope.publisher.interfaces.browser import IBrowserRequest

from zope.traversing.browser.interfaces import IAbsoluteURL

from z3c.table import column
from z3c.table import header
from z3c.table import value
from z3c.table import table
from z3c.table import batch

from z3c.table.interfaces import ITable
from z3c.table.interfaces import IBatchProvider


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

    _request_args = ['%(prefix)s-sortOn', '%(prefix)s-sortOrder', 'email']


class BaseTable(table.Table):

    cssClasses = {'table':'table',
                  'thead':'thead',
                  'tbody':'tbody',
                  'th':'th',
                  'tr':'tr',
                  'td':'td'}

    batchSize = 5
    startBatchingAt = 5

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


class EmailColumn(column.EMailColumn):

    weight = 1
    header = 'Email'
    attrName = 'email'
    linkCSS = "email"


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
        return value.strftime('%Y-%m-%dT%H:%M:%SZ') if value else ''

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


class DetailColumn(column.LinkColumn):

    weight = 6
    header = ''
    linkContent = 'details'

    def getLinkURL(self, item):
        return self.request.route_url('admin', traverse=('customers', item.__name__, '@@details'))


class DeleteColumn(column.Column):

    weight = 7
    buttonTitle = 'Delete'

    def renderCell(self, item):
        template = """<button onclick="openDeletingModal('{url}', '{id}');">Delete</button>"""
        return  template.format(url=self.request.resource_url(item),
                                id=item.__name__)


class CustomersTable(BaseTable):
    pass


class CustomerColumnHeader(header.SortingColumnHeader):

    _request_args = ['email']


class ValuesForCustomersTable(value.ValuesForContainer):

    def _get_filter(self, name, params):
        value = params.get(name) or ''
        return value.strip()

    def _predicate(self, item, email):
        return email in item.email.lower()

    @property
    def values(self):
        params = self.request.params
        email = self._get_filter('email', params)
        return self.context.values() if not email \
                         else [x for x in self.context.values() if self._predicate(x, email.lower())]


class SitesTable(BaseTable):

    def __init__(self, context, request, **kwargs):
        super(SitesTable, self).__init__(context, request)
        self._email = kwargs.get('email')

    @property
    def values(self):
        if self._email:
            return [x for x in self.context.values() if x.owner.email == self._email]
        return self.context.values()


class SiteColumnHeader(header.SortingColumnHeader):
    pass


class SiteOwnerUsernameColumn(column.GetAttrColumn):

    weight = 1
    header = 'OwnerUsername'
    attrName = 'owner_username'


class SiteStatusColumn(column.GetAttrColumn):
    
    weight = 1
    header = 'status'
    attrName = 'status'


class SiteCreatedColumn(CreatedColumn):

    weight = 4


class SiteDetailColumn(column.LinkColumn):

    weight = 5
    header = ''
    linkContent = 'view'

    def getLinkURL(self, item):
        return self.request.route_url('admin', traverse=('sites', item.__name__, '@@details'))


class SiteDeleteColumn(DeleteColumn):

    weight = 6
