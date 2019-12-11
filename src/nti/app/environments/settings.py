GOOGLE_CLIENT_ID = None
GOOGLE_CLIENT_SECRET = None
HUBSPOT_API_KEY = None


def init_app_settings(settings):
    global GOOGLE_CLIENT_ID
    global GOOGLE_CLIENT_SECRET
    global HUBSPOT_API_KEY

    GOOGLE_CLIENT_ID = settings['google_client_id']
    GOOGLE_CLIENT_SECRET = settings['google_client_secret']
    HUBSPOT_API_KEY = settings['hubspot_api_key']
