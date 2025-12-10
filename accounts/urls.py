# accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Profile URLs
    path('profile/', views.profile, name='profile'), # ดูโปรไฟล์ตัวเอง
    path('profile/edit/', views.edit_profile, name='edit_profile'), #ต้องอยู่ก่อน user_profile
    path('profile/<str:username>/', views.profile, name='user_profile'), # ดูโปรไฟล์คนอื่น
]