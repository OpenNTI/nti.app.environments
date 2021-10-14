from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from zope.cachedescriptors.property import Lazy

from nti.app.environments.auth import ACT_LIST
from nti.app.environments.auth import ACT_READ
from nti.app.environments.auth import ACT_UPDATE
from nti.app.environments.auth import ACT_CREATE
from nti.app.environments.auth import ACT_DELETE

from nti.app.environments.models.interfaces import IHost
from nti.app.environments.models.interfaces import IHostsContainer
from nti.app.environments.models.interfaces import SITE_STATUS_OPTIONS

from nti.app.environments.models.utils import get_sites_folder

from nti.app.environments.common import formatDateToLocal

from nti.app.environments.views.base import BaseView
from nti.app.environments.views.base import BaseTemplateView
from nti.app.environments.views.base import TableViewMixin
from nti.app.environments.views.base import ObjectCreateUpdateViewMixin
from nti.app.environments.views.utils import raise_json_error
from nti.app.environments.views._table_utils import make_specific_table
from nti.app.environments.views._table_utils import SitesForHostTable
from nti.app.environments.views._table_utils import HostsTable

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT
LINKS = StandardExternalFields.LINKS

from nti.traversal.traversal import find_interface


logger = __import__('logging').getLogger(__name__)


class _HostViewMixin(object):

    @Lazy
    def _hosts_folder(self):
        return find_interface(self.context, IHostsContainer)

    def _get_host_by_name(self, host_name):
        # When the hosts are very large, this will become slow,
        # and we probably need other solutions.
        for x in self._hosts_folder.values():
            if x.host_name == host_name:
                return x


@view_config(renderer='../templates/admin/hosts.pt',
             request_method='GET',
             permission=ACT_READ,
             context=IHostsContainer,
             name="list")
class HostsListView(BaseTemplateView, TableViewMixin):

    def __call__(self):
        table = make_specific_table(HostsTable, self.context, self.request)
        return {'table': table,
                'creation_url': self.request.resource_url(self.context) if self.request.has_permission(ACT_CREATE, self.context) else None,
                'is_deletion_allowed': self._is_deletion_allowed(table)}


@view_config(renderer='../templates/admin/host_detail.pt',
             request_method='GET',
             permission=ACT_READ,
             context=IHost,
             name="details")
class HostDetailView(BaseTemplateView, TableViewMixin):

    def __call__(self):
        sites = get_sites_folder(self._onboarding_root)
        table = make_specific_table(SitesForHostTable, sites, self.request, host=self.context)
        return {'hosts_list_link': self.request.resource_url(self.context.__parent__, '@@list'),
                'host': self.context,
                'site_status_options': SITE_STATUS_OPTIONS,
                'table': table,
                'format_date': formatDateToLocal}

@view_defaults(renderer='rest')
class HostsListJSONView(BaseView):

    @view_config(request_method='GET',
                 permission=ACT_READ,
                 context=IHost)
    def get_host(self):
        return self.context

    @view_config(request_method='GET',
                 permission=ACT_LIST,
                 context=IHostsContainer)
    def list_hosts(self):
        result = LocatedExternalDict()
        result.__parent__ = self.context.__parent__
        result.__name__ = self.context.__name__
        result[ITEMS] = [x for x in self.context.values()]
        result[ITEM_COUNT] = result[TOTAL] = len(self.context)
        return result

@view_config(renderer='rest',
             request_method='POST',
             permission=ACT_CREATE,
             context=IHostsContainer)
class HostCreationView(BaseView, ObjectCreateUpdateViewMixin, _HostViewMixin):

    def __call__(self):
        host = self.createObjectWithExternal()
        if self._get_host_by_name(host.host_name):
            raise_json_error(hexc.HTTPConflict,
                             "Existing host: %s." % host.host_name)
        self.context.addHost(host)
        self.request.response.status = 201
        logger.info("%s created a new host, host id: %s, name: %s.",
                    self.request.authenticated_userid,
                    host.id,
                    host.host_name)
        return host


@view_config(renderer='rest',
             request_method='PUT',
             permission=ACT_UPDATE,
             context=IHost)
class HostUpdateView(BaseView, ObjectCreateUpdateViewMixin, _HostViewMixin):

    def readInput(self):
        params = super(HostUpdateView, self).readInput()
        if      'host_name' in params \
            and params['host_name'] != self.context.host_name \
            and isinstance(params['host_name'], str):
            host = self._get_host_by_name(params['host_name'])
            if host:
                raise_json_error(hexc.HTTPConflict,
                             "Existing host: %s." % params['host_name'])
        return params

    def __call__(self):
        self.updateObjectWithExternal(self.context)
        return self.context


@view_config(renderer='rest',
             request_method='DELETE',
             permission=ACT_DELETE,
             context=IHost)
class HostDeletionView(BaseView):

    def __call__(self):
        if self.context.current_load > 0:
            raise_json_error(hexc.HTTPForbidden,
                             'Removing host is forbidden, there are sites running on this host.')

        folder = self.context.__parent__
        folder.deleteHost(self.context)
        return hexc.HTTPNoContent()
