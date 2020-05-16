"""
"""
import contextlib
from zope.app.publication.zopepublication import ZopePublication

from zope.generations.generations import SchemaManager

from ..models import OnboardingRoot
from ..models import ROOT_KEY
from ..models import CUSTOMERS
from ..models import SITES
from ..models import HOSTS

from ..models.customers import CustomersFolder
from ..models.sites import SitesFolder
from ..models.hosts import HostsFolder

generation = 1

logger = __import__('logging').getLogger(__name__)


class _EnvironmentSchemaManager(SchemaManager):
    """
    A schema manager that we can register as a utility in ZCML.
    """

    def __init__(self):
        super(_EnvironmentSchemaManager, self).__init__(
            generation=generation,
            minimum_generation=generation,
            package_name='nti.app.environments.generations')


def _install_customers(onboarding_root):
    if CUSTOMERS not in onboarding_root:
        customers = CustomersFolder()
        customers.__name__ = CUSTOMERS
        onboarding_root[CUSTOMERS] = customers
    return onboarding_root[CUSTOMERS]


def _install_sites(onboarding_root):
    if SITES not in onboarding_root:
        sites = SitesFolder()
        sites.__name__ = SITES
        onboarding_root[SITES] = sites
    return onboarding_root[SITES]


def _install_hosts(onboarding_root):
    if HOSTS not in onboarding_root:
        hosts = HostsFolder()
        hosts.__name__ = HOSTS
        onboarding_root[HOSTS] = hosts
    return onboarding_root[HOSTS]


def _install_root(zodb_root, key=ROOT_KEY):
    root = OnboardingRoot()

    _install_customers(root)
    _install_sites(root)
    _install_hosts(root)

    zodb_root[key] = root
    return root


def install_root_folders(context):
    logger.info('Installing root folders via schema manager')
    root_folder = context.connection.root()[ZopePublication.root_name]
    _install_root(root_folder)

def evolve(context):
    install_root_folders(context)
    
