
from django.core.mail import send_mail
from django.conf import settings
import requests


import random

from myaccount.models import NotificationPreference


def sms_msg(subject, msg):
    return f"Cavalier Connect- {subject}:\n{msg}"

def send_notification(user, subject, msg):
        if user.is_authenticated:
            pref,created = NotificationPreference.objects.get_or_create(user = user)
            email_pref = pref.email_notifications
            sms_pref = pref.sms_notifications
            if user.email and email_pref:
                send_mail(subject, msg, settings.NOTIFICATION_EMAIL,[user.email],fail_silently=False)
            if user.phone_number and sms_pref:
                send_sms(user.phone_number, subject, msg)


def send_sms(to_phone_number ,subject, msg):

    send_msg = sms_msg(subject, msg)
    print(f"sending {to_phone_number} from cavalier-connect: {send_msg} ")
    resp = requests.post('https://textbelt.com/text', {
        'phone': to_phone_number,
        'message': send_msg,
        'key': settings.TEXTBELT_API_KEY,
    })
    print(resp.json())


def send_verification_code(phone_num, code):
     send_sms(phone_num, "Verification", f"Here is your code: {code}")
def generate_verification_code():
    return random.randint(1000, 9999)