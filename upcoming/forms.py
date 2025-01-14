import pytz
from django import forms

UPCOMING_VIEW_TYPE_CHOICES = [
    ('list', "List View"),
    ('calendar', 'Calendar View')
]
UPCOMING_FILTER_TYPE_CHOICES = [
    ('all', 'Show my events'),
    ('my_created', 'Show my created events'),
    ('my_invited', 'Show my invited events'),
    ('my_accepted', 'Show my accepted events'),
    ('my_friends', "Show my friend(s) events"),
    ('my_recurring', 'Show my recurring events'),
]
UPCOMING_TIME_TYPE_CHOICES = [
    ('day', 'Day'),
    ('week', 'Week'),
    ('month', 'Month')
]


class UpcomingEventsForm(forms.Form):
    view_type = forms.ChoiceField(choices=UPCOMING_VIEW_TYPE_CHOICES, required=False)
    filter_type = forms.ChoiceField(choices=UPCOMING_FILTER_TYPE_CHOICES, required=False)
    time_type = forms.ChoiceField(choices=UPCOMING_TIME_TYPE_CHOICES, required=False)
    start_time = forms.DateTimeField()

    def clean_start_time(self):
        # Get the value from cleaned data
        cleaned = self.cleaned_data.get('start_time')

        # Define the time zone (you can also get it from settings or pass it dynamically)
        timezone_obj = pytz.timezone('America/New_York')

        # Convert to timezone-aware datetime if it's naive (i.e., without timezone info)
        if cleaned:
            if cleaned.tzinfo is None:
                # Make it timezone-aware by setting the time zone
                cleaned = cleaned.make_aware(cleaned, timezone_obj)

        return cleaned

