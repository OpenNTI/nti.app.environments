from pyramid.interfaces import IApplicationCreated
from zope import component

from .appserver import spawn_sites_setup_state_watchdog
from .appserver import spawn_site_invitation_code_status_watchdog


@component.adapter(IApplicationCreated)
def _spawn_setup_state_watchdog(event):
    spawn_sites_setup_state_watchdog(event.app.registry)


@component.adapter(IApplicationCreated)
def _spawn_invitation_status_watchdog(unused_event):
    spawn_site_invitation_code_status_watchdog()
