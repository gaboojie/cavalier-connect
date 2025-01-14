from django import forms
from myaccount.models import User
from .models import OrganizationMember, Organization

class CreateOrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['name', 'description']
        
    def __init__(self, *args, **kwargs):
        # Pass the instance of the organization being edited
        self.instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get('name')
        # Exclude the current instance from the uniqueness check
        if Organization.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            self.add_error("name", "An organization with this name already exists. Please choose a different name.")
            return
        return name
    
class InviteMemberForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.none(),  # Initially set to an empty queryset
        label="Select User to Invite",
        widget=forms.Select(attrs={'class': 'form-control', 'style': 'color: #0e3685;'}),
    )
    error = None
    
    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        creator = kwargs.pop('creator', None)
        super().__init__(*args, **kwargs)
        
        # Exclude users already invited or members of the organization
        if organization:
            existing_members = OrganizationMember.objects.filter(
                organization=organization
            ).values_list('user', flat=True)
            self.fields['user'].queryset = User.objects.exclude(id__in=existing_members)
            
        if creator:
            self.fields['user'].queryset = self.fields['user'].queryset.exclude(id=creator.id)

    
    def is_invite_valid(self, organization):
        user = self.cleaned_data['user']

        # can't invite yourself
        if user == organization.creator:
            self.error = "Error: You cannot invite yourself to your organization!"
            return False
            
        # can't invite someone already invited or confirmed
        member = OrganizationMember.objects.filter(
            organization = organization, 
            user = user,
            status__in = [OrganizationMember.INVITED, OrganizationMember.CONFIRMED]).first()
        
        if member:
            if member.status == OrganizationMember.INVITED:
                self.error = f'Error: {user.username} is already invited!'
                return False
            elif member.status == OrganizationMember.CONFIRMED:
                self.error = f'Error: {user.username} is already a member of this organization!'
                return False
        
        return True

    