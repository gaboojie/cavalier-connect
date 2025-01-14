from django.test import TestCase
from django.urls import reverse
from events.models import Event
from myaccount.models import User
from django.utils.timezone import make_aware
from datetime import datetime, timedelta

class PmaViewsTest(TestCase):
    def setUp(self):
        self.pma_user = User.objects.create_user(
            first_name='PMA',
            last_name='User',
            email='pma@example.com',
            password='password123',
            role=2
        )
        self.common_user = User.objects.create_user(
            first_name='Common',
            last_name='User',
            email='common@example.com',
            password='password123',
            role=1
        )
        self.event = Event.objects.create(
            title='Test Event',
            description='This is a test event description',
            creator=self.pma_user,
            start_time=make_aware(datetime.now() + timedelta(days=1)),
            end_time=make_aware(datetime.now() + timedelta(days=1, hours=2)),
        )

    def test_pma_access_pma(self):
        self.client.login(email='pma@example.com', password='password123')
        response = self.client.get(reverse('pma'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pma/pma.html')

    def test_pma_access_non_pma(self):
        self.client.login(email='common@example.com', password='password123')
        response = self.client.get(reverse('pma'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pma/pma.html')

    def test_pma_access_anonymous_user(self):
        response = self.client.get(reverse('pma'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pma/pma.html')

    def test_edit_view_pma(self):
        self.client.login(email='pma@example.com', password='password123')
        response = self.client.get(reverse('edit_event', args=[self.pma_user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pma/pma.html')

    def test_edit_view__non_pma(self):
        self.client.login(email='common@example.com', password='password123')
        response = self.client.get(reverse('edit_event', args=[self.pma_user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pma/pma.html')

    def test_edit_view_anonymous(self):
        response = self.client.get(reverse('edit_event', args=[self.pma_user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pma/pma.html')

    def test_delete_event(self):
        self.client.login(email='pma@example.com', password='password123')
        response = self.client.get(reverse('delete_event'), {'selected_events': [self.event.id]})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Event.objects.filter(id=self.event.id).exists())

    def test_delete_event_no_select(self):
        self.client.login(email='pma@example.com', password='password123')
        response = self.client.get(reverse('delete_event'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Event.objects.filter(id=self.event.id).exists())
