from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver

# --- 1. Core Models ---

class Movie(models.Model):
    tmdb_id = models.IntegerField(unique=True)
    title = models.CharField(max_length=255)
    poster_path = models.CharField(max_length=255, null=True, blank=True)
    overview = models.TextField(null=True, blank=True)
    release_date = models.DateField(null=True, blank=True)
    vote_average = models.FloatField(default=0.0)

    def __str__(self):
        return self.title

class Mood(models.Model):
    name = models.CharField(max_length=50, unique=True)

    # เพิ่ม Property นี้เพื่อให้ Template เรียกใช้ {{ mood.emoji }} ได้โดยตรง
    @property
    def emoji(self):
        if 'Happy' in self.name: return '😊'
        elif 'Sad' in self.name: return '😭'
        elif 'Scary' in self.name: return '😨'
        elif 'Surprised' in self.name: return '😲'
        elif 'Heartwarming' in self.name: return '🥰'
        elif 'Tense' in self.name: return '😬'
        elif 'Funny' in self.name: return '🤣'
        elif 'Relaxing' in self.name: return '😌'
        return '🎬'

    def __str__(self):
        # เรียกใช้ Property ด้านบน
        return f"{self.emoji} {self.name}"

# --- 2. User Interaction Models ---

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='reviews')
    primary_mood = models.ForeignKey(Mood, on_delete=models.SET_NULL, null=True, related_name='primary_reviews')
    mood_intensity = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    # rating = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    review_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie')

    def __str__(self):
        return f"{self.user.username} reviewed {self.movie.title}"

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie')

    def __str__(self):
        return f"{self.user.username} favs {self.movie.title}"

class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='bookmarked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie')

    def __str__(self):
        return f"{self.user.username} bookmarked {self.movie.title}"

class CustomList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_lists')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    movies = models.ManyToManyField(Movie, related_name='contained_in_lists', blank=True)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} by {self.user.username}"

# --- 3. User Profile & Signals ---

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    
    def __str__(self):
        return f'{self.user.username} Profile'

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except Profile.DoesNotExist:
        Profile.objects.create(user=instance)