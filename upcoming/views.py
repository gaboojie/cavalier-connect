import calendar
from datetime import datetime, timedelta, time

import pytz
from dateutil.relativedelta import relativedelta
from django.db.models import Q
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View

from events.models import Event, EventParticipant
from friend.models import Friend
from upcoming.forms import UpcomingEventsForm


class UpcomingEventsView(View):
    template_name = "upcoming/upcoming.html"

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/')
        redirect_to_landing_if_user_not_allowed(request)
        return self.get_view_from_form(request, get_initial_form(), "Upcoming Events:")

    def post(self, request):
        redirect_to_landing_if_user_not_allowed(request)
        form = UpcomingEventsForm(request.POST)
        if form.is_valid():
            form = get_new_form_from_post_request(request, form)
        else:
            print(f'User "{request.user.username}" submitted an upcoming event form that contained errors.')
            print(form.errors)
            form = get_initial_form()

        return self.get_view_from_form(request, form, "Upcoming Events:")

    def get_view_from_form(self, request, form, page_title):
        time_type = form.initial['time_type']
        start_time = form.initial['start_time']
        view_type = form.initial['view_type']

        view_title = get_view_title_by_time_type(time_type, start_time)
        events = get_events_from_form(request.user, form)

        if view_type == 'list':
            # Get events by list view
            events = get_list_view_events_info(events, request.user)
        else:
            # get events by calendar view
            if time_type == 'month':
                events = get_month_events_info(events, start_time)
            elif time_type == 'week':
                events = get_week_events_info(events, request.user, start_time)
            else:
                events = get_day_events_info(events, request.user, start_time)

        context = {
            "form": form,
            "events": events,
            "page_title": page_title,
            "view_title": view_title
        }

        return render(request, self.template_name, context)


def get_day_events_info(events, user, start_time):
    events_info = {}
    for i in range(1, 24):
        formatted_time = time(hour=i, minute=0).strftime("%I:%M %p")
        events_info[i] = [formatted_time, []]

    # Put events into their correct hour
    for event in events:
        vertical_offset = event.start_time.hour
        if vertical_offset in events_info:
            status = get_formatted_status(event, user)
            event_info = {
                'pk': event.pk,
                'title': event.title,
                'status': status,
                'start_time': event.start_time,
                'end_time': event.end_time,
                'creator': event.creator.username,
                'description': event.description
            }
            events_info[vertical_offset][1].append(event_info)

    return events_info


def get_week_events_info(events, user, start_time):
    events_info = {}

    # Add days to events_info
    for day in range(7):
        updated_time = start_time + timedelta(days=day)
        events_info[updated_time.strftime("%m/%d")] = []

    # Put events to events_info
    for event in events:
        formatted_event_time = event.start_time.strftime("%m/%d")
        if formatted_event_time in events_info:
            status = get_formatted_status(event, user)
            event_info = {
                'pk': event.pk,
                'status': status,
                'title': event.title,
                'creator': event.creator.username,
                'start_time': event.start_time
            }
            events_info[formatted_event_time].append(event_info)
        else:
            print("Error in /upcoming/views: an event that was picked up within the next week is not within the next week!")

    return events_info

def get_month_events_info(events, start_time):
    events_info = []

    # Calculate offset to make sure month lines up with Sunday first
    weekday_offset, days_in_month = calendar.monthrange(start_time.year, start_time.month)
    weekday_offset = (weekday_offset + 1) % 7

    # Add each weekday offset to events info
    for offset_day in range(weekday_offset):
        offset_day_info = ['None']
        events_info.append(offset_day_info)

    # Add each day to events info
    for day_num in range(1, days_in_month+1):
        day_info = [f'{day_num}', []]
        events_info.append(day_info)

    # Add each event to events info
    for event in events:
        day_on = event.start_time.day
        events_on_day = events_info[day_on-1+weekday_offset]
        events_on_day[1].append({'pk': event.pk, 'title': event.title})

    # Add additional days to make sure it is factorable by 7 (for each week)
    while (len(events_info) % 7) != 0:
        events_info.append(['None'])

    # Reformat events_info into week form
    events_info_in_week_form = []
    current_week = []
    for day in events_info:
        current_week.append(day)
        if len(current_week) == 7:
            events_info_in_week_form.append(current_week)
            current_week = []

    return events_info_in_week_form

def get_list_view_events_info(events, user):
    events_info = []
    for event in events:
        status = get_formatted_status(event, user)
        event_info = {
            'title': event.title,
            'creator': event.creator.username,
            'start_time': event.start_time,
            'status': status,
            'pk': event.pk
        }
        events_info.append(event_info)
    return events_info


def get_formatted_status(event, user):
    if event.creator == user:
        return "Creator"
    if user.is_anonymous:
        return "Not Participating"
    else:
        try:
            participant = EventParticipant.objects.get(user=user, event=event)
            status = participant.status
            approved = participant.approved
            if status == 'Invited' and approved is False:
                return "Requested"
            elif status == 'Confirmed' and approved is True:
                return "Going"
            elif status == 'Invited' and approved is True:
                return "Invited"
            elif status == 'Denied':
                return "Denied"
            elif status == 'Maybe':
                return "Maybe"

            return "Error"
        except EventParticipant.DoesNotExist:
            return "Not invited"


def copy_valid_form(upcoming_events_form):
    return UpcomingEventsForm(initial={
        'view_type': upcoming_events_form.cleaned_data['view_type'],
        'time_type': upcoming_events_form.cleaned_data['time_type'],
        'start_time': upcoming_events_form.cleaned_data['start_time'],
        'filter_type': upcoming_events_form.cleaned_data['filter_type']
    })


def get_new_form_from_post_request(request, old_form):
    new_form = copy_valid_form(old_form)
    time_type = new_form.initial['time_type']
    start_time = new_form.initial['start_time']
    if 'next' in request.POST:
        # Next page
        new_form.initial['start_time'] = get_next_start_time_by_time_type(time_type, start_time)
    elif 'prev' in request.POST:
        # Prev page
        new_form.initial['start_time'] = get_prev_start_time_by_time_type(time_type, start_time)
    elif 'filter_type' in request.POST:
        # Do nothing as the filter type was changed (we were just listening for a POST request).
        pass
    elif 'view_type' in request.POST:
        # Do nothing as the view type was changed (we were just listening for a POST request).
        pass
    elif 'time_type' in request.POST:
        # Do nothing as the time type was changed (we were just listening for a POST request).
        pass

    return new_form


def get_events_from_form(user, form):
    # Filter events by time
    events_query = get_events_query_by_datetime(form)

    # Filter events by filter list
    events_query = filter_events_by_filter_list(events_query, user, form)

    # Order by start_time
    return events_query.order_by('start_time')


def get_events_query_by_datetime(form):
    # Filter by [start time, end time]
    start_time = form.initial['start_time']
    end_time = get_end_time(form.initial['time_type'], form.initial['start_time'])
    return Event.objects.filter(start_time__gt=start_time, start_time__lt=end_time)


def filter_events_by_filter_list(events_query, user, form):
    filter_type = form.initial['filter_type']

    # Filter only my created events
    if filter_type == "my_created":
        events_query = events_query.filter(creator=user)

    # Filter only my invited events
    if filter_type == "my_invited":
        user_invited_events = (EventParticipant.objects.filter(user=user)
                               .filter(approved=True)
                               .filter(status='Invited')
                               .filter(event__in=events_query))
        # Construct list of PK to filter by invited events
        participants = []
        for event_participants in user_invited_events:
            participants.append(event_participants.event.pk)
        # Filter by PK
        events_query = events_query.filter(pk__in=participants)

    # Filter my accepted
    if filter_type == 'my_accepted':
        # Filter by only accepted events
        user_accepted_events = (EventParticipant.objects
                                .filter(user=user)
                                .filter(approved=True)
                                .filter(status='Confirmed')
                                .filter(event__in=events_query))
        # Construct list of PK to filter by accepted events
        participants = []
        for event_participants in user_accepted_events:
            participants.append(event_participants.event.pk)
        # Filter by PK
        events_query = events_query.filter(pk__in=participants)

    # Filter my friends
    if filter_type == "my_friends":
        # Get query set of accepted friends
        friends_query_set = (Friend.objects.filter(from_user=user).filter(status=Friend.STATUS_ACCEPTED))

        # Get friends pk
        friends_pk = []
        for friend in friends_query_set:
            friends_pk.append(friend.to_user.pk)

        # Get list of event participants that include friends
        participants = (EventParticipant.objects.filter(status="Confirmed")
                        .filter(event__in=events_query)
                        .filter(user__in=friends_pk))

        # Construct list of PK to filter by accepted events
        participants_events_pk = []
        for participant in participants:
            participants_events_pk.append(participant.event.pk)

        # Filter list of events if creator is a friend or if is confirmed event participant
        events_query = events_query.filter(Q(creator__pk__in=friends_pk) | Q(pk__in=participants_events_pk))

    # Filter by my recurring events
    if filter_type == "my_recurring":
        events_query = events_query.filter(is_recurring=True)

    return events_query


def get_view_title_by_time_type(time_type, time_to_use):
    time_type = time_type.lower()

    if time_type == 'month':
        formatted_month_year_date = time_to_use.strftime("%B %Y")
        page_title = f'Month of {formatted_month_year_date}'
    elif time_type == 'day':
        formatted_date = time_to_use.strftime('%B %d, %Y')
        page_title = f'Day of {formatted_date}'
    else:
        formatted_date = time_to_use.strftime('%B %d, %Y')
        page_title = f'Week of {formatted_date}'

    return page_title


def get_end_time(time_type, start_time):
    time_type = time_type.lower()
    time_zone = pytz.utc
    if time_type == 'day':
        end_time = datetime(start_time.year, start_time.month, start_time.day)
        end_time = time_zone.localize(end_time)
    elif time_type == 'month':
        # Get the number of days in the specified month
        _, last_day = calendar.monthrange(start_time.year, start_time.month)

        # Construct the last day of the month
        end_time = datetime(start_time.year, start_time.month, last_day)
        end_time = time_zone.localize(end_time)
    else:
        end_time = start_time + timedelta(days=6)

    # Update to last possible end time
    end_time = end_time.replace(hour=23, minute=59, second=59, microsecond=999999)

    return end_time

def get_next_start_time_by_time_type(time_type, start_time):
    time_type = time_type.lower()
    if time_type == 'day':
        return start_time + timedelta(days=1)
    elif time_type == 'month':
        return start_time + relativedelta(months=1)
    else:
        return start_time + timedelta(days=7)

def get_prev_start_time_by_time_type(time_type, start_time):
    time_type = time_type.lower()
    if time_type == 'day':
        return start_time - timedelta(days=1)
    elif time_type == 'month':
        return start_time - relativedelta(months=1)
    else:
        return start_time - timedelta(days=7)


def get_start_time_by_time_type(time_type, time_to_use):
    time_type = time_type.lower()
    time_zone = pytz.utc
    if time_to_use is None:
        # If the time_to_use was not specified, assume to start by the current time
        time_to_use = datetime.now()

    if time_type == 'day':
        # Get beginning of day so no change
        start_time = time_to_use
    elif time_type == 'month':
        # Get beginning of first day of month
        start_time = datetime(time_to_use.year, time_to_use.month, 1)
        #start_time = time_zone.localize(time_to_use)
    else:
        # Get beginning of first day as week (as default)
        start_time = time_to_use - timedelta(days=(time_to_use.weekday() + 1) % 7)


    # Return the beginning point of time for this day
    beginning_of_start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
    return beginning_of_start_time


def get_initial_form():
    start_time = get_start_time_by_time_type(time_type='week', time_to_use=None)
    return UpcomingEventsForm(initial={
        'view_type': 'calendar',
        'filter_type': 'all',
        'time_type': 'week',
        'start_time': start_time,
    })


def redirect_to_landing_if_user_not_allowed(request):
    user = request.user
    if not user.is_authenticated or user.role == 2:
        print("Permission Denied - Anonymous user tried to access upcoming events page without signing-in!")
        return redirect('/')
    if user.role == 2:
        print("Permission Denied - Admin tried to access upcoming events page!")
        return redirect('/')