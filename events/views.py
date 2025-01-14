from dateutil.relativedelta import relativedelta
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views import View
from django.views.generic import FormView
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse

from organizations.models import Organization, OrganizationMember
from .forms import CreateEventForm, EventInviteUserForm, UploadFileForm
from .models import Event, EventParticipant, EventFile, Comment
from myaccount.models import User
import boto3
import mimetypes
from datetime import timedelta
from django.core.mail import send_mail
from myaccount.sms import * 
s3 = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME
)


class EventView(View):
    template_name = "events/view_event.html"

    def get(self, request, pk):
        event = get_event(pk)
        user = request.user

        # Handle event does not exist
        if event is None:
            return self.get_event_does_not_exist_view(request)
        # Handle anonymous user
        if not user.is_authenticated:
            return self.get_event_anonymous_view(request, event)
        
        # Get all files for the event
        files = EventFile.objects.filter(event=event)
        search_query = request.GET.get("search", "").strip()
        if search_query:
            files = files.filter(keywords__icontains=search_query)
            no_match = not files.exists()
        else:
            no_match = False

        is_participant = EventParticipant.objects.filter(event=event, user=user, status='Confirmed', approved=True).exists()
        # Find the next recurrence if the event is recurring
        next_recurrence = None
        if event.is_recurring:
            next_recurrence = Event.objects.filter(
                recurrence_id=event.recurrence_id,
                start_time__gt=event.start_time
            ).order_by('start_time').first()

        has_invitation = EventParticipant.objects.filter(event=event, user=user,status = "Invited", approved=False).exists()

        if user == event.creator or user.role == 2:  # admin or creator
            return self.get_event_owner_view(request, event, files, next_recurrence=next_recurrence, no_match=no_match)
        elif has_invitation:
            return self.get_user_not_in_event_view(request, event, optional_message="Your request is pending approval.")
        elif is_participant:
            return self.get_user_in_event_view(request, event, files, next_recurrence=next_recurrence, no_match=no_match)
        else:
            return self.get_user_not_in_event_view(request, event)

    def get_event_does_not_exist_view(self, request):
        return render(request, self.template_name)

    def get_event_anonymous_view(self, request, event):
        context = {
            "event": event, 'role': "anonymous"
        }
        return render(request, self.template_name, context)

    def get_user_not_in_event_view(self, request, event, optional_message=None):
        status = "none"
        approved = "none"
        event_participant = EventParticipant.objects.filter(event=event, user=request.user)
        if event_participant.exists():
            participant = event_participant.first()
            status = participant.status.lower()
            approved = participant.approved
        context = {
            "event": event, "role": "not-in-event", "status": status, "approved": approved
        }
        if optional_message:
            context["message"] = optional_message
        return render(request, self.template_name, context)

    def get_user_in_event_view(self, request, event, files, optional_message=None, next_recurrence=None, no_match=False):
        files = EventFile.objects.filter(event=event)
        participants = EventParticipant.objects.get(event=event, user=request.user)
        comments = Comment.objects.filter(event=event)
        if participants and participants.status == 'Confirmed' and participants.approved:
            can_upload_files = True
        else:
            can_upload_files = False

        invited_participants = []
        requested_participants = []
        event_participants = EventParticipant.objects.filter(event=event)
        for participant in event_participants:
            if participant.approved:
                invited_participants.append({
                    "username": participant.user.username,
                    "status": str(participant.status)}
                )
            elif not participant.approved and participant.status == "Denied":
                invited_participants.append({
                    "username": participant.user.username,
                    "status": str(participant.status)}
                )
            else:
                requested_participants.append({
                    "username": participant.user.username,
                    "status": str(participant.status)}
                )

        context = {
            "event": event, "event_files": files, "status": str(participants.status), "comments": comments, "role": "in-event",
            "message": optional_message, "can_upload_files": can_upload_files, "next_recurrence": next_recurrence, "no_match": no_match,
            "invited_participants": invited_participants, "requested_participants": requested_participants,
        }
        return render(request, self.template_name, context)

    def get_event_owner_view(self, request, event, files, optional_message=None, next_recurrence=None, no_match=False):
        event_participants = EventParticipant.objects.filter(event=event)
        comments = Comment.objects.filter(event=event)
        invited_participants = []
        requested_participants = []

        for participant in event_participants:
            if participant.approved:
                invited_participants.append({
                    "username": participant.user.username,
                    "status": str(participant.status)}
                )
            elif not participant.approved and participant.status == "Denied":
                invited_participants.append({
                    "username": participant.user.username,
                    "status": str(participant.status)}
                )
            else:
                requested_participants.append({
                    "username": participant.user.username,
                    "status": str(participant.status)}
                )

        role = "pma"
        if request.user.username == event.creator.username:
            role = "owner"

        context = {
            "event": event, "event_files": files, "invited_participants": invited_participants,
            "requested_participants": requested_participants, "comments": comments,
            "message": optional_message, "next_recurrence": next_recurrence, "role": role, "no_match": no_match
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        event = get_event(pk)
        user = request.user

        # Handle event does not exist
        if event is None:
            return self.get_event_does_not_exist_view(request, pk)

        # Handle anonymous user
        if not user.is_authenticated:
            return self.get_event_anonymous_view(request, event)

        action = request.POST.get('action')
        delete_all = request.POST.get('delete_all') == 'true'

        if action == 'delete_event':
            event = get_object_or_404(Event, id=event.pk)
            # Check if the user is the creator or a PMA
            if request.user == event.creator or request.user.is_pma:
                if delete_all:
                    delete_all_future_occurrences(event)
                else:
                    event.delete()
                return JsonResponse({'success': True})

            return JsonResponse({'success': False}, status=403)

        # Handle user accept event
        if request.POST.get("form_type") == 'accept_event' and EventParticipant.objects.filter(event=event, user=user).exists():
            return self.post_accept_event(request, event)

        # Handle user deny event
        if request.POST.get("form_type") == 'deny_event' and EventParticipant.objects.filter(event=event, user=user).exists():
            return self.post_deny_accepting_event(request, event)

        # Handle Invite User Form
        if event.creator.username == user.username and request.POST.get("form_type") == 'invite_user':
            return self.post_invite_user_form(request, event)

        # Handle Upload Event Form
        if request.POST.get("form_type") == 'upload_file':
            is_creator = event.creator.username == user.username
            is_participant = EventParticipant.objects.filter(event=event, user=user, status="Confirmed", approved=True).exists()
            if is_creator or is_participant:
                return self.post_upload_file(request, event)

        # Handle Approve Event form
        if event.creator.username == user.username and request.POST.get("form_type") == 'approve_request':
            return self.post_approve_user_invite(request, event)

        # Handle Deny Event form
        if event.creator.username == user.username and request.POST.get("form_type") == 'deny_request':
            return self.post_deny_user_invite(request, event)

        # Handle Delete Invite Event form
        if event.creator.username == user.username and request.POST.get("form_type") == 'delete_invite':
            return self.post_delete_user_invite(request, event)

        # Handle Request Access Form
        if request.user != event.creator and request.POST.get("form_type") == 'request_access' \
                and not EventParticipant.objects.filter(event=event, user=request.user, approved=True).exists():
            return self.post_request_access(request, event)

        # Handle Post Comment Form
        if (request.user == event.creator or EventParticipant.objects.filter(event=event, user=request.user, approved=True).exists()) \
                and request.POST.get("form_type") == 'comment':
            return self.post_comment(request, event)

        # Handle Delete Comment Form
        if request.POST.get("form_type") == "delete_comment":
            return self.post_delete_comment(request, event)

        # Handle Edit Metadata
        if request.POST.get("form_type") == "edit_file":
            return self.post_edit_file(request, event)

        # Handle Invite Organization Form
        if request.POST.get("form_type") == "add_organization" and request.user.username == event.creator.username:
            return self.post_add_organization(request, event)

        # Handle Delete Organization Form
        if request.POST.get("form_type") == "remove_organization" and request.user.username == event.creator.username:
            return self.post_delete_organization(request, event)
        
        # Handle Participant Remove Self
        if request.POST.get("form_type") == "remove_self":
            try:
                participant = EventParticipant.objects.get(event=event, user=user)
                participant.delete()
                optional_message = "You have successfully removed yourself from this event."
            except EventParticipant.DoesNotExist:
                optional_message = "Error: You are not a participant of this event."
            return self.get_user_not_in_event_view(request, event, optional_message)

        print("Event post was sent, but no form matched the post!")
        return self.get(request, pk)


    def post_add_organization(self, request, event):
        files = EventFile.objects.filter(event=event);
        if request.POST.get("organization_to_add") is not None and request.POST.get("organization_to_add") != "":
            organization = Organization.objects.filter(name=request.POST.get("organization_to_add"))
            if organization.exists():
                organization = organization.first()
                organization_members = OrganizationMember.objects.filter(organization=organization)

                # Add all organization members
                for member in organization_members:
                    participates_in_event = EventParticipant.objects.filter(event=event, user=member.user)
                    if not participates_in_event.exists() and event.creator.username != member.user.username:
                        new_participant = EventParticipant(event=event, user=member.user, status="Invited", approved=True)
                        new_participant.save()

                # Add owner
                organization_owner_participates_in_event = EventParticipant.objects.filter(event=event, user=organization.creator)
                if not organization_owner_participates_in_event.exists() and event.creator.username != organization.creator.username:
                    new_participant = EventParticipant(event=event, user=organization.creator, status="Invited", approved=True)
                    new_participant.save()

                return self.get_event_owner_view(request, event, files, "Invited all organization members (that have not already been invited).")
            else:
                return self.get_event_owner_view(request, event, files, "Error: The organization you tried to add does not exist!")
        else:
            return self.get_event_owner_view(request, event, files, "Error: You did not specify an organization to add!")

    def post_delete_organization(self, request, event):
        files = EventFile.objects.filter(event=event);
        if request.POST.get("organization_to_remove") is not None and request.POST.get("organization_to_remove") != "":
            organization = Organization.objects.filter(name=request.POST.get("organization_to_remove"))
            if organization.exists():
                organization = organization.first()
                organization_members = OrganizationMember.objects.filter(organization=organization)

                # Remove all organization members
                for member in organization_members:
                    participates_in_event = EventParticipant.objects.filter(event=event, user=member.user)
                    if participates_in_event.exists():
                        participates_in_event.delete()

                # Remove organization owner
                organization_owner_participates_in_event = EventParticipant.objects.filter(event=event, user=organization.creator)
                if organization_owner_participates_in_event.exists():
                    organization_owner_participates_in_event.delete()

                return self.get_event_owner_view(request, event, files, "Removed all organization members.")
            else:
                return self.get_event_owner_view(request, event, files, "Error: No organization with that name exists!")
        else:
            return self.get_event_owner_view(request, event, files, "Error: You did not specify an organization to remove members from!")

    def post_accept_event(self, request, event):
        participant = EventParticipant.objects.get(event=event, user=request.user)
        participant.status = 'Confirmed'
        participant.save()
        files = EventFile.objects.filter(event=event)
        return self.get_user_in_event_view(request, event, files, "Accepted event.")

    def post_deny_accepting_event(self, request, event):
        participant = EventParticipant.objects.get(event=event, user=request.user)
        participant.status = 'Denied'
        participant.save()
        return self.get_user_not_in_event_view(request, event, "Denied event.")

    def post_comment(self, request, event):
        if request.POST.get("comment") is not None:
            text = request.POST.get("comment")
            Comment.objects.create(event=event, user=request.user, text=text)

            optional_message = 'Added comment.'
        else:
            optional_message = "Error: No user was found with that username!"

        files = EventFile.objects.filter(event=event)

        if event.creator.username == request.user.username:
            return self.get_event_owner_view(request, event, files, optional_message)
        else:
            return self.get_user_in_event_view(request, event, files, optional_message)

    def post_delete_user_invite(self, request, event):
        if request.POST.get("delete_invite") is not None:
            username = request.POST.get("delete_invite")
            user_with_username = User.objects.get(username=username)
            event_participant = EventParticipant.objects.get(user=user_with_username, event=event)
            event_participant.delete()

            optional_message = f'Deleted invite for "{user_with_username.username}".'
        else:
            optional_message = "Error: No user was found with that username!"

        files = EventFile.objects.filter(event=event)

        return self.get_event_owner_view(request, event, files, optional_message)

    def post_request_access(self, request, event):
        if request.POST.get("request_access") is not None:
            username = request.POST.get("request_access")
            user_with_username = User.objects.get(username=username)
            event_participant = EventParticipant(event=event, user=user_with_username, status="Invited", approved=False)
            event_participant.save()

            optional_message = 'Requested access to event!'
            # Sends notification to event creator about request
            msg = f"{user_with_username.username} has requested access to your event: [{event.title}]. Please accept or deny their request!"
            send_notification(event.creator,subject= "Request Access", msg= msg)
        else:
            optional_message = "Error: No user was found with that username!"
        return self.get_user_not_in_event_view(request, event, optional_message)

    def post_deny_user_invite(self, request, event):
        files = EventFile.objects.filter(event=event)

        if request.POST.get("deny_request") is not None:
            username = request.POST.get("deny_request")
            user_with_username = User.objects.get(username=username)
            event_participant = EventParticipant.objects.get(user=user_with_username,event=event)
            event_participant.status = 'Denied'
            event_participant.save()

            optional_message = f'Denied event request from "{user_with_username.username}".'
            msg = f"Your request to join {event.title} has been denied, sorry!"
            send_notification(user_with_username,subject= "Request Access", msg= msg)
        else:
            optional_message = "Error: No user was found with that username!"
        return self.get_event_owner_view(request, event, files, optional_message)

    def post_approve_user_invite(self, request, event):
        files = EventFile.objects.filter(event=event)
        if request.POST.get("approve_request") is not None:
            username = request.POST.get("approve_request")
            user_with_username = User.objects.get(username=username)
            event_participant = EventParticipant.objects.get(user=user_with_username,event=event)
            event_participant.approved = True
            event_participant.status = 'Confirmed'
            event_participant.save()

            optional_message = f'Accepted event request from "{user_with_username.username}".'
            msg = f"Your request to join {event.title} has been accepted, yay!"
            send_notification(user_with_username,subject= "Request Access", msg= msg)
        else:
            optional_message = "Error: No user was found with that username!"

        return self.get_event_owner_view(request, event, files, optional_message)

    def post_upload_file(self, request, event):
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid() and 'file' in request.FILES:
            uploaded_file = request.FILES['file']
            title = form.cleaned_data['title']
            description = form.cleaned_data['description']
            keywords = form.cleaned_data['keywords']

            # Set up the S3 file path
            s3_path = f'uploads/{request.user.username}/{event.pk}/{uploaded_file.name}'
            content_type, _ = mimetypes.guess_type(uploaded_file.name)
            allowed_mime_types = ['image/png', 'image/jpeg', 'application/pdf', 'text/plain']

            # Validate file type
            if content_type not in allowed_mime_types:
                return self.get_event_owner_view(request, event, "Error: Invalid file type uploaded.")

            # Attempt to upload to S3
            try:
                s3.upload_fileobj(
                    uploaded_file,
                    settings.AWS_STORAGE_BUCKET_NAME,
                    s3_path,
                    ExtraArgs={
                        'ContentType': content_type or 'application/octet-stream',
                        'ContentDisposition': 'inline'
                    }
                )

                # Save EventFile instance only after successful S3 upload
                event_file = EventFile(
                    event=event,
                    user=request.user,
                    file=s3_path,
                    title=title,
                    description=description,
                    keywords=keywords
                )
                event_file.save()
                print(f"Uploaded file {uploaded_file.name} to S3 as {s3_path}")

                # Use HttpResponseRedirect to avoid form resubmission on page reload
                return HttpResponseRedirect(reverse('events:view_event', args=[event.pk]))

            except Exception as e:
                print(f"Failed to upload file to S3: {e}")

        # Error if form is invalid or no file is uploaded
        files = EventFile.objects.filter(event=event)
        return self.get_event_owner_view(request, event, files)

    def post_edit_file(self, request, event):
        # Retrieve file details from the form
        file_id = request.POST.get("file_id")
        edit_title = request.POST.get("edit_title")
        edit_description = request.POST.get("edit_description")
        edit_keywords = request.POST.get("edit_keywords")

        # Get the file object
        try:
            file_obj = EventFile.objects.get(id=file_id, event=event)
        except EventFile.DoesNotExist:
            return self.get_event_owner_view(request, event, "Error: File not found.")

        # Check if the user is the creator of the event
        if request.user == file_obj.user or request.user == event.creator:
            file_obj.title = edit_title
            file_obj.description = edit_description
            file_obj.keywords = edit_keywords
            file_obj.save()

            optional_message = "File metadata updated successfully."
        else:
            optional_message = "Error: You do not have permission to edit this file."

        files = EventFile.objects.filter(event=event)
        return self.get_event_owner_view(request, event, files, optional_message)

    def post_delete_comment(self, request, event):
        comment_pk = int(request.POST.get("comment_to_delete"))
        comment = Comment.objects.filter(pk=comment_pk)
        if comment.exists():
            comment = comment.first()
            if request.user.username == comment.user.username or request.user.username == event.creator.userame:
                comment.delete()

        files = EventFile.objects.filter(event=event)
        if event.creator.username == request.user.username:
            return self.get_event_owner_view(request, event, files, "Deleted comment.")
        else:
            return self.get_user_in_event_view(request, event, files, "Deleted comment.")


    def post_invite_user_form(self, request, event):
        invite_form = EventInviteUserForm(request.POST)
        files = EventFile.objects.filter(event=event)
        if invite_form.is_valid():
            invite_form.username = invite_form.cleaned_data['username']
            if invite_form.is_invite_valid(event):
                user_with_username = User.objects.get(username=invite_form.username)
                new_participant = EventParticipant(user=user_with_username, event=event, status="Invited", approved=True)
                new_participant.save()
                msg = f"You have been invited to join Event '{event.title}' by '{event.creator}!"
                send_notification(user_with_username, subject= "Invitation to join event", msg=msg)
                optional_message = f'Invited user "{invite_form.username}" to this event!'
            else:
                optional_message = invite_form.error
        else:
            optional_message = "Error: No user was found with that username!"

        return self.get_event_owner_view(request, event, files, optional_message)


def get_event(pk):
    try:
        return Event.objects.get(pk=pk)
    except ObjectDoesNotExist:
        return None


def delete_event_file(request, pk, file_id):
    event_file = get_object_or_404(EventFile, id = file_id)
    if request.user != event_file.user:
        return HttpResponse("You do not have permission to delete this file!")
    try:
        s3.delete_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=str(event_file.file)
        )
    except Exception as e:
        print(f"Error deleting file from S3: {e}")
        return HttpResponse("Error deleting file from S3.")
    event_file.delete()

    return redirect('events:view_event', pk=pk)


class CreateEventView(FormView):
    form_class = CreateEventForm
    template_name = "events/create_event.html"

    def form_valid(self, form):
        form.submit()
        return super().form_valid(form)


@login_required
def create_event(request):
    return render(request, 'events/create_event.html')


def submit_event(request):
    if not request.POST:
        return render(request, 'events/create_event.html')
    form = CreateEventForm(request.POST)
    if not request.user.is_authenticated:
        return redirect('/')
    if form.is_valid():
        user = request.user
        form_title = form.cleaned_data["title"]
        form_description = form.cleaned_data["description"]
        form_location = form.cleaned_data["location"]
        form_start_time = form.cleaned_data["start_time"]
        form_end_time = form.cleaned_data["end_time"]
        is_recurring = 'repeat_checkbox' in request.POST
        recurrence_frequency = form.cleaned_data.get("recurrence_frequency") if is_recurring else None
        recurrence_end = form.cleaned_data.get("recurrence_end") if is_recurring else None

        # Verify end date is after start date
        if form_start_time >= form_end_time:
            form.add_error("end_time", "End time must be after start time.")
            return render(request, 'events/create_event.html', {'form': form})

        event = Event.objects.create(
            title=form_title,
            description=form_description,
            location=form_location,
            start_time=form_start_time,
            end_time=form_end_time,
            is_recurring=is_recurring,
            recurrence_frequency=recurrence_frequency,
            recurrence_end=recurrence_end,
            creator=user,
        )
        event.save()

        # Create recurrence
        if is_recurring and recurrence_end:
            create_recurrence(event, recurrence_frequency, recurrence_end)

        return redirect('events:view_event', pk=event.pk)
    else:
        print("Invalid form! Here are the errors: ", form.errors)

    return render(request, 'events/create_event.html')


def create_recurrence(event, recurrence_frequency, recurrence_end):
    current_start_time = event.start_time
    current_end_time = event.end_time
    # Limit events
    count = 0
    # Only date matters, not time
    recurrence_end_date = recurrence_end.replace(hour=0, minute=0, second=0, microsecond=0)
    # Loop to create events until date is reached, limit of 30 events
    while current_start_time.date() <= recurrence_end_date.date() and count < 30:
        if recurrence_frequency == 'daily':
            current_start_time += relativedelta(days=1)
            current_end_time += relativedelta(days=1)
        elif recurrence_frequency == 'weekly':
            current_start_time += relativedelta(weeks=1)
            current_end_time += relativedelta(weeks=1)
        elif recurrence_frequency == 'monthly':
            current_start_time += relativedelta(months=1)
            current_end_time += relativedelta(months=1)
        elif recurrence_frequency == 'yearly':
            current_start_time += relativedelta(years=1)
            current_end_time += relativedelta(years=1)
        if current_start_time.date() > recurrence_end_date.date():
            break
        # Create a new event
        new_event = Event(
            title=event.title,
            description=event.description,
            location=event.location,
            start_time=current_start_time,
            end_time=current_end_time,
            creator=event.creator,
            is_recurring=True,
            recurrence_frequency=recurrence_frequency,
            recurrence_end=recurrence_end,
            recurrence_id=event.recurrence_id
        )
        new_event.save()


def get_next_recurrence(event):
    if not event.is_recurring or not event.recurrence_frequency:
        return None
    next_start_time = event.start_time
    next_end_time = event.end_time
    # Adjust the next start and end times based on recurrence frequency
    if event.recurrence_frequency == 'daily':
        next_start_time += timedelta(days=1)
        next_end_time += timedelta(days=1)
    elif event.recurrence_frequency == 'weekly':
        next_start_time += timedelta(weeks=1)
        next_end_time += timedelta(weeks=1)
    elif event.recurrence_frequency == 'monthly':
        next_start_time += relativedelta(months=1)
        next_end_time += relativedelta(months=1)
    elif event.recurrence_frequency == 'yearly':
        next_start_time += relativedelta(years=1)
        next_end_time += relativedelta(years=1)

    recurrence_end_date = event.recurrence_end.replace(hour=0, minute=0, second=0, microsecond=0)

    if recurrence_end_date and next_start_time.date() > recurrence_end_date.date():
        return None

    return next_start_time, next_end_time


def delete_all_future_occurrences(event):
    event_start_time = event.start_time
    event.delete()
    events_to_delete = Event.objects.filter(
        recurrence_id=event.recurrence_id,
        # Only delete events after the current event
        start_time__gt=event_start_time
    )
    events_to_delete.delete()
    return


