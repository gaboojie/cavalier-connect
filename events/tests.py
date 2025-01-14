from django.test import TestCase
from django.test import Client
from events.models import Event, EventParticipant, EventFile, Comment
from events.views import create_recurrence
from myaccount.models import User
from organizations.models import Organization, OrganizationMember
from datetime import datetime, timedelta
from django.urls import reverse
from django.utils.timezone import make_aware
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch


#class EventModelTest(TestCase):

    # def setUp(self):
    #     self.user = User.objects.create(first_name="First", last_name="Last", student_id="test", date_of_birth=datetime.datetime.now())
    #
    # def test_event_can_be_not_recurring(self):
    #     event = Event.objects.create(title="Title", description="Description", location="Location",
    #                                  start_time=datetime.datetime.now(tz=timezone.utc), end_time=datetime.datetime.now(tz=timezone.utc), creator=self.user)
    #     event.save()
    #     self.assertEqual(event.is_recurring, False)
    #
    # def test_event_is_recurring(self):
    #     event = Event.objects.create(title="Title", description="Description", location="Location",
    #                                  start_time=datetime.datetime.now(tz=timezone.utc), end_time=datetime.datetime.now(tz=timezone.utc), creator=self.user, is_recurring=True)
    #     event.save()
    #     self.assertEqual(event.is_recurring, True)

class EventViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.creator = User.objects.create_user(
            first_name="Event",
            last_name="Creator",
            email="creator@example.com",
            password="password123",
            role=1
        )

        self.participant = User.objects.create_user(
            first_name="Event",
            last_name="Participant",
            email="participant@example.com",
            password="password123",
            role=1
        )

        self.non_participant = User.objects.create_user(
            first_name="Non",
            last_name="Participant",
            email="nonparticipant@example.com",
            password="password123",
            role=1
        )

        self.pma = User.objects.create_user(
            first_name="PMA",
            last_name="Admin",
            email="pma@example.com",
            password="password123",
            role=2
        )

        self.event = Event.objects.create(
            title="Test Event",
            description="This is a test event",
            location="Test Location",
            start_time=make_aware(datetime.now() + timedelta(days=1)),
            end_time=make_aware(datetime.now() + timedelta(days=1, hours=2)),
            creator=self.creator,
            is_recurring=False
        )

        #Add participant
        EventParticipant.objects.create(
            event=self.event,
            user=self.participant,
            status="Confirmed",
            approved=True
        )

        #Make organization
        self.organization = Organization.objects.create(
            name="Test Organization",
            creator=self.creator
        )
        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.creator
        )

    def test_event_view_accessible_to_creator(self):
        self.client.login(email="creator@example.com", password="password123")
        response = self.client.get(reverse("events:view_event", args=[self.event.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "events/view_event.html")

    def test_event_view_accessible_to_participant(self):
        self.client.login(email="participant@example.com", password="password123")
        response = self.client.get(reverse("events:view_event", args=[self.event.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "events/view_event.html")

    def test_event_view_inaccessible_to_non_participant(self):
        self.client.login(email="nonparticipant@example.com", password="password123")
        response = self.client.get(reverse("events:view_event", args=[self.event.pk]))
        self.assertEqual(response.status_code, 200)

    def test_event_view_redirects_anonymous_user(self):
        response = self.client.get(reverse("events:view_event", args=[self.event.pk]))
        self.assertEqual(response.status_code, 200)

    def test_event_delete_future_occurrences(self):
        recurrence_end = make_aware(datetime.now() + timedelta(days=10))
        self.recurring_event = Event.objects.create(
            title="Recurring Event",
            description="This is a recurring event",
            location="Test Location",
            start_time=make_aware(datetime.now() + timedelta(days=1)),
            end_time=make_aware(datetime.now() + timedelta(days=1, hours=2)),
            creator=self.creator,
            is_recurring=True,
            recurrence_frequency="daily",
            recurrence_end=recurrence_end
        )

        create_recurrence(
            self.recurring_event,
            recurrence_frequency="daily",
            recurrence_end=recurrence_end
        )

        future_events_count = Event.objects.filter(recurrence_id=self.recurring_event.recurrence_id).count()
        self.client.login(email="creator@example.com", password="password123")
        self.client.post(reverse("events:view_event", args=[self.recurring_event.pk]), {"action": "delete_event", "delete_all": "true"})
        remaining_events_count = Event.objects.filter(recurrence_id=self.recurring_event.recurrence_id).count()
        self.assertEqual(remaining_events_count, 0)
        self.assertGreater(future_events_count, 0)

    def test_comment_creation(self):
        self.client.login(email="participant@example.com", password="password123")
        comment_data = {"form_type": "comment", "comment": "This is a test comment"}
        response = self.client.post(reverse("events:view_event", args=[self.event.pk]), comment_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Comment.objects.filter(event=self.event, user=self.participant, text="This is a test comment").exists())

    def test_deny_event_request(self):
        self.client.login(email="creator@example.com", password="password123")
    
        pending_user = User.objects.create_user(
            first_name="Pending",
            last_name="User",
            email="pendinguser@example.com",
            password="password123"
        )
        EventParticipant.objects.create(
            event=self.event,
            user=pending_user,
            status="Requested",
            approved=False
        )
    
        response = self.client.post(
            reverse("events:view_event", args=[self.event.pk]), {"form_type": "deny_request", "deny_request": pending_user.username},
        )
        self.assertEqual(response.status_code, 200)
    
        participant = EventParticipant.objects.get(event=self.event, user=pending_user)
        self.assertEqual(participant.status, "Denied", "The user's request should be marked as denied")
        self.assertFalse(participant.approved, "The user's request should remain unapproved")

    def test_creator_can_delete_event(self):
        self.client.login(email="creator@example.com", password="password123")  # Login as event creator
        delete_data = {
            "action": "delete_event",
            "delete_all": "false",
        }
        response = self.client.post(reverse("events:view_event", args=[self.event.pk]), delete_data)
        self.assertEqual(response.status_code, 200, "Event creator should be allowed to delete their event")
        self.assertFalse(
            Event.objects.filter(pk=self.event.pk).exists(),
            "Event should no longer exist after creator deletes it"
        )

