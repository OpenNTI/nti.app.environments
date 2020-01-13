from zope import component
from zope import interface

from nti.externalization.interfaces import IInternalObjectExternalizer

from nti.externalization.datastructures import InterfaceObjectIO

from nti.app.environments.models.interfaces import ILMSSite


@component.adapter(ILMSSite)
@interface.implementer(IInternalObjectExternalizer)
class SiteExternalizer(InterfaceObjectIO):

    _ext_iface_upper_bound = ILMSSite

    def toExternalObject(self, **kwargs):
        context = self._ext_replacement()
        result = super(SiteExternalizer, self).toExternalObject(**kwargs)
        if 'id' not in result:
            result['id'] = context.id
        result['parent_site'] = getattr(context.parent_site, 'id', None)
        return result
