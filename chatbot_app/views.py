# AysChat_Django/chat_app/views.py

import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
# دیگر نیازی به rest_framework نیست اگر از JsonResponse استفاده می‌کنید:
# from rest_framework.decorators import api_view
# from rest_framework.response import Response

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import requests # برای استفاده از requests.post اگر خواستید
from django.conf import settings # برای دسترسی به متغیرهای settings

# ------------------- مدیریت امن کلیدهای API -------------------
# از os.environ.get استفاده کنید که در Render به درستی کار می‌کند.
# نیازی به GEMINI_API_KEYS لیست نیست، مگر اینکه واقعاً بخواهید چندین کلید را امتحان کنید.
# اگر فقط یک کلید اصلی دارید، همین کافیست.
# اگر چندین کلید دارید، منطق زیر آن را هندل می‌کند.

# این خطوط را برای تنظیم اولیه API key برای کتابخانه genai.
# این کلید اصلی است که در settings.py یا Environment Variables رندر تنظیم شده است.
try:
    GENAI_MAIN_API_KEY = os.environ.get('GEMINI_API_KEY')
    if GENAI_MAIN_API_KEY:
        genai.configure(api_key=GENAI_MAIN_API_KEY)
    else:
        print("WARNING: GEMINI_API_KEY not set in environment variables for genai.configure.")
except Exception as e:
    print(f"Error configuring genai with main API key: {e}")

# اگر چندین کلید API دارید که می‌خواهید امتحان کنید:
# این لیست را با نام متغیرهای محیطی که در Render تنظیم کرده‌اید، به روز کنید.
# مثلا اگر در رندر GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3 دارید:
FALLBACK_GEMINI_API_KEYS = [
    os.getenv('GEMINI_API_KEY'),
    os.getenv('GEMINI_API_KEY_2'), # مثال: اگر کلید دوم دارید
    os.getenv('GEMINI_API_KEY_3'), # مثال: اگر کلید سوم دارید
]
# حذف کلیدهای API خالی یا None از لیست
FALLBACK_GEMINI_API_KEYS = [key for key in FALLBACK_GEMINI_API_KEYS if key]
print(f"Loaded {len(FALLBACK_GEMINI_API_KEYS)} fallback Gemini API keys.")

# ---------------------------------------------------------------

# View برای API چت بات
@csrf_exempt
# @api_view(['POST']) # دیگر نیازی به این دکوراتور نیست
def chat_api(request):
    print("-------------------- Incoming chat_api request --------------------")
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # نام فیلد ورودی را از 'message' به 'prompt' تغییر دادم تا با فرانت‌اند قبلی سازگار باشد
            user_message = data.get('prompt', '').strip()
            print(f"Received raw prompt: '{user_message}'")

            if not user_message:
                print("Error: Empty prompt received.")
                return JsonResponse({'error': 'پیام خالی ارسال شده است.'}, status=400)

            # پاسخ‌های از پیش تعیین شده
            lower_case_message = user_message.lower()
            if any(phrase in lower_case_message for phrase in ['چه کسی تو را ساخته', 'چه کسی ساخته شدی', 'سازنده تو کیست', 'توسط چه کسی آموزش دیده ای', 'تو کی هستی']):
                print("Responding with predefined answer for 'who made you'.")
                return JsonResponse({'response': 'من یک هوش مصنوعی هستم که توسط تیم AysChat توسعه و آموزش داده شده‌ام.'}) # 'reply' به 'response' تغییر داده شد تا یکسان باشد

            if not FALLBACK_GEMINI_API_KEYS:
                print("Error: No Gemini API keys available for fallback.")
                return JsonResponse({'error': 'کلیدهای API Gemini تنظیم نشده‌اند. لطفاً با مدیر سایت تماس بگیرید.'}, status=500)

            # امتحان کردن کلیدهای API
            model_name = 'gemini-pro' # یا 'gemini-1.5-flash' یا 'gemini-1.0-pro'
            gemini_response_text = "خطا در پردازش پاسخ. لطفاً دوباره تلاش کنید."
            api_call_successful = False

            for i, api_key_to_use in enumerate(FALLBACK_GEMINI_API_KEYS):
                print(f"Attempting API call with key index {i+1}...")
                if not api_key_to_use:
                    print(f"Skipping key index {i+1} as it's empty.")
                    continue

                try:
                    # تنظیم موقت API key برای این فراخوانی
                    # این روش کار نمی‌کند: genai.configure(api_key=api_key_to_use)
                    # برای استفاده از کلیدهای fallback با generate_content باید مستقیماً آن را پاس داد.
                    # اما کتابخانه جنرال لغت گوگل خودش این کار را انجام می دهد اگر پیکربندی شده باشد.
                    # پس اگر genai.configure بالا کار کرده باشد، نیاز به این نیست.
                    # اما اگر بخواهید کلیدهای fallback را امتحان کنید، باید مستقیماً با requests کار کنید
                    # یا هر بار genai.configure را فراخوانی کنید که توصیه نمی‌شود.

                    # رویکرد پیشنهادی برای امتحان کردن چند کلید با کتابخانه genai:
                    # هر بار genai.configure را با کلید جدید فراخوانی می‌کنیم.
                    # این تنها راه ساده برای استفاده از قابلیت fallback با genai است.
                    genai.configure(api_key=api_key_to_use)

                    model = genai.GenerativeModel(model_name=model_name)
                    
                    response = model.generate_content(
                        user_message,
                        generation_config={"temperature": 0.7, "topP": 0.9, "topK": 40},
                        safety_settings={
                            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                        }
                    )
                    
                    # بررسی پاسخ برای اطمینان از وجود محتوا
                    if hasattr(response, 'text') and response.text:
                        gemini_response_text = response.text
                        api_call_successful = True
                        print(f"Gemini API call successful with key index {i+1}. Reply: {gemini_response_text[:50]}...") # نمایش 50 کاراکتر اول
                        break # اگر موفقیت آمیز بود، از حلقه خارج شو
                    else:
                        print(f"Gemini API call with key index {i+1} returned no text. Response: {response}")
                        # شاید خطایی در پاسخ باشد، به کلید بعدی برو

                except Exception as e:
                    print(f"Error calling Gemini API with key index {i+1}: {e}")
                    # اگر خطایی رخ داد، کلید بعدی را امتحان کن
                    continue

            if api_call_successful:
                print("Sending successful Gemini response.")
                return JsonResponse({'response': gemini_response_text})
            else:
                print("All Gemini API keys failed.")
                return JsonResponse({'error': 'خطا در برقراری ارتباط با AysChat. تمام کلیدهای API نامعتبر بودند یا به محدودیت رسیده‌اند. لطفاً بعداً تلاش کنید.'}, status=500)

        except json.JSONDecodeError:
            print("Error: Invalid JSON in request body.")
            return JsonResponse({'error': 'فرمت JSON نامعتبر.'}, status=400)
        except Exception as e:
            # log the full traceback for unexpected errors
            import traceback
            print(f"An unexpected error occurred in chat_api: {e}")
            traceback.print_exc() # این traceback کامل را در لاگ ها نشان می دهد
            return JsonResponse({'error': f'خطای داخلی سرور: {e}'}, status=500)
    else:
        print("Error: Only POST requests are allowed.")
        return JsonResponse({'error': 'فقط درخواست‌های POST پشتیبانی می‌شوند.'}, status=405)
