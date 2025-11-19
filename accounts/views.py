from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import SignUpForm, UserUpdateForm, ProfileUpdateForm

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def profile(request, username=None):
    if username:
        user_obj = get_object_or_404(User, username=username)
    else:
        user_obj = request.user

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

@login_required
def edit_profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'อัปเดตข้อมูลโปรไฟล์เรียบร้อยแล้ว!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    return render(request, 'accounts/edit_profile.html', {
        'u_form': u_form,
        'p_form': p_form
    })