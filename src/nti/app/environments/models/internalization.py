from zope import component
from zope import interface

from nti.externalization.interfaces import IInternalObjectUpdater

from nti.externalization.datastructures import InterfaceObjectIO

from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ITrialLicense
from nti.app.environments.models.interfaces import IEnterpriseLicense

from nti.app.environments.utils import parseDate


def _parse_date(value):
    return parseDate(value) if isinstance(value, str) else value


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
            parsed['created'] = _parse_date(parsed.get('created'))
            self._ext_self.created = parsed['created']
            updated = True

        result = super(SiteInternalizer, self).updateFromExternalObject(parsed, *args, **kwargs)
        return updated or result


class _BaseLicenseInternalizer(InterfaceObjectIO):

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        for attr_name in ('start_date', 'end_date'):
            if attr_name in parsed:
                parsed[attr_name] = _parse_date(parsed[attr_name])

        result = super(_BaseLicenseInternalizer, self).updateFromExternalObject(parsed, *args, **kwargs)
        return result


@component.adapter(ITrialLicense)
@interface.implementer(IInternalObjectUpdater)
class TrialLicenseInternalizer(_BaseLicenseInternalizer):

    _ext_iface_upper_bound = ITrialLicense


@component.adapter(IEnterpriseLicense)
@interface.implementer(IInternalObjectUpdater)
class EnterpriseLicenseInternalizer(_BaseLicenseInternalizer):

    _ext_iface_upper_bound = IEnterpriseLicense
