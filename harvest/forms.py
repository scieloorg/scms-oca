from pathlib import Path

from django import forms
from django.utils.translation import gettext_lazy as _
from wagtail.admin.forms import WagtailAdminModelForm

from .upload_indexing import SUPPORTED_EXTENSIONS


class TransformationScriptForm(WagtailAdminModelForm):
    def save_all(self, user):
        obj = super().save(commit=False)

        if self.instance.pk is not None:
            obj.updated_by = user
        else:
            obj.creator = user

        self.save()

        return obj


class HarvestOpenSearchUploadForm(forms.Form):
    file = forms.FileField(
        label=_("Arquivo CSV ou XLSX"),
        help_text=_("Envie um arquivo .csv ou .xlsx para indexar no OpenSearch."),
    )

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        extension = Path(uploaded_file.name).suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise forms.ValidationError(_("Envie um arquivo com extensão .csv ou .xlsx."))
        if uploaded_file.size == 0:
            raise forms.ValidationError(_("O arquivo enviado está vazio."))
        return uploaded_file
