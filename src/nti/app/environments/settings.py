GOOGLE_CLIENT_ID = None
GOOGLE_CLIENT_SECRET = None


def init_app_settings(settings):
    global GOOGLE_CLIENT_ID
    global GOOGLE_CLIENT_SECRET

    GOOGLE_CLIENT_ID = settings['google_client_id']
    GOOGLE_CLIENT_SECRET = settings['google_client_secret']
