import pytz
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django import forms
from django.views import View
from django.views.generic import FormView

from friend.models import Friend
from organizations.models import Organization
from search.forms import SearchForm
from events.models import Event, EventParticipant
from myaccount.models import User
from datetime import datetime, time, timedelta
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from zoneinfo import ZoneInfo
from django.db.models import Q, OuterRef, Subquery

class OrganizationEventView(View):
    template_name = "search/organization_search.html"

    def get(self, request):
        self.redirect_to_home_if_not_authenticated(request)

        organizations = self.get_organizations(name="", creator_username="")

        return render(request, self.template_name, context= {
            "organizations": organizations
        })

    def post(self, request):
        self.redirect_to_home_if_not_authenticated(request)

        # Handle search for organization by name or creator username
        name = ""
        creator_username = ""
        if request.POST.get("name") is not None:
            name = request.POST.get("name")
        if request.POST.get("creator_username") is not None:
            creator_username = request.POST.get("creator_username")

        organizations = self.get_organizations(name=name, creator_username=creator_username)
        return render(request, self.template_name, context= {
            "organizations": organizations, "name": name, "creator_username": creator_username
        })

    def redirect_to_home_if_not_authenticated(self, request):
        if not request.user.is_authenticated:
            return redirect('/')

    def get_organizations(self, name, creator_username):
        organizations = Organization.objects

        if name is not None:
            organizations = organizations.filter(name__icontains=name)

        if creator_username is not None:
            organizations = organizations.filter(creator__username__icontains=creator_username)

        # Format for template
        organizations_formatted = []
        for organization in organizations:
            organizations_formatted.append({
                'name': organization.name,
                'pk': organization.pk,
                'creator': organization.creator
            })
        return organizations_formatted

class SearchEventView(View):
    template_name = "search/event_search.html"

    def get(self, request):
        initial = {'start_time': datetime.now(), 'page_number': 1}
        events = get_all_events_after_today()
        return self.get_search_view(
            request,
            SearchForm(initial=initial),
            events,
            "Upcoming events:"
        )

    def get_search_view(self, request, form, events, search_title):
        # Filter by start time
        events = events.order_by('start_time')

        # Get page number
        page_number = form.initial.get('page_number', 1)

        # Get events within the first 10 entries and get the total number of events that matched the criteria
        events_in_range, total_event_count = only_get_events_on_page(events, page_number)

        # Convert the events into event information for the template
        events_information = get_events_information_from_events(events_in_range, request.user)

        # Calculate the highest possible page to display given the number of events
        highest_page = total_event_count // 10 + (0 if ((total_event_count % 10) == 0) else 1)
        if highest_page == 0:
            highest_page = 1
        if page_number > highest_page:
            form.initial['page_number'] = 1

        return render(request, self.template_name, {
            "form": form, "search_title": search_title, "events": events_information,
            "total_event_count": total_event_count, "highest_page": highest_page
        })

    def post(self, request):
        form = SearchForm(request.POST)
        if form.is_valid():
            # Handle next page button pressed
            page_number = int(form.cleaned_data['page_number'])
            if 'next' in request.POST:
                page_number = page_number + 1
            # Handle previous page button pressed
            elif 'prev' in request.POST:
                page_number = page_number - 1
            # Handle search button pressed
            elif 'search' in request.POST:
                page_number = 1

            # Clean form data
            cleaned_data = {
                'title': form.cleaned_data['title'],
                'creator': form.cleaned_data['creator'],
                'start_time': form.cleaned_data['start_time'],
                'end_time': form.cleaned_data['end_time'],
                'only_my_invited_events': form.cleaned_data['only_my_invited_events'],
                'only_my_accepted_events': form.cleaned_data['only_my_accepted_events'],
                'only_my_friends_accepted': form.cleaned_data['only_my_friends_accepted'],
                'only_my_events': form.cleaned_data['only_my_events'],
                'only_recurring_events': form.cleaned_data['only_recurring_events'],
                'page_number': page_number,
            }

            # Create new form using old form data and search with this new form
            events = get_searched_events_from_form(form=form, user=request.user)
            form = SearchForm(initial=cleaned_data)
            return self.get_search_view(request, form, events, "Search Results:")
        else:
            # Something went wrong, which shouldn't happen, but display error just in case.
            print("Error in Search form:")
            print(form.errors)
            # Return to initial search page as error occurred
            return self.get(request)


def get_searched_events_from_form(form, user):
    query_set = Event.objects.all()

    # Filter by text data
    query_set = filter_by_text_forms(form, query_set)

    # Filter by check list data
    query_set = filter_by_boolean_forms(form, user, query_set)

    return query_set


def filter_by_boolean_forms(form, user, query_set):
    # Filter only my events
    cleaned_only_my_events = form.cleaned_data['only_my_events']
    if cleaned_only_my_events is not None and cleaned_only_my_events is True and user.is_authenticated:
        query_set = query_set.filter(creator=user)

    # Filter recurring events
    cleaned_only_recurring_events = form.cleaned_data['only_recurring_events']
    if cleaned_only_recurring_events is not None and cleaned_only_recurring_events is True and user.is_authenticated:
        query_set = query_set.filter(is_recurring=True)

    # Filter invited events
    cleaned_only_my_invited_events = form.cleaned_data['only_my_invited_events']
    if cleaned_only_my_invited_events is not None and cleaned_only_my_invited_events is True and user.is_authenticated:
        # Filter by only invited events
        user_invited_events = (EventParticipant.objects.filter(user=user)
                               .filter(approved=True)
                               .filter(status='Invited')
                               .filter(event__in=query_set))
        # Construct list of PK to filter by invited events
        participants = []
        for event_participants in user_invited_events:
            participants.append(event_participants.event.pk)
        # Filter by PK
        query_set = query_set.filter(pk__in=participants)

    # Filter accepted events
    cleaned_only_my_accepted_events = form.cleaned_data['only_my_accepted_events']
    if cleaned_only_my_accepted_events is not None and cleaned_only_my_accepted_events is True and user.is_authenticated:
        # Filter by only accepted events
        user_accepted_events = (EventParticipant.objects
                                .filter(user=user)
                                .filter(approved=True)
                                .filter(status='Confirmed')
                                .filter(event__in=query_set))
        # Construct list of PK to filter by accepted events
        participants = []
        for event_participants in user_accepted_events:
            participants.append(event_participants.event.pk)
        # Filter by PK
        query_set = query_set.filter(pk__in=participants)

    # Filter friends accepted events
    cleaned_only_my_friends_accepted = form.cleaned_data['only_my_friends_accepted']
    if cleaned_only_my_friends_accepted is not None and cleaned_only_my_friends_accepted is True and user.is_authenticated:
        # Get query set of accepted friends
        friends_query_set = (Friend.objects.filter(from_user=user).filter(status=Friend.STATUS_ACCEPTED))

        # Get friends pk
        friends_pk = []
        for friend in friends_query_set:
            friends_pk.append(friend.to_user.pk)

        # Get list of event participants that include friends
        participants = (EventParticipant.objects.filter(status="Confirmed")
                                                .filter(event__in=query_set)
                                                .filter(user__in=friends_pk))

        # Construct list of PK to filter by accepted events
        participants_events_pk = []
        for participant in participants:
            participants_events_pk.append(participant.event.pk)

        # Filter list of events if creator is a friend or if is confirmed event participant
        query_set = query_set.filter(Q(creator__pk__in=friends_pk) | Q(pk__in=participants_events_pk))

    return query_set


def filter_by_text_forms(form, query_set):
    # Filter Start time
    cleaned_start_time = form.cleaned_data['start_time']
    if cleaned_start_time is not None and cleaned_start_time != "":
        query_set = query_set.filter(start_time__gt=cleaned_start_time)

    # Filter End time
    cleaned_end_time = form.cleaned_data['end_time']
    if cleaned_end_time is not None and cleaned_end_time != "":
        query_set = query_set.filter(start_time__lt=cleaned_end_time)

    # Filter title
    cleaned_title = form.cleaned_data['title']
    if cleaned_title is not None and cleaned_title != "":
        query_set = query_set.filter(title__icontains=cleaned_title)

    # Filter Creator
    cleaned_creator = form.cleaned_data['creator']
    if cleaned_creator is not None and cleaned_creator != "":
        query_set = query_set.filter(creator__username__icontains=cleaned_creator)

    return query_set


def get_events_information_from_events(events, user):
    events_information = []
    for event in events:
        # If info is too long, only display the start of the information
        title = event.title
        if len(title) > 25:
            title = title[:25] + "..."
        description = event.description
        if len(description) > 50:
            description = description[:50] + "..."
        creator = event.creator.username
        if len(creator) > 25:
            creator = creator[:25] + "..."

        event_information = {
            "title": title,
            "description": description,
            "creator": creator,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "pk": event.pk
        }
        if user.is_authenticated and user.role != 2:
            event_information["status"] = get_participant_information(event, user)
        events_information.append(event_information)
    return events_information


def get_participant_information(event, user):
    if event.creator.username == user.username:
        return "My event"

    try:
        # Attempt to get the record by ID
        participant = EventParticipant.objects.get(event=event, user=user)
        status = str(participant.status).lower()
        if status == "denied":
            return "Denied"
        if participant.approved and status == "invited":
            return "Invited"
        if participant.approved and status == "confirmed":
            return "Going"
        if (not participant.approved) and status == "invited":
            return "Requested"
        if participant.approved and status == "maybe":
            return "Might go"

        # Should not happen
        return "Error"
    except ObjectDoesNotExist:
        # If the participant is not in event, set to nothing
        return ""


def get_all_events_after_today():
    # Get events that start today
    time_zone = pytz.timezone('America/New_York')
    datetime_as_time_zone = time_zone.localize(datetime.now())
    return Event.objects.filter(start_time__gt=datetime_as_time_zone)


def only_get_events_on_page(query_set, page_number):
    #
    # NOTE: This function should only be called when your query set is small,
    #       otherwise it will cause a lot of database usage which uses up our tokens for Heroku.
    #
    total_query_count = query_set.count()

    # If empty, return nothing
    if total_query_count == 0:
        return query_set, total_query_count

    # Get indices to splice events by
    start_index_inclusive = (page_number - 1) * 10
    end_index_inclusive = (page_number * 10) - 1

    # Avoid start index going out of bounds
    if start_index_inclusive >= total_query_count:
        return query_set[:total_query_count], total_query_count

    # Avoid end index going out of bounds
    if end_index_inclusive >= total_query_count:
        return query_set[start_index_inclusive:end_index_inclusive + 1], total_query_count

    # Return slice as it is within the total count
    return query_set[start_index_inclusive:end_index_inclusive + 1], total_query_count
