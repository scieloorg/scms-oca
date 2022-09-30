from django.shortcuts import render
from django.utils.translation import gettext as _


def show_graph(request):
    context = {
        'indicator_index_url': request.META.get('HTTP_REFERER'),
        'report_title': 'Nome do indicador',
        'report_subtitle': 'Nome do gráfico',
    }
    return render(
        request=request,
        template_name='modeladmin/indicator/indicator/graph.html',
        context=context,
    )
