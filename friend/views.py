from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from myaccount.models import ProfilePicture
from .forms import InviteUserForm
from .models import Friend
from django.contrib.auth import get_user_model
from django.db.models import Q
from collections import defaultdict

from events.models import Event 


User = get_user_model()

@login_required
def friends_page(request):
    user = request.user
    all_users = User.objects.exclude(id=user.id)

    friends = Friend.objects.filter(
        Q(from_user=user) | Q(to_user=user),
        status=Friend.STATUS_ACCEPTED
    )

    pending_requests = Friend.objects.filter(to_user=user, status=Friend.STATUS_PENDING)
    sent_requests = Friend.objects.filter(from_user=user, status=Friend.STATUS_PENDING)

    friend_ids = {friend.to_user.id if friend.from_user == user else friend.from_user.id for friend in friends}
    sent_request_ids = {req.to_user.id for req in sent_requests}
    pending_request_ids = {req.from_user.id for req in pending_requests}

    all_events = Event.objects.all().order_by('start_time')
    
    profile_pictures = ProfilePicture.objects.filter(user__in=all_users)
    profile_picture_map = {profile_picture.user.id: profile_picture.get_file_url() for profile_picture in profile_pictures} 

    msg = None
    form = InviteUserForm(user=user)

    if request.method == "POST":
        action = request.POST.get("action")
        target_user_id = request.POST.get("user_id") or request.POST.get("friend_id") or request.POST.get("invitee_id")

        try:
            target_user = User.objects.get(id=target_user_id)
            if action == "send_request":
                if not Friend.objects.filter(from_user=user, to_user=target_user).exists():
                    Friend.objects.create(from_user=user, to_user=target_user, status=Friend.STATUS_PENDING)
                    msg = f"Friend request sent to {target_user.username}."
                else:
                    msg = "Friend request already sent."

            elif action == "remove_friend":
                # Remove a friend
                Friend.objects.filter(
                    Q(from_user=user, to_user=target_user) | Q(from_user=target_user, to_user=user),
                    status=Friend.STATUS_ACCEPTED
                ).delete()
                msg = f"Removed {target_user.username} from friends."

            elif action == "accept_request":
                friend_request = Friend.objects.filter(from_user=target_user, to_user=user, status=Friend.STATUS_PENDING).first()
                if friend_request:
                    friend_request.status = Friend.STATUS_ACCEPTED
                    friend_request.save()
        
                    # Create reciprocal friendship entry
                    Friend.objects.create(from_user=user, to_user=target_user, status=Friend.STATUS_ACCEPTED)
                    msg = f"Friend request from {target_user.username} accepted."
                else:
                    msg = "The friend request no longer exists or was already processed."
            elif action == "reject_request":
                Friend.objects.filter(from_user=target_user, to_user=user, status=Friend.STATUS_PENDING).delete()
                msg = f"Friend request from {target_user.username} rejected."

            elif action == "cancel_request":
                # Cancel a sent friend request
                Friend.objects.filter(from_user=user, to_user=target_user, status=Friend.STATUS_PENDING).delete()
                msg = f"Friend request to {target_user.username} canceled."

        except User.DoesNotExist:
            msg = "User not found."

        return redirect('friends')

    return render(request, "friend/friends.html", {
        "all_users": all_users,
        "friend_ids": friend_ids,
        "sent_request_ids": sent_request_ids,
        "pending_request_ids": pending_request_ids,
        "form": form,
        "message": msg,
        "all_events": all_events,
        "profile_picture_map": profile_picture_map
    })