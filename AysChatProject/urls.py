"""
URL configuration for AysChatProgect project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# AysChat_Django/AysChatProject/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),           # فقط یک بار ادمین را در اینجا تعریف کنید
    path('chat/', include('chat_app.urls')),   # تمام آدرس‌های زیر /chat/ را به chat_app/urls.py بفرست
    # !!! تمام خطوط دیگر (به خصوص path('', include('chatbot_app.urls'))) را حذف کنید !!!
    # !!! و هیچ TemplateView یا static file serving برای ریشه سایت نداشته باشید !!!
]
