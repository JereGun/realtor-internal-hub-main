from django.shortcuts import render

def home(request):
    return render(request, 'public/home.html')

def about(request):
    return render(request, 'public/about.html')

def properties(request):
    return render(request, 'public/properties.html')

def agents(request):
    return render(request, 'public/agents.html')
