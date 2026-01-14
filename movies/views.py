import datetime
import calendar

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Count, Avg, Q, F, FloatField, ExpressionWrapper
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from datetime import date, timedelta

from .models import Movie, Review, Mood, Favorite, Bookmark, CustomList
from .forms import ReviewForm, CustomListForm
from .utils import search_movies_tmdb, get_movie_details_tmdb, get_tmdb_genres, get_movies_in_date_range

# ==========================================
# 1. PUBLIC VIEWS (ค้นหา, รายละเอียด, แนะนำ)
# ==========================================

def search_movies(request):
    """ค้นหาภาพยนตร์ (รองรับชื่อ, อารมณ์, ปี, ประเภท)"""
    query = request.GET.get('q', '').strip()
    mood_id = request.GET.get('mood')
    year = request.GET.get('year')
    genre_id = request.GET.get('genre')

    movies = []
    search_source = ""

    # Case 1: ค้นหาจาก Local DB (เมื่อมีการเลือก Mood)
    if mood_id:
        search_source = "local"
        mood = get_object_or_404(Mood, id=mood_id)
        movies_qs = Movie.objects.filter(reviews__primary_mood=mood).distinct()
        
        if query:
            movies_qs = movies_qs.filter(title__icontains=query)
        if year:
            movies_qs = movies_qs.filter(release_date__year=year)
            
        for m in movies_qs:
            # คำนวณ Rating เฉลี่ยจากรีวิวในระบบเรา
            local_rating = m.reviews.aggregate(Avg('rating'))['rating__avg']
            
            movies.append({
                'tmdb_id': m.tmdb_id,
                'title': m.title,
                'release_date': str(m.release_date) if m.release_date else 'N/A',
                'poster_url': f"https://image.tmdb.org/t/p/w500{m.poster_path}" if m.poster_path else None,
                'overview': m.overview,
                'local_rating': local_rating
            })

    # Case 2: ค้นหาจาก TMDb API (เมื่อไม่มี Mood)
    elif query or genre_id or year:
        search_source = "tmdb"
        movies = search_movies_tmdb(query, year=year, genre_id=genre_id)

    # เตรียมข้อมูลสำหรับ Dropdown
    moods = Mood.objects.all()
    tmdb_genres = get_tmdb_genres()
    current_year = datetime.date.today().year
    years = range(current_year, 1979, -1)

    return render(request, 'movies/search.html', {
        'movies': movies,
        'query': query,
        'moods': moods,
        'tmdb_genres': tmdb_genres,
        'years': years,
        'selected_mood': int(mood_id) if mood_id else None,
        'selected_year': int(year) if year else None,
        'selected_genre': int(genre_id) if genre_id else None,
        'search_source': search_source
    })

def movie_detail(request, tmdb_id):
    """แสดงรายละเอียดภาพยนตร์และรีวิว (อัปเดตใหม่ รองรับ List)"""
    movie = Movie.objects.filter(tmdb_id=tmdb_id).first()
    tmdb_data = get_movie_details_tmdb(tmdb_id)
    
    if not tmdb_data:
         return render(request, '404.html')
    
    reviews = []
    is_favorited = False
    is_bookmarked = False
    user_lists = [] # เตรียมตัวแปรไว้เก็บ List ของ User

    if movie:
        reviews = movie.reviews.select_related('user', 'user__profile', 'primary_mood').order_by('-created_at')
        
        if request.user.is_authenticated:
            is_favorited = Favorite.objects.filter(user=request.user, movie=movie).exists()
            is_bookmarked = Bookmark.objects.filter(user=request.user, movie=movie).exists()
            
            # ดึง List ทั้งหมดของ User พร้อมเช็คว่าหนังเรื่องนี้อยู่ใน List นั้นหรือยัง
            user_lists = request.user.custom_lists.all().annotate(
                has_movie=Count('movies', filter=Q(movies__id=movie.id))
            )
    elif request.user.is_authenticated:
        # ถ้าหนังยังไม่มีใน DB เรา (แต่ User ล็อกอินอยู่) ก็ดึง List มาแสดงได้ (แต่สถานะ has_movie เป็น 0 หมด)
        user_lists = request.user.custom_lists.all()

    context = {
        'movie_db': movie,
        'movie_tmdb': tmdb_data,
        'reviews': reviews,
        'is_favorited': is_favorited,
        'is_bookmarked': is_bookmarked,
        'user_lists': user_lists, # ส่ง List ไปหน้า Detail
    }
    return render(request, 'movies/detail.html', context)

@login_required
def search_users(request):
    """ค้นหาบัญชีผู้ใช้คนอื่นๆ"""
    query = request.GET.get('q', '').strip()
    users = []
    
    if query:
        # ค้นหาจาก username, ชื่อ, หรือ นามสกุล (ไม่รวม Superuser และตัวเอง)
        users = User.objects.filter(
            Q(username__icontains=query) | 
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).exclude(is_superuser=True).exclude(id=request.user.id)

    return render(request, 'movies/search_users.html', {'users': users, 'query': query})

def mood_recommendation(request, mood_id):
    """แนะนำหนังตามอารมณ์ ด้วยสูตร Weighted Rating (IMDb Formula)"""
    mood = get_object_or_404(Mood, id=mood_id)
    
    # ---------------------------------------------------------
    # 1. กำหนดตัวแปรสำหรับสูตร IMDb
    # ---------------------------------------------------------
    m = 1  # (m) Minimum Votes: จำนวนรีวิวขั้นต่ำที่จะนำมาคำนวณ (ปรับเลขได้)
    
    # (C) Global Average: ค่าเฉลี่ยความเข้มข้นอารมณ์นี้ ของหนัง 'ทุกเรื่อง' ในระบบ
    # ถ้ายังไม่มีรีวิวเลย ให้ตั้งค่า default เป็น 5.0 (กลางๆ)
    global_stats = Review.objects.filter(primary_mood=mood).aggregate(avg_global=Avg('mood_intensity'))
    C = global_stats['avg_global'] if global_stats['avg_global'] is not None else 5.0

    # ---------------------------------------------------------
    # 2. Query และคำนวณ Weighted Score
    # ---------------------------------------------------------
    recommended_movies = Movie.objects.filter(
        reviews__primary_mood=mood
    ).annotate(
        # (v) Count: จำนวนรีวิวของหนังเรื่องนี้
        v=Count('reviews', filter=Q(reviews__primary_mood=mood)),
        # (R) Average: ค่าเฉลี่ยความเข้มข้นของหนังเรื่องนี้
        R=Avg('reviews__mood_intensity', filter=Q(reviews__primary_mood=mood))
    ).filter(
        # กรองเอาเฉพาะเรื่องที่มีรีวิวเกินค่า m (เช่น ต้องมี 5 คนขึ้นไปถึงจะติดอันดับ)
        v__gte=m  
    ).annotate(
        # สูตร IMDb: WR = (v / (v+m)) * R + (m / (v+m)) * C
        # แปลงเป็นคณิตศาสตร์ใน Django ORM (ExpressionWrapper เพื่อให้ผลลัพธ์เป็นทศนิยม)
        mood_score=ExpressionWrapper(
            ((F('v') * F('R')) + (m * C)) / (F('v') + m),
            output_field=FloatField()
        )
    ).order_by('-mood_score')[:20]

    return render(request, 'movies/recommendation.html', {
        'mood': mood,
        'movies': recommended_movies
    })

# ==========================================
# 2. USER ACTIONS (รีวิว, Fav, Bookmark)
# ==========================================

@login_required
def add_review(request, tmdb_id):
    """เพิ่มรีวิวใหม่"""
    movie = Movie.objects.filter(tmdb_id=tmdb_id).first()
    if not movie:
        tmdb_data = get_movie_details_tmdb(tmdb_id)
        if tmdb_data:
            movie = Movie.objects.create(
                tmdb_id=tmdb_data['tmdb_id'],
                title=tmdb_data['title'],
                poster_path=tmdb_data['poster_path'],
                overview=tmdb_data.get('overview', ''),
                release_date=tmdb_data.get('release_date'),
                vote_average=tmdb_data.get('vote_average', 0.0)
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

@login_required
def edit_review(request, review_id):
    """แก้ไขรีวิว (เฉพาะเจ้าของ)"""
    review = get_object_or_404(Review, id=review_id)
    
    if request.user != review.user:
        messages.error(request, 'คุณไม่มีสิทธิ์แก้ไขรีวิวนี้')
        return redirect('movie_detail', tmdb_id=review.movie.tmdb_id)

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, 'แก้ไขรีวิวเรียบร้อยแล้ว!')
            return redirect('movie_detail', tmdb_id=review.movie.tmdb_id)
    else:
        form = ReviewForm(instance=review)

    return render(request, 'movies/edit_review.html', {
        'form': form, 
        'movie': review.movie,
        'review': review
    })

@login_required
def delete_review(request, review_id):
    """ลบุรีวิว (เฉพาะเจ้าของ)"""
    review = get_object_or_404(Review, id=review_id)
    tmdb_id = review.movie.tmdb_id
    
    if request.user != review.user:
        messages.error(request, 'คุณไม่มีสิทธิ์ลบรีวิวนี้')
    else:
        review.delete()
        messages.success(request, 'ลบรีวิวเรียบร้อยแล้ว')
        
    return redirect('movie_detail', tmdb_id=tmdb_id)

@login_required
@require_POST
def toggle_favorite(request, tmdb_id):
    """Toggle Favorite (AJAX)"""
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
    """Toggle Bookmark (AJAX)"""
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

# ==========================================
# 3. CUSTOM ADMIN DASHBOARD (สำหรับ Superuser)
# ==========================================

@staff_member_required(login_url='login')
def admin_dashboard(request):
    """หน้า Dashboard หลัก"""
    total_movies = Movie.objects.count()
    total_reviews = Review.objects.count()
    total_users = User.objects.count()
    recent_reviews = Review.objects.select_related('user', 'movie', 'primary_mood').order_by('-created_at')[:5]
    
    return render(request, 'movies/admin/dashboard.html', {
        'total_movies': total_movies,
        'total_reviews': total_reviews,
        'total_users': total_users,
        'recent_reviews': recent_reviews
    })

@staff_member_required(login_url='login')
def admin_movies(request):
    """จัดการภาพยนตร์"""
    movies = Movie.objects.all().order_by('-id')
    query = request.GET.get('q')
    if query:
        movies = movies.filter(title__icontains=query)
        
    return render(request, 'movies/admin/movies.html', {'movies': movies, 'query': query})

@staff_member_required(login_url='login')
def admin_moods(request):
    """จัดการอารมณ์"""
    moods = Mood.objects.all()
    
    if request.method == 'POST':
        mood_name = request.POST.get('mood_name')
        mood_id = request.POST.get('mood_id')
        
        if mood_id:
            mood = get_object_or_404(Mood, id=mood_id)
            mood.name = mood_name
            mood.save()
            messages.success(request, f'อัปเดตอารมณ์ "{mood_name}" เรียบร้อย')
        else:
            Mood.objects.create(name=mood_name)
            messages.success(request, f'เพิ่มอารมณ์ "{mood_name}" เรียบร้อย')
        return redirect('admin_moods')
        
    return render(request, 'movies/admin/moods.html', {'moods': moods})

@staff_member_required(login_url='login')
def admin_reviews(request):
    """จัดการรีวิว"""
    reviews = Review.objects.select_related('user', 'movie', 'primary_mood').order_by('-created_at')
    query = request.GET.get('q')
    if query:
        reviews = reviews.filter(
            Q(movie__title__icontains=query) | 
            Q(user__username__icontains=query) |
            Q(review_text__icontains=query)
        )

    return render(request, 'movies/admin/reviews.html', {'reviews': reviews, 'query': query})

# ==========================================
# 4. CUSTOM LIST MANAGEMENT
# ==========================================

@login_required
def my_lists(request):
    """หน้าแสดงรายการ List ทั้งหมดของฉัน"""
    lists = request.user.custom_lists.all().annotate(movie_count=Count('movies')).order_by('-created_at')
    return render(request, 'movies/lists/my_lists.html', {'lists': lists})

@login_required
def create_list(request):
    """สร้าง List ใหม่"""
    if request.method == 'POST':
        form = CustomListForm(request.POST)
        if form.is_valid():
            custom_list = form.save(commit=False)
            custom_list.user = request.user
            custom_list.save()
            messages.success(request, f'สร้างรายการ "{custom_list.name}" เรียบร้อยแล้ว')
            return redirect('my_lists')
    else:
        form = CustomListForm()
    
    return render(request, 'movies/lists/create_list.html', {'form': form})

@login_required
def list_detail(request, list_id):
    """ดูรายละเอียดใน List"""
    custom_list = get_object_or_404(CustomList, id=list_id)
    
    # เช็คสิทธิ์: ต้องเป็นเจ้าของ หรือ List ต้องเป็น Public
    if not custom_list.is_public and request.user != custom_list.user:
        messages.error(request, 'คุณไม่สามารถเข้าถึงรายการส่วนตัวนี้ได้')
        return redirect('home')

    movies = custom_list.movies.all()
    return render(request, 'movies/lists/list_detail.html', {'custom_list': custom_list, 'movies': movies})

@login_required
def delete_list(request, list_id):
    """ลบ List"""
    custom_list = get_object_or_404(CustomList, id=list_id, user=request.user)
    custom_list.delete()
    messages.success(request, 'ลบรายการเรียบร้อยแล้ว')
    return redirect('my_lists')

@login_required
def remove_movie_from_list(request, list_id, movie_id):
    """ลบหนังออกจาก List"""
    custom_list = get_object_or_404(CustomList, id=list_id, user=request.user)
    movie = get_object_or_404(Movie, id=movie_id)
    
    custom_list.movies.remove(movie)
    messages.success(request, f'ลบ "{movie.title}" ออกจากรายการแล้ว')
    return redirect('list_detail', list_id=list_id)

@login_required
def edit_list(request, list_id):
    """แก้ไขรายการหนัง (เฉพาะเจ้าของ)"""
    custom_list = get_object_or_404(CustomList, id=list_id)

    # เช็คสิทธิ์ความเป็นเจ้าของ
    if request.user != custom_list.user:
        messages.error(request, 'คุณไม่มีสิทธิ์แก้ไขรายการนี้')
        return redirect('my_lists')

    if request.method == 'POST':
        form = CustomListForm(request.POST, instance=custom_list)
        if form.is_valid():
            form.save()
            messages.success(request, f'แก้ไขรายการ "{custom_list.name}" เรียบร้อยแล้ว')
            return redirect('list_detail', list_id=custom_list.id)
    else:
        form = CustomListForm(instance=custom_list) # ดึงข้อมูลเดิมมาใส่ฟอร์ม

    return render(request, 'movies/lists/edit_list.html', {'form': form, 'custom_list': custom_list})

@login_required
@require_POST
def toggle_list_movie(request, list_id, tmdb_id):
    """Toggle Add/Remove Movie from List (AJAX) - ใช้ในหน้า Detail"""
    custom_list = get_object_or_404(CustomList, id=list_id, user=request.user)
    
    # หาหรือสร้างหนัง
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

    # เช็คว่ามีหนังนี้ในลิสต์ไหม
    if custom_list.movies.filter(id=movie.id).exists():
        custom_list.movies.remove(movie)
        status = 'removed'
    else:
        custom_list.movies.add(movie)
        status = 'added'

    return JsonResponse({'status': status, 'list_name': custom_list.name})

def user_lists(request, username):
    # ดึงข้อมูล User จากชื่อ
    profile_user = get_object_or_404(User, username=username)

    # เช็คว่า: คนที่ล็อกอินอยู่ คือคนเดียวกับเจ้าของโปรไฟล์นี้ไหม?
    if request.user.is_authenticated and request.user == profile_user:
        # ถ้าใช่ "ตัวเราเอง" -> ดีดไปหน้าจัดการส่วนตัวเลย (my_lists)
        return redirect('my_lists')

    # ----------------------------------------------------
    # ถ้าไม่ใช่ (เป็นคนอื่นมาส่อง) -> ให้ทำงานตามปกติ
    # ----------------------------------------------------
    
    # ดึงเฉพาะรายการที่เป็น Public (is_public=True) ให้คนอื่นดู
    lists = CustomList.objects.filter(user=profile_user, is_public=True).order_by('-created_at')

    return render(request, 'movies/lists/user_lists.html', {
        'profile_user': profile_user,
        'lists': lists,
    })

# ==========================================
# 5. MOVIE CALENDAR
# ==========================================

def movie_calendar(request):
    """แสดงปฏิทินหนังเข้าใหม่"""
    # 1. หาปีและเดือนปัจจุบัน (หรือจาก URL)
    today = date.today()
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except ValueError:
        year = today.year
        month = today.month

    # 2. หาวันแรกและวันสุดท้ายของเดือน เพื่อส่งไปดึงข้อมูล API
    _, last_day = calendar.monthrange(year, month)
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{last_day}"

    # 3. ดึงหนังจาก TMDb
    movies = get_movies_in_date_range(start_date, end_date)

    # 4. จัดกลุ่มหนังตาม "วันที่" เพื่อให้ง่ายต่อการแสดงผลใน Template
    # ผลลัพธ์: {'2023-11-01': [movie1, movie2], '2023-11-15': [movie3]}
    movies_by_date = {}
    for movie in movies:
        r_date = movie['release_date']
        if r_date not in movies_by_date:
            movies_by_date[r_date] = []
        movies_by_date[r_date].append(movie)

    # 5. สร้าง Matrix ปฏิทิน (List of Lists ของวันที่)
    # 0 คือวันที่ไม่ใช่ของเดือนนี้ (ช่องว่าง)
    cal = calendar.monthcalendar(year, month)

    # 6. คำนวณเดือนก่อนหน้าและเดือนถัดไป (สำหรับปุ่มเปลี่ยนเดือน)
    prev_date = date(year, month, 1) - timedelta(days=1)
    next_date = date(year, month, last_day) + timedelta(days=1)

    # ชื่อเดือนภาษาไทย
    thai_months = [
        "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
    ]

    context = {
        'calendar': cal,
        'movies_by_date': movies_by_date,
        'year': year,
        'month': month,
        'month_name': thai_months[month],
        'prev_year': prev_date.year,
        'prev_month': prev_date.month,
        'next_year': next_date.year,
        'next_month': next_date.month,
    }
    return render(request, 'movies/calendar.html', context)

# ==========================================
# 6. ADMIN DELETE ACTIONS
# ==========================================

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

@staff_member_required(login_url='login')
def admin_delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.delete()
    messages.success(request, 'ลบรีวิวเรียบร้อยแล้ว')
    return redirect('admin_reviews')