# chatbot_app/views.py

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests
import os # <-- این خط برای دسترسی به os.getenv لازم است

from django.conf import settings
import google.generativeai as genai

genai.configure(api_key=settings.GEMINI_API_KEY)

# ------------------- مدیریت امن کلیدهای API -------------------
# کلیدهای API از متغیرهای محیطی که از فایل .env بارگذاری شده‌اند، خوانده می‌شوند.
# به این ترتیب، کلیدها در کد سورس قرار نمی‌گیرند و در گیت‌هاب منتشر نخواهند شد.
# ---------------------------------------------------------------
GEMINI_API_KEYS = [
    os.getenv('GEMINI_API_KEY'),
    os.getenv('GEMINI_API_KEY_1'),
    os.getenv('GEMINI_API_KEY_2'),
]

# حذف کلیدهای API خالی یا None از لیست
GEMINI_API_KEYS = [key for key in GEMINI_API_KEYS if key]

GEMINI_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent'

# View برای نمایش صفحه اصلی HTML
def index(request):
    return render(request, 'chatbot_app/index.html')

# View برای API چت بات
@csrf_exempt
def chat_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()

            if not user_message:
                return JsonResponse({'error': 'پیام خالی ارسال شده است.'}, status=400)

            # پاسخ‌های از پیش تعیین شده
            lower_case_message = user_message.lower()
            if any(phrase in lower_case_message for phrase in ['چه کسی تو را ساخته', 'چه کسی ساخته شدی', 'سازنده تو کیست', 'توسط چه کسی آموزش دیده ای', 'تو کی هستی']):
                return JsonResponse({'reply': 'من یک هوش مصنوعی هستم که توسط تیم AysChat توسعه و آموزش داده شده‌ام.'})

            if not GEMINI_API_KEYS:
                return JsonResponse({'error': 'کلیدهای API Gemini تنظیم نشده‌اند. لطفاً با مدیر سایت تماس بگیرید.'}, status=500)

            # ارسال پیام به Gemini API با امتحان کردن کلیدها
            for api_key in GEMINI_API_KEYS:
                url = f"{GEMINI_BASE_URL}?key={api_key}"
                request_body = {
                    "contents": [{
                        "role": "user",
                        "parts": [{"text": user_message}]
                    }],
                    "generationConfig": {
                        "temperature": 0.7,
                        "topP": 0.9,
                        "topK": 40
                    }
                }
                headers = {'Content-Type': 'application/json'}

                try:
                    response = requests.post(url, headers=headers, json=request_body)
                    response.raise_for_status() # اگر وضعیت پاسخ >= 400 بود، خطا ایجاد کن

                    gemini_data = response.json()
                    reply_text = gemini_data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'خطا در پردازش پاسخ. لطفاً دوباره تلاش کنید.')

                    return JsonResponse({'reply': reply_text})

                except requests.exceptions.RequestException as e:
                    print(f"Error calling Gemini API with key {api_key}: {e}")
                    # اگر خطایی رخ داد، کلید بعدی را امتحان کن
                    continue
                except Exception as e:
                    print(f"Error parsing Gemini response with key {api_key}: {e}")
                    continue

            # اگر همه کلیدها با شکست مواجه شدند
            return JsonResponse({'error': 'خطا در برقراری ارتباط با AysChat. تمام کلیدهای API نامعتبر بودند یا به محدودیت رسیده‌اند. لطفاً بعداً تلاش کنید.'}, status=500)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'فرمت JSON نامعتبر.'}, status=400)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return JsonResponse({'error': f'خطای داخلی سرور: {e}'}, status=500)
    else:
        return JsonResponse({'error': 'فقط درخواست‌های POST پشتیبانی می‌شوند.'}, status=405)
