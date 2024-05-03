
from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import TemplateView, ListView
from django import forms
from django.shortcuts import redirect
from django.http import HttpResponse, HttpResponseRedirect

#TODO - major unkludge
import sys
sys.path.append('/home/ben/ner-takehome')
from src.database import Neo4jDatabase
import os

def index(request):
    if request.method == 'POST':
        db_choice = request.POST.get('db_choice')
        if db_choice == 'llama':
            return HttpResponseRedirect('search_llama/')
        elif db_choice == 'flair':
            return HttpResponseRedirect('search_flair/')
        else:
            return HttpResponseRedirect('bad/')
    else:
        db_form = DBForm()
        return render(request, 'radio_select.html', {"form":db_form})


class SearchForm(forms.Form):
    firm_name = forms.CharField(label='Firm Name', max_length=280)

class DBForm(forms.Form):
    CHOICES = [
        ('llama', 'LLaMA Database'),
        ('flair', 'Flair + Babel Database'),
    ]
    db_choice = forms.ChoiceField(label='Database',
        widget=forms.RadioSelect,
        choices=CHOICES,
    )

def search_llama(request):
    URI = "neo4j://10.249.64.7"
    AUTH = ("neo4j", "[big_secret]")
    db = Neo4jDatabase(URI, AUTH)
    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            firm_name = form.cleaned_data['firm_name']
            person_list, article_list = db.search_firm(firm_name)
            return render(request, "search_results.html", {'person_list':person_list, 'article_list':article_list})
    else:
        form = SearchForm()
    return render(request, 'search_form_llama.html', {"form":form})


def search_flair(request):
    URI = "neo4j://10.249.64.11"
    AUTH = ("neo4j", "[big_secret]")
    db = Neo4jDatabase(URI, AUTH)
    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            firm_name = form.cleaned_data['firm_name']
            person_list, article_list = db.search_firm(firm_name)
            return render(request, "search_results.html", {'person_list':person_list, 'article_list':article_list})
    else:
        form = SearchForm()
    return render(request, 'search_form_flair.html', {"form":form})
