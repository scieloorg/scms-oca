from django.shortcuts import render
from .models import Chart


def chart(request):
    chart_label = request.POST.get('chart_label', None)
    menu_scope = request.GET.get('menu_scope', None)
    
    charts = Chart.objects.filter(menu_scope=menu_scope)
    context = {
        'charts': charts,       
    }   


    if chart_label:
        context['selected_chart'] = Chart.objects.filter(label=chart_label, menu_scope=menu_scope).first()
    else:
        context['selected_chart'] = Chart.objects.filter(menu_scope=menu_scope).first()

    return render(request, "chart/chart.html", context)  
