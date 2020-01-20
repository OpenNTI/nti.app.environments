from zope import interface

from zope.component import getGlobalSiteManager

from nti.environments.management.interfaces import ICeleryApp

from nti.environments.management.celery import configure_celery

def includeme(config):
    """
    Creates and configures the celery application.

    The celery application is made available as utility
    registered as ICeleryApp
    """

    app = configure_celery(settings=config.registry.settings)

    interface.alsoProvides(app, ICeleryApp)
    getGlobalSiteManager().registerUtility(app, ICeleryApp)

    config.action(("celery", "finalize"), app.finalize)
