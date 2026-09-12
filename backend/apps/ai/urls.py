from django.urls import path

from . import views

urlpatterns = [
    path("<str:organizacion_id>/conversations/", views.conversations),
    path("<str:organizacion_id>/conversations/<int:conversation_id>/", views.conversation_detail),
    path("<str:organizacion_id>/conversations/<int:conversation_id>/messages/", views.send_message),
]
