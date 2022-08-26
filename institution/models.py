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

    acronym = models.CharField(_("Acronym to the institution"), blank=True, null=True, max_length=255)

    level_1 = models.CharField(_("Level 1 organization"), blank=True, null=True, max_length=255)

    level_2 = models.CharField(_("Level 2 organization"), blank=True, null=True, max_length=255)

    level_3 = models.CharField(_("Level 3 organization"), blank=True, null=True, max_length=255)

    url = models.URLField("url", blank=True, null=True)

    logo = models.ImageField(_("Logo"), blank=True, null=True)

    panels = [
        FieldPanel('name'),
        FieldPanel('acronym'),
        FieldPanel('institution_type'),
        FieldPanel('location'),
        FieldPanel('level_1'),
        FieldPanel('level_2'),
        FieldPanel('level_3'),
        FieldPanel('url'),
        FieldPanel('logo'),
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

            institution.location = Location.get_or_create(user,
                                                          location_country,
                                                          location_region,
                                                          location_state,
                                                          location_city)

            institution.save()
        return institution

    base_form_class = InstitutionForm
