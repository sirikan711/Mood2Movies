from django.contrib import admin
from django.utils.html import format_html
from .models import Movie, Mood, Review, Favorite, Bookmark, CustomList, Profile

# Config Header
admin.site.site_header = "Mood2Movie Administration"
admin.site.site_title = "Mood2Movie Admin Portal"
admin.site.index_title = "ยินดีต้อนรับสู่ระบบจัดการหลังบ้าน"

@admin.register(Mood)
class MoodAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_emoji_display')
    search_fields = ('name',)
    
    def get_emoji_display(self, obj):
        return str(obj).split(' ')[0]
    get_emoji_display.short_description = 'Emoji'

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('id', 'poster_thumbnail', 'title', 'release_date', 'tmdb_id')
    list_display_links = ('id', 'title')
    search_fields = ('title', 'tmdb_id')
    list_filter = ('release_date',)

    def poster_thumbnail(self, obj):
        if obj.poster_path:
            full_url = f"https://image.tmdb.org/t/p/w200{obj.poster_path}"
            return format_html('<img src="{}" style="width: 40px; height: auto; border-radius: 4px;" />', full_url)
        return "-"
    poster_thumbnail.short_description = 'Poster'

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'primary_mood', 'mood_intensity', 'rating', 'created_at')
    list_filter = ('primary_mood', 'mood_intensity', 'rating', 'created_at') 
    search_fields = ('user__username', 'movie__title', 'review_text')
    date_hierarchy = 'created_at'

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'avatar_thumbnail')
    search_fields = ('user__username', 'user__email')

    def avatar_thumbnail(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover;" />', obj.avatar.url)
        return "-"
    avatar_thumbnail.short_description = 'Avatar'

# Register Simple Models
admin.site.register(Favorite)
admin.site.register(Bookmark)
admin.site.register(CustomList)