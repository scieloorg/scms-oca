from wagtail.admin.forms import WagtailAdminModelForm

from policy_directory.search_indexes import PolicyIndex


class PolicyDirectoryForm(WagtailAdminModelForm):
    def save_all(self, user):
        policy_direcotry = super().save(commit=False)

        if self.instance.pk is not None:
            policy_direcotry.updated_by = user
        else:
            policy_direcotry.creator = user

        self.save()

        # Update de index.
        PolicyIndex().update_object(instance=policy_direcotry)

        return policy_direcotry


class PolicyDirectoryFileForm(WagtailAdminModelForm):
    def save_all(self, user):
        policy_direcotry_file = super().save(commit=False)

        if self.instance.pk is not None:
            policy_direcotry_file.updated_by = user
        else:
            policy_direcotry_file.creator = user

        self.save()

        return policy_direcotry_file
