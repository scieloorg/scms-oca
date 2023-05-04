from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.views import CreateView, EditView

from core import tasks
from core_settings.models import Moderation

from .permission_helper import IndicatorPermissionHelper


class IndicatorDirectoryEditView(EditView):
    def get_moderation(self):
        if Moderation.objects.filter(model=self.model.__name__, status=True).exists():
            return Moderation.objects.get(model=self.model.__name__)

    @property
    def must_moderate(self):
        # if user is a staff must no moderate
        if self.request.user.is_staff:
            return False

        return IndicatorPermissionHelper(model=self.model).must_be_moderate(
            self.request.user
        )

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)

        # check if have moderation and if the record_status is diferent from ``PUBLISHED``
        if self.must_moderate and self.object.record_status != "PUBLISHED":
            if self.get_moderation():
                # fix the status to ``TO MODERATE``
                self.object.record_status = "TO MODERATE"
                self.object.save()

        return HttpResponseRedirect(self.get_success_url())


class IndicatorDirectoryCreateView(CreateView):
    def get_moderation(self):
        # check if exists a moderation and if is enabled
        if Moderation.objects.filter(model=self.model.__name__, status=True).exists():
            return Moderation.objects.get(model=self.model.__name__)

    @property
    def must_moderate(self):
        if self.get_moderation():
            # if user is a staff must no moderate
            if self.request.user.is_staff:
                return False

            return IndicatorPermissionHelper(model=self.model).must_be_moderate(
                self.request.user
            )

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)

        # check if have moderation
        if self.must_moderate:
            moderation = self.get_moderation()

            if moderation:
                # fix the status to ``TO MODERATE``
                self.object.record_status = "TO MODERATE"
                self.object.save()

                # check if must send e-mail
                if moderation.send_mail:
                    # get user
                    user_email = self.get_moderation().moderator.email or None
                    # get group
                    group_mails = [
                        user.email
                        for user in self.get_moderation().group_moderator.user_set.all()
                        if user.email
                    ]
                    tasks.send_mail(
                        _(
                            "Novo conteúdo para moderação - %s"
                            % self.model._meta.verbose_name.title()
                        ),
                        render_to_string(
                            "email/moderate_email.html",
                            {
                                "obj": self.object,
                                "user": self.request.user,
                                "request": self.request,
                            },
                        ),
                        to_list=[user_email],
                        bcc_list=group_mails,
                        html=True,
                    )

        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_moderation"] = self.must_moderate
        return context
