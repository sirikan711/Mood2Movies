# core/views.py
from django.shortcuts import render
from movies.models import Mood
from movies.utils import get_popular_movies_tmdb

def home(request):
    moods = Mood.objects.all() # ดึง Mood ทั้งหมดจาก DB
        # ดึงหนังยอดนิยมมาด้วย
    popular_movies = get_popular_movies_tmdb()

    return render(request, 'core/home.html', {
        'moods': moods,
        'popular_movies': popular_movies # ส่งไปที่ Template
    })