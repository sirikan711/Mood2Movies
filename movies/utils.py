# movies/utils.py
import requests
from django.conf import settings

TMDB_API_KEY = getattr(settings, 'TMDB_API_KEY', '8f3fabb4ea55b62b7d611bc956f12b8b') 
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/w500' # ขนาดรูปภาพมาตรฐาน

def get_tmdb_genres():
    # ดึงรายชื่อประเภทหนังทั้งหมดจาก TMDb
    url = f"{TMDB_BASE_URL}/genre/movie/list"
    params = {'api_key': TMDB_API_KEY, 'language': 'th-TH'}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get('genres', [])
    except Exception as e:
        print(f"Error fetching genres: {e}")
        return []

def search_movies_tmdb(query, year=None, genre_id=None):
    # ค้นหาหนังจาก TMDb (รองรับ ชื่อ, ปี, และประเภท)
    results = []
    
    # กรณี 1: ค้นหาด้วยชื่อ (Search API) -> กรอง Genre ทีหลัง
    if query:
        url = f"{TMDB_BASE_URL}/search/movie"
        params = {
            'api_key': TMDB_API_KEY,
            'query': query,
            'language': 'th-TH',
            'include_adult': 'false'
        }
        if year:
            params['primary_release_year'] = year
            
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            for item in data.get('results', []):
                # ถ้ามีการระบุ genre_id ต้องเช็คว่าหนังเรื่องนี้มี genre นั้นไหม
                if genre_id and int(genre_id) not in item.get('genre_ids', []):
                    continue # ข้ามไปถ้าไม่ตรงประเภท
                
                if item.get('poster_path'):
                    results.append({
                        'tmdb_id': item['id'],
                        'title': item['title'],
                        'release_date': item.get('release_date', 'N/A'),
                        'poster_url': f"{TMDB_IMAGE_BASE_URL}{item['poster_path']}",
                        'vote_average': item.get('vote_average', 0.0) 
                    })
        except Exception as e:
            print(f"Error searching: {e}")

    # กรณี 2: ไม่ได้พิมพ์ชื่อ แต่เลือกประเภทหรือปี (Discover API)
    elif genre_id or year:
        url = f"{TMDB_BASE_URL}/discover/movie"
        params = {
            'api_key': TMDB_API_KEY,
            'language': 'th-TH',
            'sort_by': 'popularity.desc', # เอาหนังดังขึ้นก่อน
            'include_adult': 'false',
            'page': 1
        }
        if genre_id:
            params['with_genres'] = genre_id
        if year:
            params['primary_release_year'] = year
            
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            for item in data.get('results', []):
                if item.get('poster_path'):
                    results.append({
                        'tmdb_id': item['id'],
                        'title': item['title'],
                        'release_date': item.get('release_date', 'N/A'),
                        'poster_url': f"{TMDB_IMAGE_BASE_URL}{item['poster_path']}",
                        'vote_average': item.get('vote_average', 0.0)
                    })
        except Exception as e:
            print(f"Error discovering: {e}")

    return results

def get_movie_details_tmdb(tmdb_id):
    # ดึงรายละเอียดหนังจาก TMDb
    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"
    params = {'api_key': TMDB_API_KEY, 'language': 'th-TH'}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return {
            'tmdb_id': data['id'],
            'title': data['title'],
            'poster_path': data.get('poster_path'),
            'poster_url': f"{TMDB_IMAGE_BASE_URL}{data.get('poster_path')}" if data.get('poster_path') else None,
            'overview': data.get('overview', ''),
            'release_date': data.get('release_date'),
            'genres': [g['name'] for g in data.get('genres', [])],
            'runtime': data.get('runtime'),
            'vote_average': data.get('vote_average', 0.0)
        }
    except Exception as e:
        return None

def get_popular_movies_tmdb():
    # ดึงหนังยอดนิยม (เหมือนเดิม)
    url = f"{TMDB_BASE_URL}/movie/popular"
    params = {'api_key': TMDB_API_KEY, 'language': 'th-TH', 'page': 1}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        results = []
        for item in data.get('results', [])[:10]:
            if item.get('poster_path'):
                results.append({
                    'tmdb_id': item['id'],
                    'title': item['title'],
                    'release_date': item.get('release_date', 'N/A'),
                    'poster_url': f"{TMDB_IMAGE_BASE_URL}{item['poster_path']}",
                    'vote_average': item.get('vote_average', 0.0)
                })
        return results
    except Exception as e:
        print(f"Error fetching popular movies from TMDb: {e}")
        return []
    
def get_movies_in_date_range(start_date, end_date):
    """ดึงหนังที่ฉายในไทย ช่วงวันที่กำหนด"""
    url = f"{TMDB_BASE_URL}/discover/movie"
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'th-TH',
        'region': 'TH', # 1. ระบุประเทศ
        'sort_by': 'release_date.asc', # 2. เรียงตามวันฉายในประเทศนั้น
        'release_date.gte': start_date, # 3. ใช้วันฉาย (ไม่ใช่ primary_release_date)
        'release_date.lte': end_date,
        'with_release_type': '2|3', # 2=Limited, 3=Theatrical
        'include_adult': 'false'
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get('results', []):
            if item.get('release_date'):
                results.append({
                    'tmdb_id': item['id'],
                    'title': item['title'],
                    'release_date': item['release_date'],
                    'poster_url': f"{TMDB_IMAGE_BASE_URL}{item['poster_path']}" if item.get('poster_path') else None,
                    'overview': item.get('overview', '')
                })
        return results
    except Exception as e:
        print(f"Error fetching calendar movies: {e}")
        return []