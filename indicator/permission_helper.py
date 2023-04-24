from wagtail.contrib.modeladmin.helpers import PermissionHelper

MUST_BE_MODERATE = "must_be_moderate"


class IndicatorPermissionHelper(PermissionHelper):
    
    def must_be_moderate(self, user):
        return self.user_has_specific_permission(user, MUST_BE_MODERATE)
