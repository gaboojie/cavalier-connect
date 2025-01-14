import re
from django import forms
from events.models import Event, EventFile, EventParticipant, Organization
from myaccount.models import User
from django.core.exceptions import ObjectDoesNotExist


class CreateEventForm(forms.Form):
    title = forms.CharField(max_length=200)
    description = forms.CharField()
    location = forms.CharField(max_length=200, required=False)
    start_time = forms.DateTimeField()
    end_time = forms.DateTimeField()
    # Recurrence Section
    is_recurring = forms.BooleanField(required=False)
    recurrence_frequency = forms.ChoiceField(
        choices=[
            ('', 'Repeats:'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly'),
        ],
        required=False
    )
    recurrence_end = forms.DateTimeField(required=False)
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time and end_time < start_time:
            self.add_error("time", "End time cannot be earlier than start time.")
            
        if cleaned_data.get('is_recurring'):
            recurrence_end = cleaned_data.get('recurrence_end')
            if recurrence_end and recurrence_end < start_time:
                self.add_error("time","Recurrence end date cannot be earlier than the event start time.")

        return cleaned_data



class EventInviteUserForm(forms.Form):
    username = forms.CharField()
    error = None

    def is_invite_valid(self, event):
        try:
            user = User.objects.get(username=self.username)

            # Cannot invite yourself case
            if user == event.creator:
                self.error = "Error: You cannot invite yourself to your own event!"
                return False

            # Cannot invite someone already invited
            participants = EventParticipant.objects.filter(event=event)
            for participant in participants:
                if participant.username == self.username:
                    self.error = f'Error: {self.username} is already invited!'
                    return False
        except ObjectDoesNotExist:
            self.error = 'Error: No user exists with username "' + self.username + '"!'
            return False

        return True


class UploadFileForm(forms.Form):
    file = forms.FileField()
    title = forms.CharField(max_length=100, required=True)
    description = forms.CharField(widget=forms.Textarea, required=False)
    keywords = forms.CharField(max_length=255, required=False)


class ApproveUserRequestForm(forms.Form):
    username = forms.CharField()
