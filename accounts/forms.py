from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from movies.models import Profile

class SignUpForm(UserCreationForm):
    # เพิ่ม email และปรับ label/help_text เป็นภาษาไทย
    email = forms.EmailField(
        max_length=254, 
        label='อีเมล',
        help_text='จำเป็นต้องกรอก โปรดระบุอีเมลที่ถูกต้อง',
        widget=forms.EmailInput(attrs={'class': 'w-full p-3 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
        # แปลชื่อฟิลด์ที่มาจาก Model
        labels = {
            'username': 'ชื่อผู้ใช้',
            'first_name': 'ชื่อจริง',
            'last_name': 'นามสกุล',
        }
        # แปลคำอธิบาย (Help Text)
        help_texts = {
            'username': 'จำเป็นต้องกรอก ห้ามเกิน 150 ตัวอักษร ใช้ได้เฉพาะตัวอักษรภาษาอังกฤษ ตัวเลข และเครื่องหมาย @/./+/-/_ เท่านั้น',
        }
        # เพิ่ม Widget ให้กับ field ปกติของ User model ให้สวยงาม
        widgets = {
            'username': forms.TextInput(attrs={'class': 'w-full p-3 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500'}),
            'first_name': forms.TextInput(attrs={'class': 'w-full p-3 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full p-3 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # แก้ไข Label ของรหัสผ่านที่ติดมาจาก UserCreationForm (ซึ่งไม่ได้อยู่ใน Meta)
        if 'password1' in self.fields:
            self.fields['password1'].label = "รหัสผ่าน"
            self.fields['password1'].help_text = "<ul><li>รหัสผ่านของคุณไม่ควรคล้ายกับข้อมูลส่วนตัวอื่น ๆ</li><li>รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร</li><li>รหัสผ่านไม่ควรเป็นรหัสที่ใช้กันบ่อยเกินไป</li><li>รหัสผ่านไม่ควรเป็นตัวเลขล้วน ๆ</li></ul>"
            # ใส่ class ให้ password field ด้วย
            self.fields['password1'].widget.attrs.update({'class': 'w-full p-3 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500'})
        if 'password2' in self.fields:
            self.fields['password2'].label = "ยืนยันรหัสผ่าน"
            self.fields['password2'].help_text = "กรอกรหัสผ่านเหมือนเดิมอีกครั้งเพื่อยืนยัน"
            self.fields['password2'].widget.attrs.update({'class': 'w-full p-3 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500'})

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(label='อีเมล')

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        labels = {
            'username': 'ชื่อผู้ใช้',
            'first_name': 'ชื่อจริง',
            'last_name': 'นามสกุล',
        }
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
        labels = {
            'bio': 'เกี่ยวกับฉัน',
            'avatar': 'รูปโปรไฟล์',
        }
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'w-full p-3 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500', 'rows': 3}),
            'avatar': forms.FileInput(attrs={
                'class': 'block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-yellow-500 file:text-gray-900 hover:file:bg-yellow-400',
                'accept': 'image/*'  # <-- สำคัญ: บังคับให้ Browser เลือกได้เฉพาะไฟล์รูป
            }),
        }

    # เพิ่มฟังก์ชันตรวจสอบไฟล์ (กันไฟล์ใหญ่หรือไฟล์มั่ว)
    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            # ตรวจสอบขนาดไฟล์ (ถ้าเป็นไฟล์ใหม่ที่เพิ่งอัปโหลด)
            if hasattr(avatar, 'size'): 
                if avatar.size > 5 * 1024 * 1024: # จำกัดที่ 5MB
                    raise forms.ValidationError("ไฟล์รูปภาพมีขนาดใหญ่เกินไป (ต้องไม่เกิน 5MB)")
                
                # ตรวจสอบนามสกุลไฟล์
                if not avatar.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                     raise forms.ValidationError("รองรับเฉพาะไฟล์รูปภาพ (JPG, PNG, GIF, WebP)")
                     
        return avatar