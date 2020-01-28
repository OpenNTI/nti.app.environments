from zope import component
from zope import interface

from nti.externalization.interfaces import IInternalObjectExternalizer

from nti.externalization.datastructures import InterfaceObjectIO

from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import IHost


SITE_FIELDS_EXTERNAL_FOR_ADMIN_ONLY = ('environment', )


@component.adapter(ILMSSite)
@interface.implementer(IInternalObjectExternalizer)
class SiteExternalizer(InterfaceObjectIO):

    _ext_iface_upper_bound = ILMSSite

    _excluded_out_ivars_ = frozenset(
        getattr(InterfaceObjectIO,'_excluded_out_ivars_').union(
            {*SITE_FIELDS_EXTERNAL_FOR_ADMIN_ONLY,})
    )

    def toExternalObject(self, **kwargs):
        context = self._ext_replacement()
        result = super(SiteExternalizer, self).toExternalObject(**kwargs)
        if 'id' not in result:
            result['id'] = context.id

        result['parent_site'] = getattr(context.parent_site, 'id', None)
        return result


@component.adapter(IHost)
@interface.implementer(IInternalObjectExternalizer)
class HostExternalizer(InterfaceObjectIO):

    _ext_iface_upper_bound = IHost

    def toExternalObject(self, **kwargs):
        context = self._ext_replacement()
        result = super(HostExternalizer, self).toExternalObject(**kwargs)
        if 'current_load' not in result:
            result['current_load'] = context.current_load
        if 'id' not in result:
            result['id'] = context.id
        return result
