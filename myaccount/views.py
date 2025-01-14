from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .forms import *
from .models import *
from django.contrib.auth import logout
from events.models import *
import boto3
from django.utils import timezone
import os
import mimetypes
from .sms import *
# Create your views here.


def verify_phone_number(request):
    if not request.user.is_authenticated:
        return render(request, "myaccount/landingpage.html")
    if request.method == "POST":
        otp1 = request.POST.get("otp1")
        otp2 = request.POST.get("otp2")
        otp3 = request.POST.get("otp3")
        otp4 = request.POST.get("otp4")

        entered_code = f"{otp1}{otp2}{otp3}{otp4}"
        try:
            verification_record = VerifyPhoneNumber.objects.get(user=request.user)
            expected_code = verification_record.verification_code
            if entered_code == str(expected_code):
                verification_record.verified_number = True
                verification_record.save()
                return redirect("myaccount")
            else:
                return render(request, "myaccount/phone_verification", {"verify_error" : "Entered code did not match up! Please resend code or try again!"})
        except VerifyPhoneNumber.DoesNotExist:
            print("verify record doesnt exist")
    else: #sms verifying
        verified_num = VerifyPhoneNumber.objects.filter(user=request.user).first()
        if verified_num is not None:
            verified_num.verification_code = generate_verification_code()
            verified_num.save()
            send_verification_code(request.user.phone_number, verified_num.verification_code)
            return render(request, "myaccount/phone_verification.html")
def update_notification_settings(request):
    if not request.user.is_authenticated:
        return render(request, 'myaccount/notification_setup.html')
    if request.user.phone_number is None:
        return render(request, 'myaccount/notification_setup.html', {"notif_error": True})
    verified_num = VerifyPhoneNumber.objects.filter(user=request.user).first()
    if verified_num is None:
        return render(request,'myaccount',{"notif_error": True})
    if request.method == "POST":
        email_notif = request.POST.get("email_notifications") == "on"
        sms_notif = request.POST.get("sms_notifications") == "on"
        preferences, created = NotificationPreference.objects.get_or_create(user=request.user)
        preferences.email_notifications = email_notif
        preferences.sms_notifications = sms_notif
        preferences.save()
        
    preferences, created = NotificationPreference.objects.get_or_create(user=request.user)
    return render(request, 'myaccount/notification_setup.html', {
        'preferences': preferences
    })

def my_account(request):
    user = request.user
    if not user.is_authenticated:
        return render(request, 'myaccount/myaccount.html')
    profile_picture = ProfilePicture.objects.filter(user=user).first()
    verified_num = VerifyPhoneNumber.objects.filter(user=user).first()
    context = {"profile_picture": profile_picture , "verified": verified_num}
    return render(request, 'myaccount/myaccount.html', context)


def update_profile_info(request):
    user = request.user
    if not user.is_authenticated:
        return render(request, 'myaccount/myaccount.html')
    if request.method == "POST": #update form
        form = UpdateProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            user.username = username
            user.save()
            verify_phone,created = VerifyPhoneNumber.objects.get_or_create(user = user)
            profile_picture = ProfilePicture.objects.filter(user=user).first()
            current_phone = request.user.phone_number
            new_phone_number = form.cleaned_data.get("phone_number")
            print(f"{verify_phone.verified_number}")
            if current_phone != new_phone_number:
                generate_code = generate_verification_code()
                verify_phone.verification_code = generate_code
                verify_phone.verified_number = False
                verify_phone.save()
                form.save()
            else:
                verify_phone.verified_number = verify_phone.verified_number
                verify_phone.save()
            return render(request, 'myaccount/myaccount.html', {"profile_picture": profile_picture, "verified": verify_phone})
        else:
            print("invalid form")
    else: #redirect with context to account with update profile view
        form = UpdateProfileForm(instance=request.user)
    profile_picture = ProfilePicture.objects.filter(user=user).first()
    context = {"update_profile_info": True, "form": form, "profile_picture" : profile_picture}
    return render(request, 'myaccount/myaccount.html', context)


def update_profile(request):
    form = ProfilePictureUpdateForm(request.POST, request.FILES)
    if 'file' not in request.FILES:
        return redirect('myaccount')
    if form.is_valid and 'file' in request.FILES:
        uploaded_file = request.FILES['file']
        s3_path = f'profile/{request.user.id}/{uploaded_file.name}'
        content_type, _ = mimetypes.guess_type(uploaded_file.name)
        allowed_mime_types = ['image/png', 'image/jpeg']
        allowed_extensions = ['.png', '.jpg', '.jpeg', '.jfif']
        file_extension = os.path.splitext(uploaded_file.name)[-1].lower()
        if content_type not in allowed_mime_types or file_extension not in allowed_extensions:
            context = {'file_error_msg': "Error: Only PNG, JPG, JPEG, and JFIF files are allowed!"}
            return render(request, 'myaccount/myaccount.html', context)
        try:
            s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
            )
            try:
                profile_file = ProfilePicture.objects.get(user=request.user)
                old_s3_path = profile_file.profile_picture
                s3.delete_object(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    Key=str(old_s3_path),
                )
            except ProfilePicture.DoesNotExist:
                profile_file = ProfilePicture(user=request.user)

            s3.upload_fileobj(
                uploaded_file,
                settings.AWS_STORAGE_BUCKET_NAME,
                s3_path,
                ExtraArgs={
                    'ContentType': content_type or 'application/octet-stream',
                    'ContentDisposition': 'inline'
                }
            )
            profile_file.profile_picture = s3_path
            profile_file.save()
            context = {"profile_picture": profile_file}
            return render(request, "myaccount/myaccount.html", context = context)

        except Exception as e:
            print(f"Failed to upload file to S3: {e}")

def landing_page(request):
    def get_upcoming_events(val):
        events_info = []
        if val == 2:
            event_participants = EventParticipant.objects.filter(user=request.user)
        else:
            event_participants = EventParticipant.objects.filter(user=request.user, event__start_time__gte=timezone.now()).order_by('event__start_time')[:5]
        for event_participant in event_participants:
            status = event_participant.status
            event_title = event_participant.event.title
            event_pk = event_participant.event.pk
            events_info.append({
                "status": status,
                "title": event_title,
                "event_pk": event_pk,
            })
        return events_info
    def get_my_events(val):
        my_events_list= []
        if val == 1:
            my_events = Event.objects.filter(creator = request.user)
        else:
            my_events = Event.objects.filter(creator = request.user)[:5]
        for event in my_events:
            title = event.title
            location = event.location
            start_time = event.start_time
            end_time = event.end_time
            event_pk = event.pk
            my_events_list.append({"title": title, 
                                   "location": location, 
                                   "start_time": start_time, 
                                   "end_time": end_time,
                                   'pk': event_pk
                                   })
        return my_events_list

    if request.user.is_authenticated:
        key_value = request.GET.get('key')
        if key_value is None:
            key_value = 0
        else:
            key_value = int(key_value)
        upcoming_events = get_upcoming_events(key_value)
        my_events = get_my_events(key_value)
        context = {"upcoming_events": upcoming_events, "my_events": my_events}
        return render(request, 'myaccount/landingpage.html', context)

    return render(request, 'myaccount/landingpage.html')

@login_required
def user_info(request):
    user = request.user
    user_data = {
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
    }
    return JsonResponse(user_data)
@login_required
def redirect_after_login(request):
    user = request.user
    user.refresh_from_db()
    if user.username is None or int(user.role) == 0:  
        return redirect('account_setup') 
    return redirect('myaccount')  
@login_required

def account_setup(request):
    user = request.user
    if user.username and int(user.role) != 0: #user exists, log in
        return redirect('myaccount')

    if request.method == 'POST':
        form = UpdateProfileForm(request.POST, instance=user)
        if form.is_valid():
            verify_phone,created= VerifyPhoneNumber.objects.get_or_create(user = user)
            verify_phone.verification_code = generate_verification_code()
            verify_phone.save()
            user.role = 1
            form.save()  
            return redirect('myaccount')  
        else:
            print("form is not valid. errors: ", form.errors)
    else:
        form = UpdateProfileForm(instance=user) 

    return render(request, 'myaccount/account_setup.html', {'form': form})

@login_required
def delete_account(request):
    if request.method == "POST":
        user = request.user
        user.delete() 
        return handle_logout(request)  

    return redirect('myaccount')  # return to myaccount if accessed without POST

def handle_logout(request):
    logout(request)
    request.session.flush()
    response = redirect('/')
    response.delete_cookie('sessionid') 
    response.delete_cookie('csrftoken')  
    return response


def store_refresh_token(social_account, refresh_token):
    if refresh_token:
        social_account.extra_data['refresh_token'] = refresh_token
        social_account.save()
