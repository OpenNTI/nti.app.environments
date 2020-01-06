from zope import component
from zope import interface

from nti.externalization.interfaces import IInternalObjectUpdater

from nti.externalization.datastructures import InterfaceObjectIO

from nti.app.environments.models.interfaces import ILMSSite


@component.adapter(ILMSSite)
@interface.implementer(IInternalObjectUpdater)
class SiteInternalizer(InterfaceObjectIO):

    _ext_iface_upper_bound = ILMSSite

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        updated = False
        if 'id' in parsed:
            self._ext_self.id = parsed['id']
            updated = True

        if 'created' in parsed:
            self._ext_self.created = parsed['created']
            updated = True

        result = super(SiteInternalizer, self).updateFromExternalObject(parsed, *args, **kwargs)
        return updated or result
