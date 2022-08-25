from wagtail.admin.forms import WagtailAdminModelForm


class CityForm(WagtailAdminModelForm):

    def save_all(self, user):
        city = super().save(commit=False)

        if self.instance.pk is not None:
            city.updated_by = user
        else:
            city.creator = user

        self.save()

        return city


class StateForm(WagtailAdminModelForm):

    def save_all(self, user):
        state = super().save(commit=False)

        if self.instance.pk is not None:
            state.updated_by = user
        else:
            state.creator = user

        self.save()

        return state


class CountryForm(WagtailAdminModelForm):

    def save_all(self, user):
        country = super().save(commit=False)

        if self.instance.pk is not None:
            country.updated_by = user
        else:
            country.creator = user

        self.save()

        return country

class ThematicAreaForm(WagtailAdminModelForm):

    def save_all(self, user):
        thematic = super().save(commit=False)

        if self.instance.pk is not None:
            thematic.updated_by = user
        else:
            thematic.creator = user

        self.save()

        return thematic

class PracticeForm(WagtailAdminModelForm):

    def save_all(self, user):
        pratice = super().save(commit=False)

        if self.instance.pk is not None:
            pratice.updated_by = user
        else:
            pratice.creator = user

        self.save()

        return pratice

class ActionForm(WagtailAdminModelForm):

    def save_all(self, user):
        action = super().save(commit=False)

        if self.instance.pk is not None:
            action.updated_by = user
        else:
            action.creator = user

        self.save()

        return action
