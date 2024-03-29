from nti.app.environments.subscriptions.sessions import CheckoutSessionStorage
from nti.app.environments.subscriptions.sessions import STRIPE_CHECKOUT_SESSIONS_KEY

from . import evolve_context

logger = __import__('logging').getLogger(__name__)

generation = 2

def install_stripe_sessions(root):
    if STRIPE_CHECKOUT_SESSIONS_KEY not in root:
        root[STRIPE_CHECKOUT_SESSIONS_KEY] = CheckoutSessionStorage()
        logger.info('Installed sessions container')
    else:
        logger.info('Sessions container already installed')
    

def do_evolve(context, generation=generation):
    with evolve_context(context, generation) as root:
        install_stripe_sessions(root)
        

def evolve(context):
    """
    Evolve generation 1 by removing all index data
    """
    do_evolve(context)
