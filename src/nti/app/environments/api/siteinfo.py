import requests

logger = __import__('logging').getLogger(__name__)

SITE_ENDPOINT_TPL = 'https://{host_name}/dataserver2/SiteBrand'
SITE_LOGO_TPL = 'https://{host_name}{uri}'


class NTClient(object):

    def __init__(self):
        self.session = requests.Session()

    def fetch_site_info(self, host_name):
        try:
            url = SITE_ENDPOINT_TPL.format(host_name=host_name)
            resp = self.session.get(url)
            if resp.status_code != 200:
                logger.warn("Bad request. status code: %s.", resp.status_code)
                return None

            resp = resp.json()
            logo_url = SITE_LOGO_TPL.format(host_name=host_name,
                                            uri=resp['assets']['login_logo']['href'])
            return {'logo_url': logo_url}
        except requests.exceptions.ConnectionError:
            logger.exception("Unknown site host.")
            return None


nt_client = NTClient()
