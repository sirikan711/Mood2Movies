# movies/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # หน้าค้นหา
    path('search/', views.search_movies, name='search_movies'),
    
    # หน้าแนะนำตามอารมณ์ (ใช้ int:mood_id)
    path('recommend/<int:mood_id>/', views.mood_recommendation, name='mood_recommendation'),

    # กลุ่ม URL ที่เกี่ยวกับหนัง (Movie Detail และ Actions)
    path('movie/<int:tmdb_id>/', views.movie_detail, name='movie_detail'),
    path('movie/<int:tmdb_id>/review/', views.add_review, name='add_review'),
    path('movie/<int:tmdb_id>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('movie/<int:tmdb_id>/bookmark/', views.toggle_bookmark, name='toggle_bookmark'),

    # Custom Admin URLs (เพิ่มส่วนนี้)
    path('custom-admin/', views.admin_dashboard, name='admin_dashboard'),
    path('custom-admin/movies/', views.admin_movies, name='admin_movies'),
    path('custom-admin/moods/', views.admin_moods, name='admin_moods'),
    # URL สำหรับลบข้อมูล (Delete Actions)
    path('custom-admin/movies/delete/<int:movie_id>/', views.admin_delete_movie, name='admin_delete_movie'),
    path('custom-admin/moods/delete/<int:mood_id>/', views.admin_delete_mood, name='admin_delete_mood'),
]