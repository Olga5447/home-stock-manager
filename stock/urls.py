from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'batches', BatchViewSet, basename='batch')
router.register(r'shopping-list', ShoppingListViewSet, basename='shopping-list')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    # Аутентификация
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/me/', MeView.as_view(), name='me'),
    
    # API
    path('', include(router.urls)),
]