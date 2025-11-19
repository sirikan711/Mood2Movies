# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from movies.models import Profile

class SignUpForm(UserCreationForm):
    # เพิ่ม email เป็นฟิลด์บังคับ (Optional แต่แนะนำ)
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'w-full p-3 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500'}),
            'email': forms.EmailInput(attrs={'class': 'w-full p-3 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500'}),
            'first_name': forms.TextInput(attrs={'class': 'w-full p-3 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full p-3 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500'}),
        }

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'avatar']
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'w-full p-3 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500', 'rows': 3}),
            'avatar': forms.FileInput(attrs={'class': 'block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-yellow-500 file:text-gray-900 hover:file:bg-yellow-400'}),
        }