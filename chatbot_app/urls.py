# AysChat_Django/chat_app/urls.py

from django.urls import path
from . import views # از .views برای ایمپورت کردن views از همین اپلیکیشن استفاده کنید

urlpatterns = [
    path('chat/', views.chat_api, name='chat_api'), # این خط اصلی API شماست. نام 'chat_api' را به آن بدهید.
    # !!! تمام خطوط دیگر (مثل path('admin/', ...) یا path('chat/', include(...))) را حذف کنید !!!
]
