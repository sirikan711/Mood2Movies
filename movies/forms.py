from django import forms
from .models import Review, Mood, CustomList

class MoodModelChoiceField(forms.ModelChoiceField):
    """Custom field to display Emoji in dropdown"""
    def label_from_instance(self, obj):
        # Logic เดียวกับใน Model __str__ แต่ทำเผื่อไว้ถ้า Model เปลี่ยน
        emoji = ''
        if 'Happy' in obj.name: emoji = '😊'
        elif 'Sad' in obj.name: emoji = '😭'
        elif 'Scary' in obj.name: emoji = '😨'
        elif 'Surprised' in obj.name: emoji = '😲'
        elif 'Heartwarming' in obj.name: emoji = '🥰'
        elif 'Tense' in obj.name: emoji = '😬'
        elif 'Funny' in obj.name: emoji = '🤣'
        elif 'Relaxing' in obj.name: emoji = '😌'
        else: emoji = '🎬'
        return f"{emoji} {obj.name}"

class ReviewForm(forms.ModelForm):
    primary_mood = MoodModelChoiceField(
        queryset=Mood.objects.all(),
        empty_label="เลือกอารมณ์หลักที่รู้สึก...",
        widget=forms.Select(attrs={
            'class': 'w-full p-3 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500 focus:ring-1 focus:ring-yellow-500'
        })
    )
    
    mood_intensity = forms.IntegerField(
        min_value=1, max_value=5,
        widget=forms.NumberInput(attrs={
            'type': 'range', 
            'min': '1', 
            'max': '5', 
            'class': 'w-full h-2 bg-gray-600 rounded-lg appearance-none cursor-pointer accent-yellow-500', 
            'step': '1'
        })
    )
    
    rating = forms.FloatField(
        min_value=0, max_value=10,
        widget=forms.NumberInput(attrs={
            'class': 'w-full p-3 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500', 
            'placeholder': '0.0 - 10.0'
        })
    )
    
    review_text = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4, 
            'class': 'w-full p-3 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500', 
            'placeholder': 'เล่าความรู้สึกของคุณเพิ่มเติม (ไม่บังคับ)...'
        }),
        required=False
    )

    class Meta:
        model = Review
        fields = ['primary_mood', 'mood_intensity', 'rating', 'review_text']

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