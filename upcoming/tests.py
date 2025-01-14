from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.utils.timezone import now, make_aware
from datetime import datetime, timedelta
from django.conf import settings

from events.models import Event
from upcoming.forms import UpcomingEventsForm
from upcoming.views import (
    UpcomingEventsView,
    get_day_events_info,
    get_week_events_info,
    get_month_events_info,
    get_list_view_events_info,
    filter_events_by_filter_list,
    get_view_title_by_time_type,
)


class UpcomingEventsViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            first_name="Test",
            last_name="User",
            username="testuser",
            email="testuser@example.com",
            password="password123"
        )
        self.factory = RequestFactory()
        settings.STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

        self.event = Event.objects.create(
            title="Test Event",
            description="This is a test event.",
            start_time=make_aware(datetime(2024, 12, 1, 10, 0, 0)),
            end_time=make_aware(datetime(2024, 12, 1, 12, 0, 0)),
            creator=self.user
        )



    def test_get_day_events_info(self):
        events_info = get_day_events_info([self.event], self.user, now())
        self.assertEqual(len(events_info), 23)
        self.assertIn(self.event.title, [e['title'] for slot in events_info.values() for e in slot[1]])

    def test_get_week_events_info(self):
        start_time = make_aware(datetime(2024, 11, 30))  # Start on the Saturday before the event
        week_events = get_week_events_info([self.event], self.user, start_time)
        formatted_event_day = self.event.start_time.strftime("%m/%d")
        self.assertIn(formatted_event_day, week_events)
        self.assertEqual(len(week_events[formatted_event_day]), 1)


    def test_get_month_events_info(self):
        start_time = now().replace(day=1)
        events_info = get_month_events_info([self.event], start_time)
        event_found = any(
            self.event.title in [event['title'] for event in day_info[1] if isinstance(event, dict)]
            for week in events_info for day_info in week if isinstance(day_info, list)
        )
        self.assertTrue(event_found, "The event title was not found in the monthly events info.")

    def test_get_list_view_events_info(self):
        events_info = get_list_view_events_info([self.event], self.user)
        self.assertEqual(len(events_info), 1)
        self.assertEqual(events_info[0]['title'], self.event.title)

    def test_filter_events_by_filter_list_my_created(self):
        form = UpcomingEventsForm(initial={'filter_type': 'my_created'})
        events_query = Event.objects.all()
        filtered_events = filter_events_by_filter_list(events_query, self.user, form)
        self.assertIn(self.event, filtered_events)

    def test_get_view_authenticated_user(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get('/upcoming/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')

    def test_post_valid_form(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.post('/upcoming/', {
            'view_type': 'calendar',
            'filter_type': 'all',
            'time_type': 'week',
            'start_time': now().strftime('%Y-%m-%d')
        })
        self.assertEqual(response.status_code, 200)

    def test_post_invalid_form(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.post('/upcoming/', {
            'view_type': 'invalid',
            'filter_type': 'invalid',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Upcoming Events:')

    def test_redirect_anonymous_user(self):
        request = self.factory.get('/upcoming/')
        request.user = AnonymousUser()
        response = UpcomingEventsView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')