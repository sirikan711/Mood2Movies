# accounts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from .forms import SignUpForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # สมัครเสร็จ ล็อกอินให้เลย
            return redirect('home') # กลับหน้าแรก
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def profile(request, username=None):
    if username:
        user_obj = get_object_or_404(User, username=username)
    else:
        user_obj = request.user # ถ้าไม่ระบุชื่อ ให้ดูโปรไฟล์ตัวเอง

    # ดึงข้อมูลต่างๆ ของ User คนนี้มาแสดง
    recent_reviews = user_obj.reviews.all().order_by('-created_at')[:5]
    favorites = user_obj.favorites.all().order_by('-created_at')[:10]
    bookmarks = user_obj.bookmarks.all().order_by('-created_at')[:10]
    
    return render(request, 'accounts/profile.html', {
        'profile_user': user_obj,
        'recent_reviews': recent_reviews,
        'favorites': favorites,
        'bookmarks': bookmarks
    })