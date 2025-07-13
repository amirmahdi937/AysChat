# AysChat_Django/chat_app/views.py

import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.generativeai.types import BrokenResponseError # این خط را اضافه کنید

# ... (کدهای ایمپورت و تنظیمات API Key شما در ابتدای فایل) ...

# ------------------- مدیریت امن کلیدهای API -------------------
try:
    GENAI_MAIN_API_KEY = os.environ.get('GEMINI_API_KEY')
    if GENAI_MAIN_API_KEY:
        genai.configure(api_key=GENAI_MAIN_API_KEY)
    else:
        print("WARNING: GEMINI_API_KEY not set in environment variables for genai.configure. Trying fallback keys.")
except Exception as e:
    print(f"Error configuring genai with main API key: {e}")

FALLBACK_GEMINI_API_KEYS = [
    os.getenv('GEMINI_API_KEY'),
    os.getenv('GEMINI_API_KEY_2'),
    os.getenv('GEMINI_API_KEY_3'),
]
FALLBACK_GEMINI_API_KEYS = [key for key in FALLBACK_GEMINI_API_KEYS if key]
print(f"Loaded {len(FALLBACK_GEMINI_API_KEYS)} fallback Gemini API keys.")

# ---------------------------------------------------------------

@csrf_exempt
def chat_api(request):
    print("-------------------- Incoming chat_api request --------------------")
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('prompt', '').strip()
            print(f"Received raw prompt: '{user_message}'")

            if not user_message:
                print("Error: Empty prompt received.")
                return JsonResponse({'error': 'پیام خالی ارسال شده است.'}, status=400)

            lower_case_message = user_message.lower()
            if any(phrase in lower_case_message for phrase in ['چه کسی تو را ساخته', 'چه کسی ساخته شدی', 'سازنده تو کیست', 'توسط چه کسی آموزش دیده ای', 'تو کی هستی']):
                print("Responding with predefined answer for 'who made you'.")
                return JsonResponse({'response': 'من یک هوش مصنوعی هستم که توسط تیم AysChat توسعه و آموزش داده شده‌ام.'})

            if not FALLBACK_GEMINI_API_KEYS:
                print("Error: No Gemini API keys available for fallback.")
                return JsonResponse({'error': 'کلیدهای API Gemini تنظیم نشده‌اند. لطفاً با مدیر سایت تماس بگیرید.'}, status=500)

            model_name = 'gemini-pro' # مطمئن شوید این مدل در منطقه شما در دسترس است
            gemini_response_text = "خطا در پردازش پاسخ. لطفاً دوباره تلاش کنید."
            api_call_successful = False

            # برای مدیریت BrokenResponseError و لاگ کردن دلیل بلاک شدن
            safety_block_reason = None

            for i, api_key_to_use in enumerate(FALLBACK_GEMINI_API_KEYS):
                print(f"Attempting API call with key index {i+1}...")
                if not api_key_to_use:
                    print(f"Skipping key index {i+1} as it's empty.")
                    continue

                try:
                    genai.configure(api_key=api_key_to_use) # هر بار کلید را تنظیم کنید
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

                    if hasattr(response, 'text') and response.text:
                        gemini_response_text = response.text
                        api_call_successful = True
                        print(f"Gemini API call successful with key index {i+1}. Reply: {gemini_response_text[:50]}...")
                        break
                    else:
                        # این قسمت مهم است: اگر متن نیست، دلیل آن را پیدا کنید
                        print(f"Gemini API call with key index {i+1} returned no text. Checking prompt feedback...")
                        if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                            safety_block_reason = response.prompt_feedback.safety_ratings
                            print(f"Prompt blocked due to safety: {safety_block_reason}")
                        elif hasattr(response, 'candidates') and response.candidates:
                            for candidate in response.candidates:
                                if hasattr(candidate, 'finish_reason') and candidate.finish_reason == 'SAFETY':
                                    if hasattr(candidate, 'safety_ratings'):
                                        safety_block_reason = candidate.safety_ratings
                                        print(f"Candidate blocked due to safety: {safety_block_reason}")
                                        break # دلیل بلاک شدن را پیدا کردیم
                        else:
                            print(f"No specific safety feedback found for response: {response}")
                        # ادامه به کلید بعدی
                        continue

                except BrokenResponseError as bre: # اضافه کردن مدیریت برای این خطا
                    print(f"BrokenResponseError with key index {i+1}: {bre}")
                    # معمولا این خطا به دلیل بلاک شدن ایمنی است، لاگ آن را بررسی کنید
                    # اگر به خاطر safety بود، دلیلش در `bre` است.
                    if hasattr(bre, 'response') and hasattr(bre.response, 'prompt_feedback') and bre.response.prompt_feedback:
                        safety_block_reason = bre.response.prompt_feedback.safety_ratings
                        print(f"Prompt blocked due to safety in BrokenResponseError: {safety_block_reason}")
                    # ادامه به کلید بعدی
                    continue
                except Exception as e:
                    print(f"An general error occurred calling Gemini API with key index {i+1}: {e}")
                    # ادامه به کلید بعدی
                    continue

        if api_call_successful:
            print("Sending successful Gemini response.")
            return JsonResponse({'response': gemini_response_text})
        else:
            print("All Gemini API keys failed or responses were blocked.")
            error_message = 'خطا در برقراری ارتباط با AysChat. تمام کلیدهای API نامعتبر بودند یا به محدودیت رسیده‌اند.'
            if safety_block_reason:
                error_message += f' دلیل: محتوای ارسالی با قوانین ایمنی Gemini مطابقت ندارد. {safety_block_reason}'
            else:
                error_message += ' لطفاً بعداً تلاش کنید.'
            return JsonResponse({'error': error_message}, status=500)

    except json.JSONDecodeError:
        print("Error: Invalid JSON in request body.")
        return JsonResponse({'error': 'فرمت JSON نامعتبر.'}, status=400)
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in chat_api: {e}")
        traceback.print_exc()
        return JsonResponse({'error': f'خطای داخلی سرور: {e}'}, status=500)
else:
    print("Error: Only POST requests are allowed.")
    return JsonResponse({'error': 'فقط درخواست‌های POST پشتیبانی می‌شوند.'}, status=405)
