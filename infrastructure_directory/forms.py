from wagtail.admin.forms import WagtailAdminModelForm

from infrastructure_directory.search_indexes import InfraStrutureIndex


class InfrastructureDirectoryForm(WagtailAdminModelForm):

    def save_all(self, user):
        structure_directory = super().save(commit=False)

        if self.instance.pk is not None:
            structure_directory.updated_by = user
        else:
            structure_directory.creator = user

        self.save()

        # Update de index.
        InfraStrutureIndex().update_object(instance=structure_directory)

        return structure_directory


class InfrastructureDirectoryFileForm(WagtailAdminModelForm):

    def save_all(self, user):
        structure_directory_file = super().save(commit=False)

        if self.instance.pk is not None:
            structure_directory_file.updated_by = user
        else:
            structure_directory_file.creator = user

        self.save()

        return structure_directory_file
