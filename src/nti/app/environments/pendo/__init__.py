from .client import PendoV1Client

PENDO_USAGE_TOTAL_SITE_ADMIN_COUNT = 'usagetotalsiteadmincount'
PENDO_USAGE_TOTAL_INSTRUCTOR_COUNT = 'usagetotalinstructorcount'
PENDO_USAGE_TOTAL_USER_COUNT = 'usagetotalusercount'
PENDO_USAGE_TOTAL_COURSE_COUNT = 'usagetotalcoursecount'
PENDO_USAGE_TOTAL_SCORM_PACKAGE_COUNT = 'usagetotalscormpackagecount'
PENDO_USAGE_USED_LICENSE_COUNT = 'usageusedlicensecount'

def make_pendo_client(key):
    return PendoV1Client(key)
