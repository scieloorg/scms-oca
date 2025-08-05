from django.db import models

class Chart(models.Model):
    CHART_TYPE_CHOICES = [
        ('iframe', 'Iframe'),
        ('image', 'Imagem'),
    ]

    title = models.CharField("Título", max_length=255, blank=True, null=True)
    label = models.CharField("Rótulo", max_length=255, blank=True, null=True)
    scope = models.CharField("Escopo", max_length=255, blank=True, null=True)
    chart_type = models.CharField("Tipo de Gráfico", choices=CHART_TYPE_CHOICES, max_length=10)
    iframe_url = models.TextField("URL do iframe", blank=True, null=True)
    image = models.ImageField("Imagem", upload_to="charts/images/", blank=True, null=True)
    data_zip = models.FileField("Arquivo ZIP com dados", upload_to="charts/zips/", blank=True, null=True)
    link_chart = models.CharField("Link", max_length=255, blank=True, null=True)
    menu_scope = models.CharField("Escopo do menu", max_length=255, blank=True, null=True)

    def __str__(self):
        return self.title or ""

    class Meta:
        verbose_name = "Gráfico"
        verbose_name_plural = "Gráficos"
