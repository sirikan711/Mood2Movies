from django.urls import path
from . import views

urlpatterns = [
    # --- 1. ระบบค้นหาและแนะนำ ---
    path('search/', views.search_movies, name='search_movies'),
    path('recommend/<int:mood_id>/', views.mood_recommendation, name='mood_recommendation'),

    # --- 2. จัดการภาพยนตร์ ---
    path('movie/<int:tmdb_id>/', views.movie_detail, name='movie_detail'),
    path('movie/<int:tmdb_id>/review/', views.add_review, name='add_review'),
    path('movie/<int:tmdb_id>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('movie/<int:tmdb_id>/bookmark/', views.toggle_bookmark, name='toggle_bookmark'),

    # --- 3. จัดการรีวิวส่วนตัว ---
    path('review/edit/<int:review_id>/', views.edit_review, name='edit_review'),
    path('review/delete/<int:review_id>/', views.delete_review, name='delete_review'),

    # --- 4. Custom Admin Dashboard ---
    path('custom-admin/', views.admin_dashboard, name='admin_dashboard'),
    path('custom-admin/movies/', views.admin_movies, name='admin_movies'),
    path('custom-admin/movies/delete/<int:movie_id>/', views.admin_delete_movie, name='admin_delete_movie'),
    path('custom-admin/moods/', views.admin_moods, name='admin_moods'),
    path('custom-admin/moods/delete/<int:mood_id>/', views.admin_delete_mood, name='admin_delete_mood'),
    path('custom-admin/reviews/', views.admin_reviews, name='admin_reviews'),
    path('custom-admin/reviews/delete/<int:review_id>/', views.admin_delete_review, name='admin_delete_review'),
]