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

    @property
    def emoji(self):
        if 'Happy' in self.name: return '😊'
        elif 'Sad' in self.name: return '😭'
        elif 'Scary' in self.name: return '😨'
        elif 'Surprised' in self.name: return '😲'
        elif 'Heartwarming' in self.name: return '🥰'
        elif 'Tense' in self.name: return '😬'
        elif 'Funny' in self.name: return '🤣'
        return '😐'

    def __str__(self):
        return self.name

class Review(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='reviews')
    # [FIXED] เติม related_name='reviews' เพื่อให้ User เรียก user.reviews.all() ได้
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Review by {self.user.username} on {self.movie.title}"

class ReviewMoodScore(models.Model):
    """
    ตารางนี้เก็บคะแนนความเข้มข้นของแต่ละอารมณ์ ใน 1 รีวิว
    เช่น รีวิวนี้มี Joy=5, Sad=2, Fear=0
    """
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='mood_scores')
    mood = models.ForeignKey(Mood, on_delete=models.CASCADE)
    intensity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )

    class Meta:
        unique_together = ('review', 'mood')

# --- 2. User Interactions ---

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie')

    def __str__(self):
        return f"{self.user.username} likes {self.movie.title}"

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
    instance.profile.save()