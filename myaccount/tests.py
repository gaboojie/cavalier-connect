# /***************************************************************************************
# *  REFERENCES
# *  Title: Unit Testing File Objects in Django with SimpleUploadedFile
# *  Author: kinsacreative
# *  Date Published: Mar 4, 2021
# *  Date Accessed: Nov 16, 2024
# *  URL: https://blog.kinsacreative.com/articles/unit-testing-file-objects-django/
# ***************************************************************************************/

from django.test import TestCase

from myaccount.models import User, profile_picture_path
from myaccount.models import ProfilePicture, NotificationPreference, VerifyPhoneNumber
from myaccount.forms import ProfilePictureUpdateForm, UpdateProfileForm
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

class UserTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            first_name="Test",
            last_name="User",
            username="testuser",
            email="testuser@example.com",
            password="password123"
    )

    # Test creating superuser
    def test_create_superuser(self):
        superuser = User.objects.create_superuser(
            email="admin@example.com",
            username="admin",
            password="admin123"
        )
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)

    # Adding profile picture
    def test_add_profile_picture(self):
        profile_picture = ProfilePicture.objects.create(
            user=self.user, profile_picture="path/to/image.jpg"
        )
        self.assertEqual(profile_picture.user, self.user)
        self.assertEqual(profile_picture.profile_picture, "path/to/image.jpg")

    # Replacing a profile picture
    def test_replace_profile_picture(self):
        old_picture = ProfilePicture.objects.create(
            user=self.user, profile_picture="path/to/old_image.jpg"
        )
        new_picture = ProfilePicture(
            user=self.user, profile_picture="path/to/new_image.jpg"
        )
        new_picture.save()
        self.assertEqual(new_picture.profile_picture, "path/to/new_image.jpg")
        self.assertNotEqual(new_picture.profile_picture, old_picture.profile_picture)

    # Test notification
    def test_notification(self):
        preferences = NotificationPreference.objects.create(
            user=self.user, email_notifications=True, sms_notifications=False
        )
        self.assertTrue(preferences.email_notifications)
        self.assertFalse(preferences.sms_notifications)

    # Test phone number verification
    def test_generate_verification_code(self):
        verification = VerifyPhoneNumber.objects.create(
            user=self.user, verification_code="1234", verified_number=False
        )
        self.assertEqual(verification.verification_code, "1234")
        self.assertFalse(verification.verified_number)

    # Test ProfilePictureUpdateForm
    def test_valid_picture(self):
        test_file = SimpleUploadedFile("test_image.jpg", b"file_content", content_type="image/jpeg")
        form = ProfilePictureUpdateForm(data={}, files={"file": test_file})
        self.assertTrue(form.is_valid())

    # Test ProfilePictureUpdateForm without a file
    def test_no_file_picture(self):
        form = ProfilePictureUpdateForm(data={})
        self.assertFalse(form.is_valid())

    # Test updating profile form
    def test_update_profile(self):
        form_data = {"username": "newuser", "phone_number": "8045556666"}
        form = UpdateProfileForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())

    # Test invalid username
    def test_username_update_profile(self):
        form_data = {"username": "", "phone_number": "8045556666"}
        form = UpdateProfileForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("Username cannot be empty!", form.errors["username"])

    # Test invalid phone number     
    def test_phone_number_update_profile(self):
        form_data = {"username": "validuser", "phone_number": "abc123"}
        form = UpdateProfileForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Mobile number must be 10 digits long!", form.errors["phone_number"]
    )
        
    # Test short username
    def test_short_username(self):
        form_data = {"username": "test", "phone_number": "8045556666"}
        form = UpdateProfileForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("Username must be greater than 6 characters!", form.errors["username"])

    # Test username invalid characters
    def test_invalid_username(self):
        form_data = {"username": "test!ngTime", "phone_number": "8045556666"}
        form = UpdateProfileForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("Username can only contain letters and numbers, no spaces or special characters!", form.errors["username"])

    # Test duplicate username
    def test_duplicate_username(self):
        User.objects.create_user(
            first_name="Another",
            last_name="User",
            username="duplicateuser",
            email="another@example.com",
            password="password123",
            phone_number="1112223333"
        )
        form_data = {"username": "duplicateuser", "phone_number": "8045556666"}
        form = UpdateProfileForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("This username is already in use!", form.errors["username"])

    # Test invalid phone number length
    def test_phone_number_length(self):
        form_data = {"username": "validuser", "phone_number": "123"}
        form = UpdateProfileForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("Mobile number must be 10 digits long!", form.errors["phone_number"])

    # Test duplicate phone number
    def test_duplicate_phone_number(self):
        User.objects.create_user(
            first_name="Another",
            last_name="User",
            username="anotheruser",
            email="another@example.com",
            password="password123",
            phone_number="8045556666"
        )
        form_data = {"username": "validuser", "phone_number": "8045556666"}
        form = UpdateProfileForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("This mobile number is already in use by another account!", form.errors["phone_number"])

    # Test invalid characters in phone number
    def test_invalid_phone_number(self):
        form_data = {"username": "validuser", "phone_number": "804555abcd"}
        form = UpdateProfileForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("Mobile number must contain only digits!", form.errors["phone_number"])

    # Test save method in UpdateProfileForm
    def test_save_user_with_form(self):
        form_data = {"username": "updateduser", "phone_number": "8045556666"}
        form = UpdateProfileForm(data=form_data, instance=self.user)
        if form.is_valid():
            user = form.save(commit=True)
            self.assertEqual(user.username, "updateduser")
            self.assertEqual(user.phone_number, "8045556666")

    # Test creating user without email
    def test_create_user_without_email(self):
        with self.assertRaisesMessage(ValueError, "The Email field must be set"):
            User.objects.create_user(email=None, password="password123")

    # Test creating superuser without is_staff=True
    def test_create_superuser_without_is_staff(self):
        with self.assertRaisesMessage(ValueError, "Superuser must have is_staff=True."):
            User.objects.create_superuser(
                email="admin@example.com", username="admin", password="admin123", is_staff=False
            )

    # Test creating superuser without is_superuser=True
    def test_create_superuser_without_is_superuser(self):
        with self.assertRaisesMessage(ValueError, "Superuser must have is_superuser=True."):
            User.objects.create_superuser(
                email="admin@example.com", username="admin", password="admin123", is_superuser=False
            )

    # Test profile picture path generation
    def test_profile_picture_path(self):
        profile_picture = ProfilePicture(user=self.user, profile_picture="example.jpg")
        path = profile_picture_path(profile_picture, "example.jpg")
        self.assertEqual(path, f"profile/{self.user.id}/example.jpg")


    # Test User __str__ method
    def test_user_str(self):
        self.assertEqual(
            str(self.user),
            f"{self.user.username} ({self.user.first_name} {self.user.last_name}) - Role: {self.user.role}"
        )

    # Test get_file_url method
    def test_get_file_url(self):
        profile_picture = ProfilePicture(user=self.user, profile_picture="example.jpg")
        self.assertEqual(
            profile_picture.get_file_url(),
            f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/example.jpg"
        )