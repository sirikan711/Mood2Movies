# movies/views.py
import datetime
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Avg, Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .utils import search_movies_tmdb, get_movie_details_tmdb, get_tmdb_genres
from .models import Movie, Review, Mood, Favorite, Bookmark
from .forms import ReviewForm
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User

def search_movies(request):
    query = request.GET.get('q', '').strip()
    mood_id = request.GET.get('mood')
    year = request.GET.get('year')
    genre_id = request.GET.get('genre') # รับค่า Genre ID

    movies = []
    search_source = ""

    # Case 1: เลือก Mood (ค้นจาก Local DB) -> **ยังไม่รองรับ Genre Filter** (เพราะใน DB เรายังไม่ได้เก็บ Genre)
    if mood_id:
        search_source = "local"
        mood = get_object_or_404(Mood, id=mood_id)
        movies_qs = Movie.objects.filter(reviews__primary_mood=mood).distinct()
        
        if query:
            movies_qs = movies_qs.filter(title__icontains=query)
        if year:
            movies_qs = movies_qs.filter(release_date__year=year)
            
        for m in movies_qs:
            movies.append({
                'tmdb_id': m.tmdb_id,
                'title': m.title,
                'release_date': str(m.release_date) if m.release_date else 'N/A',
                'poster_url': f"https://image.tmdb.org/t/p/w500{m.poster_path}" if m.poster_path else None,
                'overview': m.overview,
                'local_rating': m.reviews.aggregate(Avg('rating'))['rating__avg']
            })

    # Case 2: ค้นหาทั่วไป (TMDb) -> รองรับ Query, Year, Genre
    elif query or genre_id or year:
        search_source = "tmdb"
        # ส่ง genre_id ไปให้ฟังก์ชันค้นหาด้วย
        movies = search_movies_tmdb(query, year=year, genre_id=genre_id)

    # เตรียมข้อมูล Dropdown
    moods = Mood.objects.all()
    tmdb_genres = get_tmdb_genres() # ดึงประเภทหนังจาก TMDb
    
    current_year = datetime.date.today().year
    years = range(current_year, 1979, -1)

    return render(request, 'movies/search.html', {
        'movies': movies,
        'query': query,
        'moods': moods,
        'tmdb_genres': tmdb_genres, # ส่งไป Template
        'years': years,
        'selected_mood': int(mood_id) if mood_id else None,
        'selected_year': int(year) if year else None,
        'selected_genre': int(genre_id) if genre_id else None, # ส่งค่าที่เลือกกลับไป
        'search_source': search_source
    })

def movie_detail(request, tmdb_id):
    movie = Movie.objects.filter(tmdb_id=tmdb_id).first()
    tmdb_data = get_movie_details_tmdb(tmdb_id)
    
    if not tmdb_data:
        return render(request, '404.html')
    
    reviews = []
    is_favorited = False
    is_bookmarked = False

    if movie:
        reviews = movie.reviews.all().order_by('-created_at')
        if request.user.is_authenticated:
            is_favorited = Favorite.objects.filter(user=request.user, movie=movie).exists()
            is_bookmarked = Bookmark.objects.filter(user=request.user, movie=movie).exists()

    context = {
        'movie_db': movie,
        'movie_tmdb': tmdb_data,
        'reviews': reviews,
        'is_favorited': is_favorited,
        'is_bookmarked': is_bookmarked,
    }
    return render(request, 'movies/detail.html', context)

@login_required
def add_review(request, tmdb_id):
    movie = Movie.objects.filter(tmdb_id=tmdb_id).first()
    if not movie:
        tmdb_data = get_movie_details_tmdb(tmdb_id)
        if tmdb_data:
            movie = Movie.objects.create(
                tmdb_id=tmdb_data['tmdb_id'],
                title=tmdb_data['title'],
                poster_path=tmdb_data['poster_path'],
                overview=tmdb_data.get('overview', ''),
                release_date=tmdb_data.get('release_date')
            )
        else:
            messages.error(request, 'ไม่พบข้อมูลภาพยนตร์')
            return redirect('home')

    existing_review = Review.objects.filter(user=request.user, movie=movie).first()
    if existing_review:
        messages.warning(request, 'คุณเคยรีวิวหนังเรื่องนี้ไปแล้ว')
        return redirect('movie_detail', tmdb_id=tmdb_id)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.movie = movie
            review.save()
            messages.success(request, 'บันทึกอารมณ์ของคุณเรียบร้อยแล้ว!')
            return redirect('movie_detail', tmdb_id=tmdb_id)
    else:
        form = ReviewForm()

    return render(request, 'movies/add_review.html', {'form': form, 'movie': movie})

def mood_recommendation(request, mood_id):
    mood = get_object_or_404(Mood, id=mood_id)
    recommended_movies = Movie.objects.filter(
        reviews__primary_mood=mood
    ).annotate(
        mood_count=Count('reviews', filter=Q(reviews__primary_mood=mood)),
        avg_intensity=Avg('reviews__mood_intensity', filter=Q(reviews__primary_mood=mood))
    ).annotate(
        mood_score=models.F('mood_count') * models.F('avg_intensity')
    ).order_by('-mood_score')[:20]

    return render(request, 'movies/recommendation.html', {
        'mood': mood,
        'movies': recommended_movies
    })

# --- Custom Action Views ---
@login_required
@require_POST
def toggle_favorite(request, tmdb_id):
    movie = Movie.objects.filter(tmdb_id=tmdb_id).first()
    if not movie:
        tmdb_data = get_movie_details_tmdb(tmdb_id)
        if tmdb_data:
            movie = Movie.objects.create(
                tmdb_id=tmdb_data['tmdb_id'],
                title=tmdb_data['title'],
                poster_path=tmdb_data['poster_path'],
                overview=tmdb_data.get('overview', ''),
                release_date=tmdb_data.get('release_date')
            )
        else:
            return JsonResponse({'status': 'error', 'message': 'Movie not found'}, status=404)

    fav, created = Favorite.objects.get_or_create(user=request.user, movie=movie)
    if not created:
        fav.delete()
        status = 'removed'
    else:
        status = 'added'

    return JsonResponse({'status': status})

@login_required
@require_POST
def toggle_bookmark(request, tmdb_id):
    movie = Movie.objects.filter(tmdb_id=tmdb_id).first()
    if not movie:
        tmdb_data = get_movie_details_tmdb(tmdb_id)
        if tmdb_data:
            movie = Movie.objects.create(
                tmdb_id=tmdb_data['tmdb_id'],
                title=tmdb_data['title'],
                poster_path=tmdb_data['poster_path'],
                overview=tmdb_data.get('overview', ''),
                release_date=tmdb_data.get('release_date')
            )
        else:
            return JsonResponse({'status': 'error', 'message': 'Movie not found'}, status=404)

    bookmark, created = Bookmark.objects.get_or_create(user=request.user, movie=movie)
    if not created:
        bookmark.delete()
        status = 'removed'
    else:
        status = 'added'

    return JsonResponse({'status': status})

# --- Custom Admin Views ---
@staff_member_required(login_url='login') # บังคับว่าเป็น Staff/Superuser เท่านั้น
def admin_dashboard(request):
    # ข้อมูลสรุปเบื้องต้น
    total_movies = Movie.objects.count()
    total_reviews = Review.objects.count()
    total_users = User.objects.count()
    recent_reviews = Review.objects.order_by('-created_at')[:5]
    
    return render(request, 'movies/admin/dashboard.html', {
        'total_movies': total_movies,
        'total_reviews': total_reviews,
        'total_users': total_users,
        'recent_reviews': recent_reviews
    })

@staff_member_required(login_url='login')
def admin_movies(request):
    movies = Movie.objects.all().order_by('-id') # เรียงจากใหม่ไปเก่า
    
    # ถ้ามีการค้นหา
    query = request.GET.get('q')
    if query:
        movies = movies.filter(title__icontains=query)
        
    return render(request, 'movies/admin/movies.html', {'movies': movies, 'query': query})

@staff_member_required(login_url='login')
def admin_moods(request):
    moods = Mood.objects.all()
    
    # Logic เพิ่ม/แก้ไข Mood แบบง่ายๆ (ในหน้าเดียวกัน)
    if request.method == 'POST':
        mood_name = request.POST.get('mood_name')
        mood_id = request.POST.get('mood_id')
        
        if mood_id: # แก้ไข
            mood = get_object_or_404(Mood, id=mood_id)
            mood.name = mood_name
            mood.save()
            messages.success(request, f'อัปเดตอารมณ์ "{mood_name}" เรียบร้อย')
        else: # เพิ่มใหม่
            Mood.objects.create(name=mood_name)
            messages.success(request, f'เพิ่มอารมณ์ "{mood_name}" เรียบร้อย')
            
        return redirect('admin_moods')
        
    return render(request, 'movies/admin/moods.html', {'moods': moods})

@staff_member_required(login_url='login')
def admin_delete_movie(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    movie.delete()
    messages.success(request, 'ลบภาพยนตร์เรียบร้อยแล้ว')
    return redirect('admin_movies')

@staff_member_required(login_url='login')
def admin_delete_mood(request, mood_id):
    mood = get_object_or_404(Mood, id=mood_id)
    mood.delete()
    messages.success(request, 'ลบอารมณ์เรียบร้อยแล้ว')
    return redirect('admin_moods')