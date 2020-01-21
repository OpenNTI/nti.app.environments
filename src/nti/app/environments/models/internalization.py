from zope import component
from zope import interface

from nti.externalization.interfaces import IInternalObjectUpdater

from nti.externalization.datastructures import InterfaceObjectIO

from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ITrialLicense
from nti.app.environments.models.interfaces import IEnterpriseLicense
from nti.app.environments.models.interfaces import IDedicatedEnvironment
from nti.app.environments.models.interfaces import ISetupStateSuccess
from nti.app.environments.utils import parseDate


def _parse_date(value):
    return parseDate(value) if isinstance(value, str) else value


@component.adapter(ILMSSite)
@interface.implementer(IInternalObjectUpdater)
class SiteInternalizer(InterfaceObjectIO):

    _ext_iface_upper_bound = ILMSSite

    __external_oids__ = ('parent_site',)

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        updated = False
        if 'id' in parsed:
            self._ext_self.id = parsed['id']
            updated = True

        if 'parent_site' in parsed:
            self._ext_self.parent_site = parsed['parent_site']
            updated = True

        dns_names = parsed.get('dns_names')

        result = super(SiteInternalizer, self).updateFromExternalObject(parsed, *args, **kwargs)

        # Make sure we store dns_names in a list, and lower case all dns_names.
        # IO, by default will store in a set.
        if dns_names is not None:
            self._ext_self.dns_names = [x.lower() for x in dns_names]

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


@component.adapter(IDedicatedEnvironment)
@interface.implementer(IInternalObjectUpdater)
class DedicatedEnvironmentInternalizer(InterfaceObjectIO):

    _ext_iface_upper_bound = IDedicatedEnvironment

    __external_oids__ = ('host',)


@component.adapter(ISetupStateSuccess)
@interface.implementer(IInternalObjectUpdater)
class SetupStateSuccessInternalizer(InterfaceObjectIO):

    _ext_iface_upper_bound = ISetupStateSuccess

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        urls = parsed.get('urls')
        result = super(SetupStateSuccessInternalizer, self).updateFromExternalObject(parsed, *args, **kwargs)

        # Make sure we store urls in a list, and lower case all dns_names.
        # IO, by default will store in a set.
        if urls is not None:
            self._ext_self.urls = [x for x in urls]
            result = True

        return result
