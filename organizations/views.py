from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import FormView
from .forms import CreateOrganizationForm, InviteMemberForm
from .models import Organization, OrganizationMember
from myaccount.models import User

class CreateOrganizationView(FormView):
    form_class = CreateOrganizationForm
    template_name = "organizations/create_organization.html"

@login_required
def create_organization(request):
    all_users = User.objects.exclude(id=request.user.id)  # Retrieve all users except the current user
    form = CreateOrganizationForm()  # Instantiate the form

    # Render the template with the form and all_users in context
    return render(request, 'organizations/create_organization.html', {
        'form': form,
        'all_users': all_users,
    })
   
@login_required 
def submit_organization(request): 
    if request.method == 'POST':
        form = CreateOrganizationForm(request.POST)
        all_users = User.objects.exclude(id=request.user.id)

        if not request.user.is_authenticated:
            return redirect('/')

        if form.is_valid():
            user = request.user
            form_name = form.cleaned_data["name"]
            form_description = form.cleaned_data["description"]
                
            organization = Organization(
                name=form_name, description=form_description, creator=user)
                    
            organization.save()
            
            # Automatically add the creator as a member
            OrganizationMember.objects.create(
                organization=organization,
                user=user,
                status=OrganizationMember.CONFIRMED
            )
            
            selected_members = request.POST.getlist('members')
            
            for member_id in selected_members:
                member = User.objects.get(id=member_id)
                OrganizationMember.objects.create(
                    organization=organization,
                    user=member,
                    status=OrganizationMember.INVITED
                )
                
            # messages.success(request, 'Organization created successfully!')
            
            return redirect('organizations:view_organization', pk=organization.pk)
            
        return render(request, 'organizations/create_organization.html', {
            'form': form,  # Include the form with validation errors
            'all_users': all_users,
        })
        
    return render(request, 'organizations/create_organization.html', {
        'form': CreateOrganizationForm(),  # New form instance for GET requests
        'all_users': User.objects.exclude(id=request.user.id),
    })
    
    
class OrganizationView(FormView):
    template_name = "organizations/view_organization.html"
    
    def get(self, request, pk):
        organization = self.get_organization(pk)
        user = request.user
        
        # Ensure the user is logged in
        if not user.is_authenticated:
            #messages.error(request, "You must be logged in to view this organization.")
            return redirect('/')  # Redirect to the login page

        # handle organization doesn't exist
        if organization is None:
            return self.get_organization_does_not_exist_view(request)


        # determine requesting user's membership status
        is_member = OrganizationMember.objects.filter(
            organization = organization, 
            user = user, 
            status = OrganizationMember.CONFIRMED).exists()
        
        is_invited = OrganizationMember.objects.filter(
            organization = organization, 
            user = user, 
            status = OrganizationMember.INVITED).exists()


        # different views based on role and membership status
        if user == organization.creator or user.role == 2:  # admin or creator
            return self.get_organization_owner_view(request, organization)
        
        elif is_invited or is_member:
            return self.get_user_in_organization_view(request, organization)
        
        else:
            return self.get_user_not_in_organization_view(request, organization, "You are not a member of this organization.")
        
        
    def get_organization_does_not_exist_view(self, request):
        return render(request, self.template_name, {"error": "This organization does not exist."})
    
    def get_organization_owner_view(self, request, organization, optional_message=None):
        members = OrganizationMember.objects.filter(organization = organization).exclude(user=request.user)
        confirmed_members = members.filter(status = OrganizationMember.CONFIRMED)
        invited_members = members.filter(status = OrganizationMember.INVITED)
        
        # initialize the InviteMemberForm with the organization instance
        invite_form = InviteMemberForm(organization=organization, creator=organization.creator)

        context = {
            "organization": organization,
            "confirmed_members": confirmed_members,
            "invited_members": invited_members,
            "invite_form": invite_form,
            "message": optional_message
        }
        return render(request, self.template_name, context)
    
    # kind of hesitant here about whether users should see the invited members or just confirmed?
    def get_user_in_organization_view(self, request, organization, optional_message=None):
        # invited_members = members.filter(organization=organization, status = OrganizationMember.INVITED)
        members = OrganizationMember.objects.filter(organization=organization).exclude(user=organization.creator)
        confirmed_members = members.filter(organization=organization, status = OrganizationMember.CONFIRMED)
        
        context = {
            "organization": organization,
            # "invited_members": invited_members,
            "confirmed_members": confirmed_members,
            "message": optional_message,
            "is_member": members.filter(user=request.user, status=OrganizationMember.CONFIRMED).exists(),
            "is_invited": members.filter(user=request.user, status=OrganizationMember.INVITED).exists(),
        }
        return render(request, self.template_name, context)
    
    # set up so non members can't see list of members for the org but can easily change
    def get_user_not_in_organization_view(self, request, organization, optional_message=None):
        context = {
            "organization": organization,
            "message": optional_message
        }
        return render(request, self.template_name, context)
    
    
    
    def post(self, request, pk):
        organization = self.get_organization(pk)
        user = request.user

        if organization is None:
            return self.get_organization_does_not_exist_view(request)

        if not user.is_authenticated:
            return redirect('/')

        form_type = request.POST.get("form_type")
        
        # Handle different actions based on form_type
        if form_type == 'delete' and (user == organization.creator or user.role == 2):
            return self.delete_organization(request, organization)
        elif form_type == 'invite_user' and user == organization.creator:
            return self.invite_user_to_organization(request, organization)
        elif form_type == 'remove_user' and user == organization.creator:
            return self.remove_user_from_organization(request, organization)
        elif form_type == 'edit' and user == organization.creator:
            return self.edit_organization(request, organization)
        elif form_type == 'accept_invitation':
            return self.accept_invitation(request, organization)
        elif form_type == 'deny_invitation':
            return self.deny_invitation(request, organization)

        return self.get(request, pk)

    def delete_organization(self, request, organization):
        organization.delete()
        return redirect('/')  # for now while we don't have an all organizations page
    
    def invite_user_to_organization(self, request, organization):
        if request.method == 'POST':
            form = InviteMemberForm(request.POST, organization = organization, creator = organization.creator)
            
            if form.is_valid(): # make sure the form itself is valid
                if form.is_invite_valid(organization): # make sure the user is valid to invite
                    # Add the user as an invited member
                    user_to_invite = form.cleaned_data['user']
                    OrganizationMember.objects.create(
                        organization = organization,
                        user = user_to_invite,
                        status = OrganizationMember.INVITED
                    )
                    messages.success(request, f"Invitation sent to {user_to_invite.username}.")
                else:
                    # Display any error set by the form's `is_invite_valid` method
                    messages.error(request, form.error)
            else:
                messages.error(request, "Invalid data in the form.")
        
        # Redirect back to the owner view with updated context
        return self.get_organization_owner_view(request, organization)
    
    def remove_user_from_organization(self, request, organization):    
        username = request.POST.get("username")

        if username:
            try:
                user_to_remove = User.objects.get(username=username)
                try:
                    member = OrganizationMember.objects.get(organization=organization, user=user_to_remove)
                    member.delete()  # Remove the user from the organization
                    messages.success(request, f"{user_to_remove.username} has been removed from the organization.")
                except OrganizationMember.DoesNotExist:
                    messages.error(request, "User is not a member of this organization.")
            except User.DoesNotExist:
                messages.error(request, "User not found.")
        else:
            messages.error(request, "No user specified.")
            
        return self.get_organization_owner_view(request, organization)
    
    def accept_invitation(self, request, organization):
        user = request.user
        member = OrganizationMember.objects.filter(organization=organization, user=user, status=OrganizationMember.INVITED).first()
        if member:
            member.status = OrganizationMember.CONFIRMED
            member.save()
            messages.success(request, "You have successfully joined the organization!")
        else:
            messages.error(request, "No invitation found for you in this organization.")
        
        return self.get_user_in_organization_view(request, organization)
    
    def deny_invitation(self, request, organization):
        user = request.user
        member = OrganizationMember.objects.filter(organization=organization, user=user, status=OrganizationMember.INVITED).first()
        if member:
            member.delete()
            messages.success(request, "You have successfully rejected this invitiation.")
        else:
            messages.error(request, "No invitation found for you in this organization.")
        
        return self.get_user_in_organization_view(request, organization)

    def get_organization(self, pk):
        try:
            return Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return None
        
@login_required
def edit_organization_view(request, pk):
    organization = get_object_or_404(Organization, pk=pk)
    
    if not request.user.is_authenticated:
        #messages.error(request, "You must be logged in to view this organization.")
        return redirect('/')  # Redirect to the login page
    
    # Check if the current user is the creator
    if request.user != organization.creator:
        messages.error(request, "You do not have permission to edit this organization.")
        return redirect('organizations:view_organization', pk=pk)  # Redirect to the organization view page
    
    if request.method == 'POST':
        form = CreateOrganizationForm(request.POST, instance=organization)
        if form.is_valid():
            form.save()
            messages.success(request, "Organization updated successfully.")
            return redirect('organizations:view_organization', pk=pk)
    else:
        form = CreateOrganizationForm(initial={'name': organization.name, 'description': organization.description})
    
    return render(request, 'organizations/edit_organization.html', {'form': form, 'organization': organization})