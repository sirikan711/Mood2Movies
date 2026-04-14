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

from .models import Movie, Review, Mood, Favorite, Bookmark, CustomList, ReviewMoodScore
from .forms import ReviewForm, CustomListForm
from .utils import search_movies_tmdb, get_movie_details_tmdb, get_tmdb_genres, get_movies_in_date_range

# ==========================================
# 1. PUBLIC VIEWS (ค้นหา, รายละเอียด, แนะนำ)
# ==========================================

def search_movies(request):
    """ค้นหาภาพยนตร์ (รองรับชื่อ, อารมณ์แบบใหม่ Multi-Mood, ปี, ประเภท)"""
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
        
        # กรองจากตารางลูก ReviewMoodScore ที่คะแนน > 0 เท่านั้น
        movies_qs = Movie.objects.filter(
            reviews__mood_scores__mood=mood,
            reviews__mood_scores__intensity__gt=0 
        ).distinct()
        
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
    """แสดงรายละเอียดภาพยนตร์และรีวิว (อัปเดตใหม่ รองรับ Multi-Mood & Radar Chart)"""
    
    # 1. จัดการข้อมูลหนัง (หาใน DB หรือดึงจาก TMDB)
    movie = Movie.objects.filter(tmdb_id=tmdb_id).first()
    tmdb_data = get_movie_details_tmdb(tmdb_id)
    
    if not tmdb_data:
        return render(request, '404.html', status=404)

    # ถ้ายังไม่มีหนังใน DB ให้สร้างใหม่
    if not movie and tmdb_data:
        movie = Movie.objects.create(
            tmdb_id=tmdb_data['tmdb_id'], 
            title=tmdb_data['title'],
            poster_path=tmdb_data.get('poster_path'),
            overview=tmdb_data.get('overview', ''),
            release_date=tmdb_data.get('release_date') or None,
            vote_average=tmdb_data.get('vote_average', 0)
        )

    # 2. Handle Review Submission (POST)
    if request.method == 'POST' and request.user.is_authenticated:
        
        # Check Duplicate Review
        if Review.objects.filter(user=request.user, movie=movie).exists():
            messages.warning(request, 'คุณได้รีวิวหนังเรื่องนี้ไปแล้ว หากต้องการเปลี่ยนคะแนน กรุณาแก้ไขรีวิวเดิม')
            return redirect('movie_detail', tmdb_id=tmdb_id)

        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.movie = movie
            review.user = request.user
            review.save()

            # วนลูปเก็บคะแนน Mood Score
            all_moods = Mood.objects.all()
            for mood in all_moods:
                score_key = f'mood_score_{mood.id}'
                score_val = request.POST.get(score_key)
                if score_val and score_val.isdigit():
                    intensity = int(score_val)
                    if intensity > 0:
                        ReviewMoodScore.objects.create(
                            review=review,
                            mood=mood,
                            intensity=intensity
                        )
            messages.success(request, 'บันทึกรีวิวเรียบร้อยแล้ว!')
            return redirect('movie_detail', tmdb_id=movie.tmdb_id)
    else:
        form = ReviewForm()
    
    # 3. เตรียมข้อมูลแสดงผล
    reviews = []
    is_favorited = False
    is_bookmarked = False
    user_lists = []
    mood_stats = []
    all_moods = Mood.objects.all()
    user_review = None

    if movie:
        reviews = movie.reviews.select_related('user', 'user__profile') \
                               .prefetch_related('mood_scores__mood') \
                               .order_by('-created_at')
        
        # คำนวณ Mood Stats สำหรับ Radar Chart
        for mood in all_moods:
            avg_intensity = ReviewMoodScore.objects.filter(
                review__movie=movie, 
                mood=mood
            ).aggregate(avg=Avg('intensity'))['avg'] or 0
            
            mood_stats.append({
                'name': mood.name,
                'score': round(avg_intensity, 1)
            })

        if request.user.is_authenticated:
            is_favorited = Favorite.objects.filter(user=request.user, movie=movie).exists()
            is_bookmarked = Bookmark.objects.filter(user=request.user, movie=movie).exists()
            user_lists = request.user.custom_lists.all().annotate(
                has_movie=Count('movies', filter=Q(movies__id=movie.id))
            )
            # หา User Review
            user_review = reviews.filter(user=request.user).first()
            
    elif request.user.is_authenticated:
        user_lists = request.user.custom_lists.all()

    context = {
        'movie': movie,
        'movie_db': movie,      
        'movie_tmdb': tmdb_data,
        'reviews': reviews,
        'is_favorited': is_favorited,
        'is_bookmarked': is_bookmarked,
        'user_lists': user_lists,
        'form': form,
        'mood_stats': mood_stats,
        'all_moods': all_moods,
        'user_review': user_review,
    }
    return render(request, 'movies/detail.html', context)

@login_required
def search_users(request):
    """ค้นหาบัญชีผู้ใช้คนอื่นๆ"""
    query = request.GET.get('q', '').strip()
    users = []
    
    if query:
        users = User.objects.filter(
            Q(username__icontains=query) | 
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).exclude(is_superuser=True).exclude(id=request.user.id)

    return render(request, 'movies/search_users.html', {'users': users, 'query': query})

def mood_recommendation(request, mood_id):
    """แนะนำหนังตามอารมณ์ ด้วยสูตร Weighted Rating (IMDb Formula) [FIXED: กรองคะแนน 0 ออก]"""
    mood = get_object_or_404(Mood, id=mood_id)
    
    m = 1  # Minimum Votes
    
    # (C) Global Average: คิดเฉพาะที่มีคะแนน (>0) ไม่งั้นค่าเฉลี่ยจะต่ำเกินจริง
    global_stats = ReviewMoodScore.objects.filter(mood=mood, intensity__gt=0).aggregate(avg_global=Avg('intensity'))
    C = global_stats['avg_global'] if global_stats['avg_global'] is not None else 5.0

    # Query และคำนวณ Weighted Score
    recommended_movies = Movie.objects.filter(
        reviews__mood_scores__mood=mood,
        reviews__mood_scores__intensity__gt=0 # [FIX] กรองหนังที่มีคะแนนอารมณ์นี้ > 0 เท่านั้น
    ).distinct().annotate(
        # (v) Count: นับเฉพาะคะแนน > 0
        v=Count('reviews__mood_scores', filter=Q(reviews__mood_scores__mood=mood, reviews__mood_scores__intensity__gt=0)),
        # (R) Average: เฉลี่ยเฉพาะคะแนน > 0
        R=Avg('reviews__mood_scores__intensity', filter=Q(reviews__mood_scores__mood=mood, reviews__mood_scores__intensity__gt=0))
    ).filter(
        v__gte=m  
    ).annotate(
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
def edit_review(request, review_id):
    """แก้ไขรีวิว (อัปเดตใหม่ รับค่า Slider ได้แล้ว)"""
    review = get_object_or_404(Review, id=review_id)
    
    # ป้องกันคนอื่นมาเนียนแก้รีวิวเรา
    if request.user != review.user:
        messages.error(request, 'คุณไม่มีสิทธิ์แก้ไขรีวิวนี้')
        return redirect('movie_detail', tmdb_id=review.movie.tmdb_id)

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save() # 1. บันทึกข้อความ Comment ก่อน

            # 2. บันทึกคะแนน Mood Score (ส่วนที่ขาดหายไป)
            all_moods = Mood.objects.all()
            
            # [Debug] ปริ้นท์เช็กหน่อยว่าส่งอะไรมาบ้าง
            print(f"--- Editing Review ID: {review_id} ---")
            
            for mood in all_moods:
                score_key = f'mood_score_{mood.id}'
                score_val = request.POST.get(score_key)
                
                if score_val and score_val.isdigit():
                    intensity = int(score_val)
                    
                    # ถ้าคะแนนมากกว่า 0 ให้บันทึก/อัปเดต
                    if intensity > 0:
                        ReviewMoodScore.objects.update_or_create(
                            review=review,
                            mood=mood,
                            defaults={'intensity': intensity}
                        )
                        print(f"Saved: {mood.name} = {intensity}")
                    else:
                        # (Option) ถ้าเลื่อนเหลือ 0 ให้ลบคะแนนอารมณ์นั้นทิ้ง
                        ReviewMoodScore.objects.filter(review=review, mood=mood).delete()
                        print(f"Removed: {mood.name}")

            messages.success(request, 'แก้ไขรีวิวเรียบร้อยแล้ว!')
            return redirect('movie_detail', tmdb_id=review.movie.tmdb_id)
            
    else:
        form = ReviewForm(instance=review)

    # ส่งคะแนนเดิมไปโชว์ที่หน้าเว็บด้วย (เผื่อ JS ดึงไปใช้)
    existing_scores = {score.mood.id: score.intensity for score in review.mood_scores.all()}

    return render(request, 'movies/edit_review.html', {
        'form': form, 
        'movie': review.movie,
        'review': review,
        'all_moods': Mood.objects.all(),
        'existing_scores': existing_scores
    })

@login_required
def delete_review(request, review_id):
    """ลบุรีวิว"""
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
    recent_reviews = Review.objects.select_related('user', 'movie').order_by('-created_at')[:5]
    
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
    reviews = Review.objects.select_related('user', 'movie').order_by('-created_at')
    query = request.GET.get('q')
    if query:
        reviews = reviews.filter(
            Q(movie__title__icontains=query) | 
            Q(user__username__icontains=query) |
            Q(comment__icontains=query)
        )

    return render(request, 'movies/admin/reviews.html', {'reviews': reviews, 'query': query})

@staff_member_required(login_url='login')
def admin_users(request):
    """จัดการผู้ใช้งาน (แสดงรายชื่อ + ค้นหา)"""
    # เรียงลำดับจากคนสมัครล่าสุดก่อน
    users = User.objects.all().order_by('-date_joined')
    
    # ระบบค้นหา (ค้นจาก Username หรือ Email)
    query = request.GET.get('q')
    if query:
        users = users.filter(
            Q(username__icontains=query) | 
            Q(email__icontains=query)
        )
        
    return render(request, 'movies/admin/users.html', {'users': users, 'query': query})

@staff_member_required(login_url='login')
def admin_delete_user(request, user_id):
    """ฟังก์ชันลบผู้ใช้งาน"""
    user_to_delete = get_object_or_404(User, id=user_id)
    
    # 🛑 ระบบป้องกัน: ห้ามแอดมินลบตัวเอง!
    if user_to_delete == request.user:
        messages.error(request, 'คุณไม่สามารถลบบัญชีของตัวเองขณะล็อกอินได้')
        return redirect('admin_users')
    
    # ถ้าไม่ใช่ตัวเอง ก็ลบได้เลย
    username = user_to_delete.username
    user_to_delete.delete()
    
    messages.success(request, f'ลบผู้ใช้ "{username}" ออกจากระบบเรียบร้อยแล้ว')
    return redirect('admin_users')

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

from datetime import date, timedelta
import calendar

def movie_calendar(request):
    """แสดงปฏิทินหนังเข้าใหม่"""
    # 1. หาปีและเดือนปัจจุบัน (วันนี้จริงๆ)
    today = date.today() 
    
    try:
        # อันนี้คือ ปี/เดือน ที่ user เลือกดู (อาจจะไม่ใช่เดือนปัจจุบัน)
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except ValueError:
        year = today.year
        month = today.month

    # 2. หาวันแรกและวันสุดท้ายของเดือน
    _, last_day = calendar.monthrange(year, month)
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{last_day}"

    # 3. ดึงหนัง (สมมติว่าฟังก์ชันนี้มีอยู่แล้ว)
    movies = get_movies_in_date_range(start_date, end_date) 

    # 4. จัดกลุ่มหนังตามวันที่
    movies_by_date = {}
    # (เช็กนิดนึงว่า movies ไม่ใช่ None ก่อนวนลูป)
    if movies:
        for movie in movies:
            r_date = movie.get('release_date') # ใช้ .get ป้องกัน error
            if r_date:
                if r_date not in movies_by_date:
                    movies_by_date[r_date] = []
                movies_by_date[r_date].append(movie)

    # 5. สร้าง Matrix ปฏิทิน
    cal = calendar.monthcalendar(year, month)

    # 6. คำนวณเดือนก่อนหน้า/ถัดไป
    prev_date = date(year, month, 1) - timedelta(days=1)
    # trick: หาวันที่ 1 ของเดือนถัดไป แล้วลบ 1 วันจะได้สิ้นเดือนนี้ -> บวกอีกทีจะได้เดือนหน้า
    # หรือใช้วิธีคำนวณง่ายๆ:
    if month == 12:
        next_year = year + 1
        next_month = 1
    else:
        next_year = year
        next_month = month + 1

    thai_months = [
        "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
    ]

    context = {
        'calendar': cal,
        'movies_by_date': movies_by_date,
        'year': year,   # ปีที่กำลังดู
        'month': month, # เดือนที่กำลังดู
        'month_name': thai_months[month],
        'prev_year': prev_date.year,
        'prev_month': prev_date.month,
        'next_year': next_year,
        'next_month': next_month,
        
        # --- ส่งวันปัจจุบันไปให้ HTML ---
        'current_day': today.day,     # วันที่วันนี้ (เช่น 20)
        'current_month': today.month, # เดือนนี้ (เช่น 2)
        'current_year': today.year,   # ปีนี้ (เช่น 2026)
        # -----------------------------------------------
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