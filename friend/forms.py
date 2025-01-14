from django import forms
from django.contrib.auth import get_user_model
from .models import Friend
from django.db.models import Q

User = get_user_model()

class InviteUserForm(forms.Form):
    invitee = forms.ModelChoiceField(
        queryset=User.objects.none(), 
        label="Select a user to invite",
        required=True
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

        excluded_users = Friend.objects.filter(
            Q(from_user=user) | Q(to_user=user),
            status__in=[Friend.STATUS_ACCEPTED, Friend.STATUS_PENDING]
        ).values_list('from_user', 'to_user')

        excluded_user_ids = set([user_id for pair in excluded_users for user_id in pair])

        self.fields['invitee'].queryset = User.objects.exclude(id__in=excluded_user_ids).exclude(id=user.id)
