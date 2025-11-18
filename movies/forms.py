# movies/forms.py
from django import forms
from .models import Review, Mood

class ReviewForm(forms.ModelForm):
    # ปรับแต่ง Widget ให้น่าใช้ขึ้น
    primary_mood = forms.ModelChoiceField(
        queryset=Mood.objects.all(),
        empty_label="เลือกอารมณ์หลักที่รู้สึก...",
        widget=forms.Select(attrs={'class': 'w-full p-2 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500'})
    )
    mood_intensity = forms.IntegerField(
        min_value=1, max_value=5,
        widget=forms.NumberInput(attrs={'type': 'range', 'min': '1', 'max': '5', 'class': 'w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer', 'step': '1'})
    )
    rating = forms.FloatField(
        min_value=0, max_value=10,
        widget=forms.NumberInput(attrs={'class': 'w-full p-2 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500', 'placeholder': '0.0 - 10.0'})
    )
    review_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'w-full p-3 rounded bg-gray-700 text-white border border-gray-600 focus:border-yellow-500', 'placeholder': 'เล่าความรู้สึกของคุณเพิ่มเติม (ไม่บังคับ)...'}),
        required=False
    )

    class Meta:
        model = Review
        fields = ['primary_mood', 'mood_intensity', 'rating', 'review_text']