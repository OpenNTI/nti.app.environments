from zope import interface

from zope import component

from zope.component import getGlobalSiteManager

from nti.environments.management.interfaces import ICeleryApp
from nti.environments.management.interfaces import ISettings

from nti.environments.management.celery import configure_celery

def includeme(config):
    """
    Creates and configures the celery application.

    The celery application is made available as utility
    registered as ICeleryApp
    """
    def _build_celery():
        app = configure_celery(settings=component.getUtility(ISettings))

        interface.alsoProvides(app, ICeleryApp)
        getGlobalSiteManager().registerUtility(app, ICeleryApp)
        app.finalize()

    config.action(("celery", "setup"), _build_celery)
