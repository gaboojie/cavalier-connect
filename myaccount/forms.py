from django import forms
from .models import User
import re
class ProfilePictureUpdateForm(forms.Form):
    file = forms.FileField()
    
class UpdateProfileForm(forms.ModelForm):
    class Meta:
        model = User  
        fields = ['username', 'phone_number']
    
    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        phone_number = cleaned_data.get("phone_number")
        self.check_username(username)
        self.check_phone_number(phone_number)
        return cleaned_data
    
    def check_username(self, username):
        if not username:
            self.add_error("username", "Username cannot be empty!")
            return
        if username is None or len(username) < 6:
            self.add_error("username", "Username must be greater than 6 characters!")
            return
        if not re.match(r'^[a-zA-Z0-9]+$', username):
            self.add_error("username", "Username can only contain letters and numbers, no spaces or special characters!")
            return
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            self.add_error("username", "This username is already in use!")
            return

    def check_phone_number(self, pn):
        if pn:
            if len(pn) != 10:
                self.add_error("phone_number", "Mobile number must be 10 digits long!")
                return
            if User.objects.filter(phone_number=pn).exclude(pk=self.instance.pk).exists():
                self.add_error("phone_number", "This mobile number is already in use by another account!")
                return
            pattern = r'^\d{10}$'
            if not re.match(pattern, pn):
                self.add_error("phone_number", "Mobile number must contain only digits!")
                return

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user