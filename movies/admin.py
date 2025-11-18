# movies/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Movie, Mood, Review, Favorite, Bookmark, CustomList

# 1. จัดการหมวดหมู่อารมณ์ (Moods)
@admin.register(Mood)
class MoodAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_emoji_display')
    search_fields = ('name',)
    
    def get_emoji_display(self, obj):
        # ดึง Logic การแสดง Emoji จาก __str__ หรือเขียนใหม่
        return str(obj).split(' ')[0] # เอาตัวอักษรตัวแรก (Emoji) มาโชว์
    get_emoji_display.short_description = 'Emoji'

# 2. จัดการข้อมูลหนัง (Movies)
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('id', 'poster_thumbnail', 'title', 'release_date', 'tmdb_id')
    list_display_links = ('id', 'title') # คลิกที่ ID หรือชื่อเพื่อแก้ไข
    search_fields = ('title', 'tmdb_id') # ค้นหาจากชื่อหรือ ID
    list_filter = ('release_date',) # กรองตามปีที่ฉาย

    # ฟังก์ชันสร้างรูปย่อ (Thumbnail)
    def poster_thumbnail(self, obj):
        if obj.poster_path:
            full_url = f"https://image.tmdb.org/t/p/w200{obj.poster_path}"
            return format_html('<img src="{}" style="width: 50px; height: auto; border-radius: 4px;" />', full_url)
        return "-"
    poster_thumbnail.short_description = 'Poster'

# 3. จัดการรีวิว (Reviews) - เอาไว้ดูหรือลบรีวิวที่ไม่เหมาะสม
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'primary_mood', 'mood_intensity', 'rating', 'created_at')
    list_filter = ('primary_mood', 'rating', 'created_at')
    search_fields = ('user__username', 'movie__title', 'review_text')
    date_hierarchy = 'created_at' # เพิ่มแถบนำทางตามวันเวลาด้านบน

# 4. จัดการรายการอื่นๆ (Optional)
admin.site.register(Favorite)
admin.site.register(Bookmark)
admin.site.register(CustomList)

# ปรับแต่งหัวข้อหน้า Admin
admin.site.site_header = "Mood2Movie Administration"
admin.site.site_title = "Mood2Movie Admin Portal"
admin.site.index_title = "ยินดีต้อนรับสู่ระบบจัดการหลังบ้าน"