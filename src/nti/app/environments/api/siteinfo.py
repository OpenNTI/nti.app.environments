import requests

logger = __import__('logging').getLogger(__name__)

SITE_URL = 'https://{host_name}'
SITE_INFO_TPL = 'https://{host_name}/dataserver2/SiteBrand'
SITE_LOGO_TPL = 'https://{host_name}{uri}'


class NTClient(object):

    def __init__(self):
        self.session = requests.Session()

    def _logo_url(self, resp):
        assets = resp['assets']
        login_logo = assets.get('login_logo') if assets else None
        return login_logo['href'] if login_logo else None

    def fetch_site_info(self, host_name):
        try:
            logger.info("Fetching site info: {}.".format(host_name))
            url = SITE_INFO_TPL.format(host_name=host_name)
            resp = self.session.get(url, timeout=(5, 5))
            if resp.status_code != 200:
                logger.warn("Bad request. status code: %s.", resp.status_code)
                return None

            resp = resp.json()
            uri = self._logo_url(resp)
            logo_url = SITE_LOGO_TPL.format(host_name=host_name,uri=uri) if uri else None
            return {'logo_url': logo_url,
                    'brand_name': resp['brand_name'],
                    'site_url': SITE_URL.format(host_name=host_name)}
        except requests.exceptions.ConnectionError:
            logger.exception("Unknown site host.")
            return None


nt_client = NTClient()
