import uuid

from pyramid.security import Allow
from pyramid.security import ALL_PERMISSIONS

from zope import interface

from zope.container.contained import Contained

from nti.property.property import alias
from nti.property.property import LazyOnClass

from nti.containers.containers import CaseInsensitiveCheckingLastModifiedBTreeContainer

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.schema.fieldproperty import createFieldProperties
from nti.schema.schema import SchemaConfigured

from nti.app.environments.auth import ADMIN_ROLE
from nti.app.environments.auth import ACT_READ
from nti.app.environments.auth import ACCOUNT_MANAGEMENT_ROLE

from nti.app.environments.models.interfaces import IHost
from nti.app.environments.models.interfaces import IHostsContainer
from nti.app.environments.models.interfaces import IDedicatedEnvironment

from nti.app.environments.models.utils import get_sites_folder


@interface.implementer(IHost)
class PersistentHost(SchemaConfigured, PersistentCreatedModDateTrackingObject, Contained):

    createFieldProperties(IHost)

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.host'

    id = alias('__name__')

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)

    _current_load = 0

    @property
    def current_load(self):
        return self._current_load

    def set_current_load(self, current_load):
        self._current_load = current_load

    def recompute_current_load(self, exclusive_site=None):
        _load = 0
        for site in get_sites_folder().values():
            if      site != exclusive_site \
                and IDedicatedEnvironment.providedBy(site.environment) \
                and site.environment.host == self:
                _load += site.environment.load_factor

        self.set_current_load(_load)
        return _load


@interface.implementer(IHostsContainer)
class HostsFolder(CaseInsensitiveCheckingLastModifiedBTreeContainer):

    @LazyOnClass
    def __acl__(self):
        return [(Allow, ADMIN_ROLE, ALL_PERMISSIONS),
                (Allow, ACCOUNT_MANAGEMENT_ROLE, ACT_READ)]

    def addHost(self, host):
        if host.id is None:
            host.id = _generate_host_id()
        self[host.id] = host
        return host

    def getHost(self, host_id):
        return self.get(host_id)

    def deleteHost(self, host):
        host_id = getattr(host, 'id', host)
        del self[host_id]


def _generate_host_id():
    return 'H' + uuid.uuid4().hex
