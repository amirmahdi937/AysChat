# AysChat_Django/chat_app/views.py

import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging # اضافه کردن لاگینگ

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.generativeai.types import BrokenResponseError
from google.generativeai import GenerativeModel # اضافه کردن GenerativeModel برای تعریف نوع

# پیکربندی لاگینگ
logger = logging.getLogger(__name__)

# ------------------- مدیریت امن کلیدهای API -------------------
# بهتر است کلیدها را یک بار در زمان شروع برنامه بارگذاری کنیم نه در هر درخواست
GEMINI_API_KEYS = []
for i in range(1, 4): # فرض می‌کنیم تا 3 کلید داریم (GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3)
    key = os.getenv(f'GEMINI_API_KEY_{i}')
    if key:
        GEMINI_API_KEYS.append(key)
    else:
        # برای حالت‌های توسعه که شاید فقط GEMINI_API_KEY تنظیم شده باشد
        if i == 1 and not os.getenv('GEMINI_API_KEY_2') and not os.getenv('GEMINI_API_KEY_3'):
            main_key = os.getenv('GEMINI_API_KEY')
            if main_key and main_key not in GEMINI_API_KEYS:
                GEMINI_API_KEYS.append(main_key)

if not GEMINI_API_KEYS:
    logger.warning("No Gemini API keys found in environment variables. Ensure GEMINI_API_KEY, GEMINI_API_KEY_2, etc., are set.")
    # در محیط Production باید حتماً کلیدها تنظیم شوند. این فقط برای توسعه محلی است.
    # در محیط Production (Render) باید GEMINI_API_KEY_1 و غیره را در Environment Variables تنظیم کنید.
    # اگر نیاز به dotenv در محیط محلی دارید، آن را خارج از این فایل و در manage.py یا settings.py لود کنید.
    # from dotenv import load_dotenv
    # load_dotenv()
    # for i in range(1, 4):
    #     key = os.getenv(f'GEMINI_API_KEY_{i}')
    #     if key and key not in GEMINI_API_KEYS:
    #         GEMINI_API_KEYS.append(key)
    # if not GEMINI_API_KEYS:
    #     logger.error("Still no Gemini API keys found after trying .env fallback.")

logger.info(f"Loaded {len(GEMINI_API_KEYS)} Gemini API keys.")

# برای حفظ تاریخچه چت، از یک دیکشنری ساده استفاده می‌کنیم.
# در یک برنامه واقعی، باید این را با یک پایگاه داده یا سیستم کشینگ (مثل Redis) جایگزین کنید.
chat_sessions = {} # {session_id: GenerativeModel.chat_session}

# ---------------------------------------------------------------

@csrf_exempt
def chat_api(request):
    logger.info("-------------------- Incoming chat_api request --------------------")
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('prompt').strip()
            session_id = request.COOKIES.get('session_id') # فرض کنید session_id از کوکی می‌آید.
                                                           # در غیر این صورت، می‌توانید از IP یا روش دیگری استفاده کنید.
            if not session_id:
                # یک session_id ساده ایجاد می‌کنیم اگر وجود ندارد. در تولید واقعی بهتر است از uuid استفاده کنید.
                session_id = request.META.get('REMOTE_ADDR', 'anonymous_user') # یا از یک uuid واقعی استفاده کنید
                logger.warning(f"No session_id found. Using default: {session_id}")

            logger.info(f"Received raw prompt: '{user_message}' for session: {session_id}")

            if not user_message:
                logger.warning("Error: Empty prompt received.")
                return JsonResponse({'error': 'پیام خالی ارسال شده است.'}, status=400)

            lower_case_message = user_message.lower()
            if any(phrase in lower_case_message for phrase in ['چه کسی تو را ساخته', 'چه کسی ساخته شدی', 'سازنده تو کیست', 'توسط چه کسی آموزش دیده ای', 'تو کی هستی']):
                logger.info("Responding with predefined answer for 'who made you'.")
                return JsonResponse({'response': 'من یک هوش مصنوعی هستم که توسط تیم AysChat توسعه و آموزش داده شده‌ام.'})

            if not GEMINI_API_KEYS:
                logger.error("Error: No Gemini API keys available. Please configure them in Render environment variables.")
                return JsonResponse({'error': 'کلیدهای API Gemini تنظیم نشده‌اند. لطفاً با مدیر سایت تماس بگیرید.'}, status=500)

            model_name = 'gemini-pro' # مطمئن شوید این مدل در منطقه شما در دسترس است
            gemini_response_text = "خطا در پردازش پاسخ. لطفاً دوباره تلاش کنید."
            api_call_successful = False
            
            safety_block_reason = None # برای نگهداری دلیل بلاک شدن ایمنی

            # اگر session_id قبلاً چت سشن دارد، آن را بازیابی می‌کنیم، در غیر این صورت جدید ایجاد می‌کنیم
            if session_id not in chat_sessions:
                chat_sessions[session_id] = None # placeholder

            # تلاش برای هر کلید API
            for i, api_key_to_use in enumerate(GEMINI_API_KEYS):
                logger.info(f"Attempting API call with key index {i+1}...")
                if not api_key_to_use:
                    logger.warning(f"Skipping key index {i+1} as it's empty.")
                    continue

                try:
                    genai.configure(api_key=api_key_to_use) # هر بار کلید را تنظیم کنید
                    
                    # اگر مدل قبلاً برای این سشن ایجاد نشده، ایجاد کنید
                    if chat_sessions[session_id] is None:
                        model = genai.GenerativeModel(model_name=model_name)
                        # شروع چت سشن و ذخیره آن
                        chat_sessions[session_id] = model.start_chat(history=[])
                        logger.info(f"New chat session started for session_id: {session_id}")
                    
                    convo = chat_sessions[session_id] # استفاده از سشن موجود
                    
                    # تنظیمات جنریشن
                    generation_config = {
                        "temperature": 0.7, 
                        "top_p": 0.9, 
                        "top_k": 40
                    }

                    # تنظیمات ایمنی برای جلوگیری از بلاک شدن پیام‌های بی‌خطر
                    safety_settings = {
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    }
                    
                    # ارسال پیام به مدل و دریافت پاسخ
                    response = convo.send_message(
                        user_message,
                        generation_config=generation_config,
                        safety_settings=safety_settings
                    )

                    if hasattr(response, 'text') and response.text:
                        gemini_response_text = response.text
                        api_call_successful = True
                        logger.info(f"Gemini API call successful with key index {i+1}. Reply: {gemini_response_text[:100]}...")
                        break # اگر موفق بود، از حلقه خارج می‌شویم
                    else:
                        logger.warning(f"Gemini API call with key index {i+1} returned no text for prompt: '{user_message}'. Checking prompt feedback...")
                        if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                            safety_block_reason = response.prompt_feedback.safety_ratings
                            logger.warning(f"Prompt blocked due to safety: {safety_block_reason}")
                        elif hasattr(response, 'candidates') and response.candidates:
                            # بررسی دلیل بلاک شدن کاندیداها
                            for candidate in response.candidates:
                                if hasattr(candidate, 'finish_reason') and candidate.finish_reason == 'SAFETY':
                                    if hasattr(candidate, 'safety_ratings'):
                                        safety_block_reason = candidate.safety_ratings
                                        logger.warning(f"Candidate blocked due to safety: {safety_block_reason}")
                                        break # دلیل بلاک شدن را پیدا کردیم
                        else:
                            logger.warning(f"No specific safety feedback found for response: {response}")
                        continue # به کلید بعدی می‌رویم

                except BrokenResponseError as bre:
                    logger.error(f"BrokenResponseError with key index {i+1} for prompt: '{user_message}': {bre}")
                    if hasattr(bre, 'response') and hasattr(bre.response, 'prompt_feedback') and bre.response.prompt_feedback:
                        safety_block_reason = bre.response.prompt_feedback.safety_ratings
                        logger.warning(f"Prompt blocked due to safety in BrokenResponseError: {safety_block_reason}")
                    # ادامه به کلید بعدی
                    continue
                except Exception as e:
                    logger.error(f"An general error occurred calling Gemini API with key index {i+1} for prompt: '{user_message}': {e}", exc_info=True)
                    # ادامه به کلید بعدی
                    continue
            
            # پس از تلاش برای تمام کلیدها
            if api_call_successful:
                logger.info("Sending successful Gemini response.")
                return JsonResponse({'response': gemini_response_text})
            else:
                logger.error("All Gemini API keys failed or responses were blocked for prompt: '{user_message}'.")
                error_message = 'خطا در برقراری ارتباط با AysChat. تمام کلیدهای API نامعتبر بودند یا به محدودیت رسیده‌اند.'
                if safety_block_reason:
                    error_message += f' دلیل: محتوای ارسالی با قوانین ایمنی Gemini مطابقت ندارد. {safety_block_reason}'
                else:
                    error_message += ' لطفاً بعداً تلاش کنید.'
                return JsonResponse({'error': error_message}, status=500)

        except json.JSONDecodeError:
            logger.error("Error: Invalid JSON in request body.")
            return JsonResponse({'error': 'فرمت JSON نامعتبر.'}, status=400)
        except Exception as e:
            import traceback
            logger.critical(f"An unexpected critical error occurred in chat_api: {e}", exc_info=True)
            traceback.print_exc()
            return JsonResponse({'error': f'خطای داخلی سرور: {e}'}, status=500)
    else:
        logger.warning("Error: Only POST requests are allowed.")
        return JsonResponse({'error': 'فقط درخواست‌های POST پشتیبانی می‌شوند.'}, status=405)
