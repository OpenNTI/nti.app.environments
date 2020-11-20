from .client import PendoV1Client

PENDO_USAGE_TOTAL_SITE_ADMIN_COUNT = 'usagetotalsiteadmincount'
PENDO_USAGE_TOTAL_INSTRUCTOR_COUNT = 'usagetotalinstructorcount'
PENDO_USAGE_TOTAL_USER_COUNT = 'usagetotalusercount'
PENDO_USAGE_TOTAL_COURSE_COUNT = 'usagetotalcoursecount'
PENDO_USAGE_TOTAL_SCORM_PACKAGE_COUNT = 'usagetotalscormpackagecount'

PENDO_SITE_STATUS = 'sitestatus'
PENDO_SITE_LICENSE_TYPE = 'sitelicensetype'
PENDO_SITE_LICENSE_FREQUENCY = 'sitelicensefrequency'
PENDO_SITE_LICENSE_SEATS = 'sitelicenseseats'
PENDO_SITE_LICENSE_INSTRUCTOR_ADDON_SEATS = 'sitelicenseinstructoraddonseats'
PENDO_SITE_TRIAL_ENDDATE = 'sitetrialenddate'

def make_pendo_client(key):
    return PendoV1Client(key)

def serialize_datetime(datetime):
    return datetime.isoformat()
