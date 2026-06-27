import re

# ---- الكلمات المشبوهة للفلترة المحلية ----
# أرقام الهواتف والتواصل بصيغ مختلفة
QUICK_SPAM_TRIGGERS = [
    r"\b05\d{8}\b", 
    r"\b9665\d{8}\b", 
    r"\b\+9665\d{8}\b", 
    r"\b009665\d{8}\b",
    r"\b05\d{1}\s?\d{3}\s?\d{4}\b", # مثل 055 123 4567
    r"\b\+?966\s?5\d{8}\b",
    r"\b\+?\d{3}[-\s]?\d{3}[-\s]?\d{4}\b" # أرقام جوال عامة
]

QUICK_SPAM_WORDS = [
    # كلمات ترويجية للمعلنين والاعلانات
    "تواصل", "راسلني", "تواصل معي", "واتساب", "سناب", "سناب شات", "انستقرام", "تيك توك",
    "حل واجب", "حل كويز", "تسليم", "مشروع", "تقرير", "بحوث", "واجبات", "مشاريع", "كويزات",
    "اشتراك", "قناة", "قروب", "خدمة", "سعر", "تكليف", "تمويل", "قرض", "تسويق", "ارقام", "أرقام",
    "اتصال", "تليجرام", "تيليجرام", "رابط المجموعه", "كود خصم", "خصم", "متوفر الان", "يوجد لدينا",
    "تصميم", "اعلانات", "اعلان", "أرخص", "ضمان", "مضمون", "شحن", "بيع", "شراء", "حسابات", "ربح",
    "وظيفة", "وظائف", "توظيف", "فرصة", "فرص", "راتب"
]

# تعبير نمطي قوي لكشف الروابط
LINK_REGEX = re.compile(
    r'(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.(com|net|org|info|xyz|me|edu|co|sa|ly|app|link|club|site|online|tech|vip|top|gov)\b([/?#][^\s]*)?|t\.me/[^\s]+|wa\.me/[^\s]+)',
    re.IGNORECASE
)

def is_suspicious(text: str, custom_words: list = None) -> bool:
    """فحص سريع محلي: هل الرسالة مشبوهة لإرسالها إلى Gemini؟"""
    if not text:
        return False
    text_lower = text.lower()
    
    words_to_use = custom_words if custom_words is not None else QUICK_SPAM_WORDS
    keyword_matches = sum(1 for word in words_to_use if word in text_lower)
    has_phone = any(re.search(p, text_lower) for p in QUICK_SPAM_TRIGGERS)
    
    if (has_phone and keyword_matches >= 1) or keyword_matches >= 2:
        return True
    
    return False
