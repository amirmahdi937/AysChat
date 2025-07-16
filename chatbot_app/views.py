# AysChat_Django/chat_app/views.py

import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.generativeai.types import BrokenResponseError
# نیازی به وارد کردن GenerativeModel به صورت مستقیم در اینجا نیست مگر اینکه به عنوان نوع hint استفاده شود
# from google.generativeai import GenerativeModel 

logger = logging.getLogger(__name__)

# ------------------- مدیریت امن کلیدهای API -------------------
# بهتر است کلیدها را یک بار در زمان شروع برنامه بارگذاری کنیم نه در هر درخواست
# از یک لیست برای نگهداری کلیدها استفاده می کنیم.
GEMINI_API_KEYS = []
# متغیرهای محیطی Render معمولا با GEMINI_API_KEY_1, GEMINI_API_KEY_2 و غیره نامگذاری می‌شوند.
# اگر فقط GEMINI_API_KEY اصلی را دارید، آن را هم اضافه کنید.
# اطمینان حاصل کنید که این متغیرها در تنظیمات Render Services->Environment وارد شده باشند.

# سعی می کنیم تا 5 کلید را بارگذاری کنیم (برای انعطاف پذیری بیشتر)
for i in range(1, 6): 
    key = os.getenv(f'GEMINI_API_KEY_{i}')
    if key:
        GEMINI_API_KEYS.append(key)

# اگر هیچ کلید شماره‌گذاری شده‌ای پیدا نشد، سعی می‌کنیم GEMINI_API_KEY عمومی را پیدا کنیم.
if not GEMINI_API_KEYS:
    main_key = os.getenv('GEMINI_API_KEY')
    if main_key:
        GEMINI_API_KEYS.append(main_key)

if not GEMINI_API_KEYS:
    logger.critical("CRITICAL: No Gemini API keys found in environment variables. Please set GEMINI_API_KEY or GEMINI_API_KEY_1, etc. Service will likely fail.")
else:
    logger.info(f"Successfully loaded {len(GEMINI_API_KEYS)} Gemini API keys.")

# برای حفظ تاریخچه چت، از یک دیکشنری ساده استفاده می‌کنیم.
# در یک برنامه واقعی، باید این را با یک پایگاه داده یا سیستم کشینگ (مثل Redis) جایگزین کنید.
# توجه: در محیط Render، هر درخواست ممکن است توسط یک Process/Worker جدید مدیریت شود.
# این دیکشنری `chat_sessions` فقط برای سشن‌های درون همان Worker پایدار خواهد بود.
# برای یک سیستم پایدار، به Redis یا دیتابیس نیاز دارید. اما برای تست اولیه مشکلی ندارد.
chat_sessions = {} # {session_id: GenerativeModel.chat_session_object}

# ---------------------------------------------------------------

@csrf_exempt
def chat_api(request):
    logger.info("-------------------- Incoming chat_api request --------------------")
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('prompt', '').strip()
            
            # استفاده از session_key جنگو برای session_id پایدارتر
            session_id = request.session.session_key
            if not session_id:
                # این حالت نباید رخ دهد اگر Django Session Middleware فعال باشد
                request.session.save() # اطمینان از اینکه session_key ایجاد شده است
                session_id = request.session.session_key
                logger.warning(f"Django session_id was not available, created new: {session_id}")
            
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
            # این `chat_sessions` در بین درخواست ها و Worker ها پایدار نیست.
            # برای حفظ تاریخچه چت در Production، نیاز به Redis/DB دارید.
            current_convo = chat_sessions.get(session_id)
            if current_convo is None:
                # برای هر سشن یک مدل جدید ایجاد می‌کنیم
                model_instance = genai.GenerativeModel(model_name=model_name)
                current_convo = model_instance.start_chat(history=[])
                chat_sessions[session_id] = current_convo
                logger.info(f"New chat session initialized for session_id: {session_id}")
            
            # تنظیمات جنریشن
            generation_config = {
                "temperature": 0.7, 
                "top_p": 0.9, 
                "top_k": 40
            }

            # تنظیمات ایمنی برای جلوگیری از بلاک شدن پیام‌های بی‌خطر
            # این تنظیمات را در لاگ ها به خوبی کنترل کرده اید.
            safety_settings = [
                {"category": HarmCategory.HARM_CATEGORY_HARASSMENT, "threshold": HarmBlockThreshold.BLOCK_NONE},
                {"category": HarmCategory.HARM_CATEGORY_HATE_SPEECH, "threshold": HarmBlockThreshold.BLOCK_NONE},
                {"category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, "threshold": HarmBlockThreshold.BLOCK_NONE},
                {"category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, "threshold": HarmBlockThreshold.BLOCK_NONE},
            ]
            
            # تلاش برای هر کلید API
            for i, api_key_to_use in enumerate(GEMINI_API_KEYS):
                logger.info(f"Attempting Gemini API call with key index {i+1}...")
                
                try:
                    genai.configure(api_key=api_key_to_use) # هر بار کلید را تنظیم کنید
                    
                    # ارسال پیام به مدل و دریافت پاسخ
                    response = current_convo.send_message(
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
                            for candidate in response.candidates:
                                if hasattr(candidate, 'finish_reason') and candidate.finish_reason == 'SAFETY':
                                    if hasattr(candidate, 'safety_ratings'):
                                        safety_block_reason = candidate.safety_ratings
                                        logger.warning(f"Candidate blocked due to safety: {safety_block_reason}")
                                        break # دلیل بلاک شدن را پیدا کردیم
                        else:
                            logger.warning(f"No specific safety feedback or candidates found for response: {response}")
                        # اگر پاسخی نبود یا بلاک شد، به کلید بعدی می رویم
                        continue 

                except BrokenResponseError as bre:
                    logger.error(f"BrokenResponseError with key index {i+1} for prompt: '{user_message}': {bre}")
                    if hasattr(bre, 'response') and hasattr(bre.response, 'prompt_feedback') and bre.response.prompt_feedback:
                        safety_block_reason = bre.response.prompt_feedback.safety_ratings
                        logger.warning(f"Prompt blocked due to safety in BrokenResponseError: {safety_block_reason}")
                    continue # به کلید بعدی می‌رویم
                except genai.types.StopCandidateException as sce:
                    logger.error(f"StopCandidateException (content blocked by safety filters) with key index {i+1} for prompt: '{user_message}': {sce}")
                    if hasattr(sce, 'response') and hasattr(sce.response, 'prompt_feedback') and sce.response.prompt_feedback:
                        safety_block_reason = sce.response.prompt_feedback.safety_ratings
                        logger.warning(f"Prompt blocked due to safety in StopCandidateException: {safety_block_reason}")
                    continue # به کلید بعدی می‌رویم
                except Exception as e:
                    # این Exception یک خطای عمومی است و ممکن است Timeout را هم شامل شود.
                    # اطلاعات بیشتری را در لاگ ها ثبت می کنیم.
                    logger.exception(f"An unexpected error occurred calling Gemini API with key index {i+1} for prompt: '{user_message}': {e}")
                    continue # به کلید بعدی می‌رویم
            
            # پس از تلاش برای تمام کلیدها
            if api_call_successful:
                logger.info("Sending successful Gemini response to client.")
                return JsonResponse({'response': gemini_response_text})
            else:
                final_error_message = 'خطا در برقراری ارتباط با AysChat. تمام کلیدهای API نامعتبر بودند یا به محدودیت رسیده‌اند.'
                if safety_block_reason:
                    final_error_message += f' دلیل: محتوای ارسالی با قوانین ایمنی Gemini مطابقت ندارد. جزئیات: {safety_block_reason}'
                else:
                    final_error_message += ' لطفاً بعداً تلاش کنید یا با پیام دیگری امتحان کنید.'
                logger.error(f"All Gemini API calls failed for session: {session_id}, prompt: '{user_message}'. Final error: {final_error_message}")
                return JsonResponse({'error': final_error_message}, status=500)

        except json.JSONDecodeError:
            logger.error("Error: Invalid JSON in request body.", exc_info=True)
            return JsonResponse({'error': 'فرمت JSON ارسالی نامعتبر است. لطفاً ساختار پیام را بررسی کنید.'}, status=400)
        except Exception as e:
            logger.critical(f"An unexpected critical error occurred in chat_api outside of Gemini call: {e}", exc_info=True)
            return JsonResponse({'error': f'خطای داخلی سرور: {e}. لطفاً لاگ‌های سرور را بررسی کنید.'}, status=500)
    else:
        logger.warning("Error: Only POST requests are allowed for this endpoint.")
        return JsonResponse({'error': 'فقط درخواست‌های POST پشتیبانی می‌شوند.'}, status=405)
