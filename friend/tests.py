# /***************************************************************************************
# *  REFERENCES
# *  Title: ValueError: Missing staticfiles manifest entry for 'favicon.ico'
# *  Author: Vladimir
# *  Date Published: Jun 27, 2018
# *  Date Accessed: Nov 16, 2024
# *  URL: https://stackoverflow.com/questions/44160666/valueerror-missing-staticfiles-manifest-entry-for-favicon-ico
# ***************************************************************************************/

from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from myaccount.models import User
from friend.models import Friend


class FriendTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            first_name="Test1",
            last_name="User1",
            username="testuser1",
            email="testuser1@example.com",
            password="password123"
        )
        self.user2 = User.objects.create_user(
            first_name="Test2",
            last_name="User2",
            username="testuser2",
            email="testuser2@example.com",
            password="password123"
        )
        self.user3 = User.objects.create_user(
            first_name="Test3",
            last_name="User3",
            username="testuser3",
            email="testuser3@example.com",
            password="password123"
        )

        Friend.objects.create(from_user=self.user1, to_user=self.user2, status=Friend.STATUS_ACCEPTED)
        Friend.objects.create(from_user=self.user2, to_user=self.user3, status=Friend.STATUS_PENDING)

    # Test if two users are friends
    def test_friend_model_are_friends(self):
        self.assertTrue(Friend.are_friends(self.user1, self.user2))
        self.assertFalse(Friend.are_friends(self.user1, self.user3))

    def test_friend_request_str(self):
        friend_request = Friend.objects.get(from_user=self.user1, to_user=self.user2)
        self.assertEqual(str(friend_request), "testuser1 -> testuser2 (accepted)")

    # Test duplicate friend requests
    def test_duplicate_friend_request(self):
        with self.assertRaises(Exception):
            Friend.objects.create(from_user=self.user1, to_user=self.user2, status=Friend.STATUS_PENDING)

    # Test that rejecting a friend request removes it from the database
    def test_reject_friend_request(self):
        friend_request = Friend.objects.create(from_user=self.user2, to_user=self.user1, status=Friend.STATUS_PENDING)
        self.assertTrue(Friend.objects.filter(id=friend_request.id).exists())
        friend_request.delete()
        self.assertFalse(Friend.objects.filter(id=friend_request.id).exists())

    # Bidirectional friend status
    def test_reverse_friendship_check(self):
        self.assertTrue(Friend.are_friends(self.user2, self.user1))


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class FriendsPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="Test",
            last_name="User",
            username="testuser",
            email="testuser@example.com",
            password="password123"
        )
        self.client.login(email="testuser@example.com", password="password123")
        self.other_user = User.objects.create_user(
            first_name="Other",
            last_name="User",
            username="otheruser",
            email="otheruser@example.com",
            password="password123"
        )

    def test_friends_page_loads(self):
        response = self.client.get(reverse('friends'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "friend/friends.html")


    # Test sending a friend request to another user
    def test_send_friend_request(self):
        response = self.client.post(reverse('friends'), {
            'action': 'send_request',
            'user_id': self.other_user.id,
        })
        self.assertEqual(response.status_code, 302)  # Redirect after POST
        response = self.client.get(reverse('friends'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Friend.objects.filter(from_user=self.user, to_user=self.other_user, status=Friend.STATUS_PENDING).exists())

    # Test accepting a friend request and update the status
    def test_accept_friend_request(self):
        Friend.objects.create(from_user=self.other_user, to_user=self.user, status=Friend.STATUS_PENDING)
        response = self.client.post(reverse('friends'), {
            'action': 'accept_request',
            'friend_id': self.other_user.id,
        })
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('friends'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Friend.are_friends(self.user, self.other_user))

    # Test rejecting a friend request
    def test_reject_friend_request(self):
        Friend.objects.create(from_user=self.other_user, to_user=self.user, status=Friend.STATUS_PENDING)
        response = self.client.post(reverse('friends'), {
            'action': 'reject_request',
            'friend_id': self.other_user.id,
        })
        self.assertEqual(response.status_code, 302)

        # Follow the redirect to confirm the friend request was rejected
        response = self.client.get(reverse('friends'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Friend.objects.filter(from_user=self.other_user, to_user=self.user).exists())

    # Test canceling a friend request and removing from database
    def test_cancel_sent_friend_request(self):
        Friend.objects.create(from_user=self.user, to_user=self.other_user, status=Friend.STATUS_PENDING)

        response = self.client.post(reverse('friends'), {
            'action': 'cancel_request',
            'user_id': self.other_user.id,
        })
        self.assertEqual(response.status_code, 302) 
        response = self.client.get(response.url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Friend.objects.filter(from_user=self.user, to_user=self.other_user, status=Friend.STATUS_PENDING).exists())

    # Test that removing a friend removes it in both directions
    def test_user_not_found(self):
        nonexistent_user_id = 9999
        response = self.client.post(reverse('friends'), {
            'action': 'send_request',
            'user_id': nonexistent_user_id,
        })
        self.assertEqual(response.status_code, 302)  # Redirect after POST

        # Follow the redirect to confirm no errors and correct message handling
        response = self.client.get(reverse('friends'))
        self.assertEqual(response.status_code, 200)

        # Test that sending a friend request to an existing friend does not duplicate
    def test_send_request_to_existing_friend(self):
        Friend.objects.create(from_user=self.user, to_user=self.other_user, status=Friend.STATUS_ACCEPTED)

        response = self.client.post(reverse('friends'), {
            'action': 'send_request',
            'user_id': self.other_user.id,
        })
        self.assertEqual(response.status_code, 302) 
        response = self.client.get(response.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Friend.objects.filter(from_user=self.user, to_user=self.other_user, status=Friend.STATUS_PENDING).count(), 0)

    # Test that the invite form excludes users who are already friends
    def test_invite_form_excludes_existing_friends(self):
        Friend.objects.create(from_user=self.user, to_user=self.other_user, status=Friend.STATUS_ACCEPTED)

        response = self.client.get(reverse('friends'))
        form = response.context['form']
        self.assertNotIn(self.other_user, form.fields['invitee'].queryset)

    # Ensure the invite form includes users who are friend-able
    def test_invite_form_includes_valid_users(self):
        another_user = User.objects.create_user(
            first_name="Another",
            last_name="User",
            username="anotheruser",
            email="anotheruser@example.com",
            password="password123"
        )
        response = self.client.get(reverse('friends'))
        form = response.context['form']
        self.assertIn(another_user, form.fields['invitee'].queryset)

    # Nonexistent friend request
    def test_accept_nonexistent_friend_request(self):
        friend_request = Friend.objects.create(
            from_user=self.other_user, 
            to_user=self.user, 
            status=Friend.STATUS_PENDING
        )
        friend_request.delete()

        response = self.client.post(reverse('friends'), {
            'action': 'accept_request',
            'friend_id': self.other_user.id,
        })
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('friends'))
        self.assertEqual(response.status_code, 200)

    # Test interacting with a nonexistent user
    def test_user_not_found(self):      
        nonexistent_user_id = 9999
        response = self.client.post(reverse('friends'), {
            'action': 'send_request',
            'user_id': nonexistent_user_id,
        })
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('friends'))
        self.assertEqual(response.status_code, 200)