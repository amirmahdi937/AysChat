from django.urls import path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('chat/', include('chat_app.urls')),
]
