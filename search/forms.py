from django import forms
from datetime import datetime


class SearchForm(forms.Form):
    title = forms.CharField(max_length=200, required=False, initial="")
    creator = forms.CharField(max_length=200, required=False, initial="")
    start_time = forms.DateTimeField(initial=None, required=False, widget=forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local', 'style': 'outline: none; border: none; width: 100%; background-color: transparent;'}))
    end_time = forms.DateTimeField(initial=None, required=False, widget=forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local', 'style': 'outline: none; border: none; width: 100%; background-color: transparent;'}))
    only_my_invited_events = forms.BooleanField(initial=False, required=False, widget=forms.CheckboxInput())
    only_my_accepted_events = forms.BooleanField(initial=False, required=False, widget=forms.CheckboxInput())
    only_my_friends_accepted = forms.BooleanField(initial=False, required=False)
    only_my_events = forms.BooleanField(initial=False, required=False)
    only_recurring_events = forms.BooleanField(initial=False, required=False)
    page_number = forms.IntegerField(initial=1, required=False)
