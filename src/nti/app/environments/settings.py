GOOGLE_CLIENT_ID = None
GOOGLE_CLIENT_SECRET = None
HUBSPOT_API_KEY = None
HUBSPOT_PORTAL_ID = None


def init_app_settings(settings):
    global GOOGLE_CLIENT_ID
    global GOOGLE_CLIENT_SECRET
    global HUBSPOT_API_KEY
    global HUBSPOT_PORTAL_ID

    GOOGLE_CLIENT_ID = settings['google_client_id']
    GOOGLE_CLIENT_SECRET = settings['google_client_secret']
    HUBSPOT_API_KEY = settings['hubspot_api_key']
    HUBSPOT_PORTAL_ID = settings['hubspot_portal_id']
