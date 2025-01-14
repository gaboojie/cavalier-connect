from django.db import models
from django.conf import settings
from myaccount.models import User
from organizations.models import Organization

import uuid



class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_events')
    organizations = models.ManyToManyField(Organization, related_name='events')

    # Recurrence Section
    is_recurring = models.BooleanField(default=False)
    # Options not required
    recurrence_frequency = models.CharField(max_length=10, choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'),
                                                                    ('yearly', 'Yearly')], null=True, blank=True)
    recurrence_end = models.DateTimeField(null=True, blank=True)
    recurrence_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=False, null=True, blank=True)

    def get_recurrence_info(self):
        if self.is_recurring and self.recurrence_frequency:
            return f"Recurs {self.get_recurrence_frequency_display()}"
        return "Does Not Recur"

    def __str__(self):
        return f'{self.title} - {self.creator}'
    

def upload_file(instance, filename):
    return f'uploads/{instance.user.username}/{instance.event.id}/{filename}'


class EventFile(models.Model):
    event = models.ForeignKey(Event, related_name="files", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to=upload_file)
    title = models.CharField(max_length=100, default="Untitled")
    description = models.TextField(blank=True, null=True)
    keywords = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def get_file_url(self):
        return f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{self.file.name}"

    def __str__(self):
        return f'{self.file.name} for event: [{self.event.title}]'
    

class EventParticipant(models.Model):
    INVITED = 'Invited'
    CONFIRMED = 'Confirmed'
    DENIED = 'Denied'
    MAYBE = 'Maybe'

    STATUS_CHOICES = [
        (INVITED, 'Invited'),
        (CONFIRMED, 'Confirmed'),
        (DENIED, 'Denied'),
        (MAYBE, 'Maybe'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    approved = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user.username} - {self.event.title} - {self.status} - approved? {self.approved}'


class Comment(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Comment by {self.user.username} on {self.event.title} at {self.created_at}'
    