from django.db import models
from myaccount.models import User

class Organization(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_organizations')
    created_at = models.DateTimeField(auto_now_add=True)
            
    def __str__(self):
        return self.name
    
class OrganizationMember(models.Model):
    INVITED = 'invited'
    CONFIRMED = 'confirmed'

    STATUS_CHOICES = [
        (INVITED, 'Invited'),
        (CONFIRMED, 'Confirmed'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)

    def __str__(self):
        return f'{self.user.username} - {self.organization.name} - {self.status}'