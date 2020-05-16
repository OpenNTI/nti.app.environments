from nti.app.environments.models.utils import get_sites_folder

from . import evolve_context

logger = __import__('logging').getLogger(__name__)

generation = 1

def migrate_site_license(site):
    site._p_activate()
    license = site.__dict__.pop('license', None)
    if license is not None:
        site.license = license
        assert license.__parent__ == site

def do_evolve(context, generation=generation):
    with evolve_context(context, generation) as root:
        sites = get_sites_folder(root)
        count = 0
        for sid in sites:
            migrate_site_license(sites[sid])
            count += 1
        logger.info('Migrated license for %i sites', count)
        

def evolve(context):
    """
    Evolve generation 1 by removing all index data
    """
    do_evolve(context)
