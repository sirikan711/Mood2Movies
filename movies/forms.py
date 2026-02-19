from django import forms
from .models import Review, Mood, CustomList

class ReviewForm(forms.ModelForm):
    # ลบ primary_mood และ mood_intensity ออก 
    # เพราะเราจัดการ inputs เหล่านั้นด้วย Slider HTML และ Logic ใน Views แทนแล้ว
    
    # เปลี่ยนชื่อจาก review_text เป็น comment ให้ตรงกับ Model ใหม่
    comment = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4, 
            'class': 'w-full p-3 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500', 
            'placeholder': 'เล่าความรู้สึกของคุณเพิ่มเติม (ไม่บังคับ)...'
        }),
        required=False,
        label="ความคิดเห็น"
    )

    class Meta:
        model = Review
        fields = ['comment'] # เหลือแค่ฟิลด์นี้ที่ต้องจัดการผ่าน Form

class CustomListForm(forms.ModelForm):
    class Meta:
        model = CustomList
        fields = ['name', 'description', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full p-3 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500', 'placeholder': 'ชื่อรายการ (เช่น หนังรัก 2024)'}),
            'description': forms.Textarea(attrs={'class': 'w-full p-3 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500', 'rows': 3, 'placeholder': 'รายละเอียด (ไม่บังคับ)'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-yellow-500 bg-gray-700 border-gray-600 rounded focus:ring-yellow-500 focus:ring-2'})
        }
        labels = {
            'name': 'ชื่อรายการ',
            'description': 'คำอธิบาย',
            'is_public': 'เผยแพร่เป็นสาธารณะ (คนอื่นเห็นได้)',
        }