from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from django.utils.timezone import make_aware
from events.models import Event
from organizations.models import Organization
from friend.models import Friend
from search.views import OrganizationEventView, SearchEventView

class OrganizationViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            first_name="Test",
            last_name="User",
            username="testuser",
            email="testuser@example.com",
            password="password123"
        )
        self.organization = Organization.objects.create(
            name="Test Organization", creator=self.user
        )
        self.factory = RequestFactory()

    def test_get_authenticated_user(self):
        request = self.factory.get(reverse("search:organization-search"))
        request.user = self.user
        response = OrganizationEventView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.organization.name, str(response.content))

    def test_post_search_organization_by_name(self):
        request = self.factory.post(
            reverse("search:organization-search"), {"name": "Test"}
        )
        request.user = self.user
        response = OrganizationEventView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.organization.name, str(response.content))

    def test_post_search_organization_by_creator(self):
        request = self.factory.post(
            reverse("search:organization-search"), {"creator_username": "testuser"}
        )
        request.user = self.user
        response = OrganizationEventView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.organization.name, str(response.content))

class EventViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            first_name="Test",
            last_name="User",
            username="testuser",
            email="testuser@example.com",
            password="password123"
        )
        self.event = Event.objects.create(
            title="Test Event",
            description="This is a test event.",
            start_time=make_aware(datetime.now() + timedelta(days=1)),
            end_time=make_aware(datetime.now() + timedelta(days=1, hours=2)),
            creator=self.user,
        )
        self.factory = RequestFactory()

    def test_get_search_events(self):
        request = self.factory.get(reverse("search:search"))
        request.user = self.user
        response = SearchEventView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.event.title, str(response.content))

    def test_post_search_events_title(self):
        form_data = {"title": "Test Event", "page_number": 1}
        request = self.factory.post(reverse("search:search"), data=form_data)
        request.user = self.user
        response = SearchEventView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.event.title, str(response.content))
