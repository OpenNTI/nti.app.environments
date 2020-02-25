from pyramid.interfaces import IApplicationCreated
from zope import component

from .appserver import spawn_sites_setup_state_watchdog


@component.adapter(IApplicationCreated)
def _spawn_setup_state_watchdog(event):
    spawn_sites_setup_state_watchdog(event.app.registry)
