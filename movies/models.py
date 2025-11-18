# movies/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Movie(models.Model):
    tmdb_id = models.IntegerField(unique=True)
    title = models.CharField(max_length=255)
    poster_path = models.CharField(max_length=255, null=True, blank=True)
    overview = models.TextField(null=True, blank=True)
    release_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.title

class Mood(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        # กำหนด Emoji ตามชื่อ Mood
        emoji = ''
        if 'Happy' in self.name: emoji = '😊'
        elif 'Sad' in self.name: emoji = '😭'
        elif 'Scary' in self.name: emoji = '😨'
        elif 'Surprised' in self.name: emoji = '😲'
        elif 'Heartwarming' in self.name: emoji = '🥰'
        elif 'Tense' in self.name: emoji = '😬'
        elif 'Funny' in self.name: emoji = '🤣'
        elif 'Relaxing' in self.name: emoji = '😌'
        else: emoji = '🎬'
        
        return f"{emoji} {self.name}" # คืนค่าเป็น "😊 มีความสุข (Happy)"

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='reviews')
    primary_mood = models.ForeignKey(Mood, on_delete=models.SET_NULL, null=True, related_name='primary_reviews')
    mood_intensity = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    rating = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    review_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie') # 1 คนรีวิวหนังเรื่องเดิมได้แค่ครั้งเดียว

    def __str__(self):
        return f"{self.user.username} reviewed {self.movie.title}"
    
# 1. รายการหนังโปรด (Favorite)
class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie') # 1 คน fav หนังเรื่องเดิมได้ครั้งเดียว

    def __str__(self):
        return f"{self.user.username} favs {self.movie.title}"

# 2. บุ๊กมาร์ก/ดูภายหลัง (Bookmark/Watchlist)
class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='bookmarked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie')

    def __str__(self):
        return f"{self.user.username} bookmarked {self.movie.title}"

# 3. รายการส่วนตัว (Custom List) - แบบง่าย
class CustomList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_lists')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    movies = models.ManyToManyField(Movie, related_name='contained_in_lists', blank=True)
    is_public = models.BooleanField(default=True) # เผื่ออนาคตอยากให้แชร์ได้
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} by {self.user.username}"