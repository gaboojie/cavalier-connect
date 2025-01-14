# /***************************************************************************************
# *  REFERENCES
# *  Title: ValueError: Missing staticfiles manifest entry for 'favicon.ico'
# *  Author: Vladimir
# *  Date Published: Jun 27, 2018
# *  Date Accessed: Nov 16, 2024
# *  URL: https://stackoverflow.com/questions/44160666/valueerror-missing-staticfiles-manifest-entry-for-favicon-ico
# ***************************************************************************************/

from django.test import TestCase, Client
from django.urls import reverse
from django.test import override_settings
from myaccount.models import User
from .models import Organization, OrganizationMember
from .forms import CreateOrganizationForm, InviteMemberForm

# Create your tests here.
class OrganizationModelTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            first_name = "Test",
            last_name = "User",
            username = "testuser",
            email = "testuser@example.com",
            password = "password123"
        )
        self.organization = Organization.objects.create(
            name = "Test Organization",
            description = "Organization created for testing.",
            creator = self.creator
        )
    
    def test_organization_creation(self):
        self.assertEqual(self.organization.name, "Test Organization")
        self.assertEqual(self.organization.description, "Organization created for testing.")
        self.assertEqual(self.organization.creator, self.creator)
        self.assertIsNotNone(self.organization.created_at)
        
    def test_organization_creator_deletion(self):
        self.creator.delete()
        self.assertFalse(Organization.objects.filter(id=self.organization.id).exists())
    
    
class OrganizationMemberModelTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            first_name = "Test1",
            last_name = "Creator",
            username = "testcreator",
            email = "testcreator@example.com",
            password = "creator123"
        )
        self.member = User.objects.create_user(
            first_name = "Test2",
            last_name = "Member",
            username = "testmember",
            email = "testmember@example.com",
            password = "member123"
        )
        self.organization = Organization.objects.create(
            name = "Test Organization",
            description = "Organization created for testing.",
            creator = self.creator
        )
        
        self.organization_member = OrganizationMember.objects.create(
            organization = self.organization,
            user = self.member,
            status = OrganizationMember.INVITED
        )
        
    def test_organization_member_creation(self):
        self.assertEqual(self.organization_member.organization, self.organization)
        self.assertEqual(self.organization_member.user, self.member)
        self.assertEqual(self.organization_member.status, OrganizationMember.INVITED)
        
    def test_member_and_organization_relationship(self):
        members = self.organization.members.all()
        self.assertIn(self.organization_member, members)
    
class CreateOrganizationFormTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            first_name = "Test1",
            last_name = "Creator",
            username = "testcreator",
            email = "testcreator@example.com",
            password = "creator123"
        )
        self.organization = Organization.objects.create(
            name = "Test Organization",
            description = "Organization created for testing.",
            creator = self.creator
        )
        
    def test_valid_form_data(self):
        form_data = {
            'name': 'Unique Organization',
            'description': 'This is a test organization.',
        }
        form = CreateOrganizationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
    def test_invalid_form_data(self):
        form_data = {
            'name': '',
            'description': 'This is a test organization.',
        }
        form = CreateOrganizationForm(data = form_data)
        self.assertFalse(form.is_valid())
        
    def test_duplicate_name_form(self):
        form_data = {
            'name': 'Test Organization',
            'description': 'This is an organization with the same name as an existing organization.',
        }
        form = CreateOrganizationForm(data = form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        
    def test_duplicate_name_editing_form(self):
        form_data = {
            'name': 'Test Organization',
            'description': 'Updated description.',
        }
        form = CreateOrganizationForm(data = form_data, instance = self.organization)
        self.assertTrue(form.is_valid())
        
class InviteMemberFormTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            first_name = "Test1",
            last_name = "Creator",
            username = "testcreator",
            email = "testcreator@example.com",
            password = "creator123"
        )
        self.confirmed_member = User.objects.create_user(
            first_name = "Confirmed",
            last_name = "Member2",
            username = "confirmedmember",
            email = "confirmedmember@example.com",
            password = "confirmedmember123"
        )
        self.invited_member = User.objects.create_user(
            first_name = "Invited",
            last_name = "Member3",
            username = "invitedmember",
            email = "invitedmember@example.com",
            password = "invitedmember123"
        )
        self.potential_member = User.objects.create_user(
            first_name = "Potential",
            last_name = "Member4",
            username = "potentialmember",
            email = "potentialmember@example.com",
            password = "potentialmember123"
        )
        self.organization = Organization.objects.create(
            name = "Test Organization",
            description = "Organization created for testing.",
            creator = self.creator
        )
        
        self.organization_invited_member = OrganizationMember.objects.create(
            organization = self.organization,
            user = self.invited_member,
            status = OrganizationMember.INVITED
        )
        
        self.organization_confirmed_member = OrganizationMember.objects.create(
            organization = self.organization,
            user = self.confirmed_member,
            status = OrganizationMember.CONFIRMED
        )
        
    def test_queryset_excludes_existing_members(self):
        form = InviteMemberForm(organization = self.organization, creator = self.creator)
        queryset = form.fields['user'].queryset

        # Check that the invited and confirmed users are not in the queryset
        self.assertNotIn(self.invited_member, queryset)
        self.assertNotIn(self.confirmed_member, queryset)

        # Check that the creator is still in the queryset (shouldn't be excluded here)
        self.assertNotIn(self.creator, queryset)
        
@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class OrganizationsViewsTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            first_name = "Test1",
            last_name = "Creator",
            username = "testcreator",
            email = "testcreator@example.com",
            password = "creator123"
        )
        self.confirmed_member = User.objects.create_user(
            first_name = "Confirmed",
            last_name = "Member2",
            username = "confirmedmember",
            email = "confirmedmember@example.com",
            password = "confirmedmember123"
        )
        self.invited_member = User.objects.create_user(
            first_name = "Invited",
            last_name = "Member3",
            username = "invitedmember",
            email = "invitedmember@example.com",
            password = "invitedmember123"
        )
        self.non_member = User.objects.create_user(
            first_name = "Not",
            last_name = "Member4",
            username = "nonmember",
            email = "nonmember@example.com",
            password = "nonmember123"
        )
        self.organization = Organization.objects.create(
            name = "Test Organization",
            description = "Organization created for testing.",
            creator = self.creator
        )
        
        self.organization_invited_member = OrganizationMember.objects.create(
            organization = self.organization,
            user = self.invited_member,
            status = OrganizationMember.INVITED
        )
        
        self.organization_confirmed_member = OrganizationMember.objects.create(
            organization = self.organization,
            user = self.confirmed_member,
            status = OrganizationMember.CONFIRMED
        )
        
        self.client = Client()
        
    def test_create_organization_page_access(self):
        # Test unauthenticated access
        response = self.client.get(reverse('organizations:create_organization'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

        # Test authenticated access
        self.client.login(email='testcreator@example.com', password='creator123')
        response = self.client.get(reverse('organizations:create_organization'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'organizations/create_organization.html')
        
    def test_create_organization(self):
        self.client.login(email='testcreator@example.com', password='creator123')
        response = self.client.post(reverse('organizations:submit_organization'), {
            'name': 'New Org',
            'description': 'A new organization.'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Organization.objects.filter(name='New Org').exists())
        
    def test_view_organization_as_creator(self):
        self.client.login(email='testcreator@example.com', password='creator123')
        response = self.client.get(reverse('organizations:view_organization', kwargs={'pk': self.organization.pk}))
        self.assertTemplateUsed(response, 'organizations/view_organization.html')
        self.assertContains(response, 'You are the owner of this organization.')
        self.assertContains(response, 'Invite Member')
        
    def test_view_organization_as_member(self):
        self.client.login(email= 'confirmedmember@example.com', password = 'confirmedmember123')
        response = self.client.get(reverse('organizations:view_organization', kwargs={'pk': self.organization.pk}))
        self.assertTemplateUsed(response, 'organizations/view_organization.html')
        self.assertContains(response, 'You are a member of this organization.')
        self.assertNotContains(response, 'Invite Member')
        self.assertNotContains(response, 'Accept Invitation')
        
    def test_view_organization_as_invited_member(self):
        self.client.login(email= 'invitedmember@example.com', password = 'invitedmember123')
        response = self.client.get(reverse('organizations:view_organization', kwargs={'pk': self.organization.pk}))
        self.assertTemplateUsed(response, 'organizations/view_organization.html')
        self.assertContains(response, 'You have been invited to join this organization.')
        self.assertNotContains(response, 'Invite Member')
        self.assertContains(response, 'Accept Invitation')
        
    def test_view_organization_as_non_member(self):
        self.client.login(email= 'nonmember@example.com', password = 'nonmember123')
        response = self.client.get(reverse('organizations:view_organization', kwargs={'pk': self.organization.pk}))
        self.assertTemplateUsed(response, 'organizations/view_organization.html')
        self.assertContains(response, 'You are not a member of this organization.')
        self.assertNotContains(response, 'Invite Member')
        
    def test_delete_organization(self):
        self.client.login(email='testcreator@example.com', password='creator123')
        response = self.client.post(reverse('organizations:view_organization', kwargs={'pk': self.organization.pk}), {
            'form_type': 'delete',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Organization.objects.filter(pk = self.organization.pk).exists())
        
    def test_invite_user_to_organization(self):
        self.client.login(email='testcreator@example.com', password='creator123')
        response = self.client.post(reverse('organizations:view_organization', kwargs={'pk': self.organization.pk}), {
            'form_type': 'invite_user',
            'user': self.non_member.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            OrganizationMember.objects.filter(
                organization = self.organization,
                user = self.non_member,
                status = OrganizationMember.INVITED
            ).exists()
        )
        
    def test_remove_user_from_organization(self):
        self.client.login(email='testcreator@example.com', password='creator123')
        response = self.client.post(reverse('organizations:view_organization', kwargs={'pk': self.organization.pk}), {
            'form_type': 'remove_user',
            'username': self.confirmed_member.username,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            OrganizationMember.objects.filter(
                organization = self.organization,
                user = self.confirmed_member
            ).exists()
        )
        
    def test_accept_invitation(self):
        self.client.login(email = 'invitedmember@example.com', password = 'invitedmember123')
        response = self.client.post(reverse('organizations:view_organization', kwargs={'pk': self.organization.pk}),{
            'form_type': 'accept_invitation',
        })
        self.assertEqual(response.status_code, 200)
        member_status = OrganizationMember.objects.get(organization = self.organization, user = self.invited_member).status
        self.assertEqual(member_status, OrganizationMember.CONFIRMED)
        
    def test_deny_invitation(self):
        self.client.login(email = 'invitedmember@example.com', password = 'invitedmember123')
        response = self.client.post(reverse('organizations:view_organization', kwargs={'pk': self.organization.pk}),{
            'form_type': 'deny_invitation',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            OrganizationMember.objects.filter(
                organization = self.organization,
                user = self.invited_member
            ).exists()
        )
        
    def test_edit_organization(self):
        self.client.login(email='testcreator@example.com', password='creator123')
        response = self.client.post(reverse('organizations:edit_organization', kwargs={'pk': self.organization.pk}),{
            'name': 'Updated Name',
            'description': 'Updated description.',
        })
        self.assertTrue(response.status_code, 302)
        edited_org = Organization.objects.get(pk = self.organization.pk)
        self.assertEqual(edited_org.name, 'Updated Name')
        self.assertEqual(edited_org.description, 'Updated description.')
        

