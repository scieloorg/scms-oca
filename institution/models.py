from django.db import models
from django.utils.translation import gettext as _
from modelcluster.models import ClusterableModel
from wagtail.admin.edit_handlers import FieldPanel, InlinePanel

from core.models import CommonControlField
from location.models import Location

from . import choices
from .forms import InstitutionForm


class Institution(CommonControlField, ClusterableModel):
    name = models.CharField(_("Name"), max_length=255, null=True, blank=True)
    institution_type = models.CharField(_("Institution Type"), choices=choices.inst_type,
                                        max_length=255, null=True, blank=True)

    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL)
    panels = [
        FieldPanel('name'),
        FieldPanel('institution_type'),
        FieldPanel('location'),
    ]

    def __unicode__(self):
        return u'%s - %s: %s' % (self.name, _('Location'), self.location)

    def __str__(self):
        return u'%s - %s: %s' % (self.name, _('Location'), self.location)

    @classmethod
    def get_or_create(cls, inst_name, location_country, location_region,
                      location_state, location_city, user):

        # Institution
        # check if exists the institution
        if cls.objects.filter(name=inst_name).exists():
            return cls.objects.get(name=inst_name)
        else:
            institution = cls()
            institution.name = inst_name
            institution.creator = user

            institution.location = Location.get_or_create(location_country,
                                                          location_region,
                                                          location_state,
                                                          location_city,
                                                          user)

            institution.save()
        return institution

    base_form_class = InstitutionForm