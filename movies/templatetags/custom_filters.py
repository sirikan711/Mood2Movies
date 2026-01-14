# movies/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """ดึงค่าจาก Dictionary โดยใช้ Key ใน Template"""
    return dictionary.get(key)

@register.filter
def pad_zero(value):
    """เติมเลข 0 ข้างหน้าถ้าเป็นเลขหลักเดียว (เช่น 5 -> 05)"""
    return str(value).zfill(2)