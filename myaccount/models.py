import random
import string

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.hashers import make_password
from django.conf import settings

class CreateUser(BaseUserManager):

    def create_user(self, email, username = None, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")

        email = self.normalize_email(email)
        if User.objects.filter(username=username).exists():
            # If username already exists, make a random one
            username = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        # Fix user not having role assigned after creating account (which happens if they don't save() after logging in)
        if username:
            user.role = 1

        user.save(using=self._db)
        return user

    def create_superuser(self, email, username=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, username, password, **extra_fields)

def profile_picture_path(instance, filename):
    return f'profile/{instance.user.id}/{filename}'
class User(AbstractBaseUser, PermissionsMixin):
    #0 = anonymous, 1 = common, 2 = pma, 3 = django
    first_name = models.CharField(max_length=250)
    last_name = models.CharField(max_length=250)
    username = models.CharField(max_length=250, unique=False, null=True, blank=True)   #change to True for unqiue later
    email = models.EmailField(unique=True, default = "johndoe@gmail.com") 
    password = models.CharField(max_length=128)
    role = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(9)])
    created_timestamp = models.DateTimeField(default=timezone.now)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    #DONT DELETE; DJANGO REQUIRES
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    
    REQUIRED_FIELDS = ['first_name', 'last_name']


    objects = CreateUser()

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def __str__(self):
        return f"{self.username} ({self.first_name} {self.last_name}) - Role: {self.role}"
class ProfilePicture(models.Model):
    profile_picture = models.FileField(upload_to=profile_picture_path)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def get_file_url(self):
        return f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{self.profile_picture.name}"
    def save(self, *args, **kwargs):
        if self.pk:
            old_picture = ProfilePicture.objects.filter(pk=self.pk).first().profile_picture
            if old_picture and old_picture != self.profile_picture:
                old_picture.delete(save=False)
        super().save(*args, **kwargs)
class NotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)

class VerifyPhoneNumber(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    verification_code = models.CharField(max_length=4, blank=True, null=True)
    verified_number = models.BooleanField(default=False)