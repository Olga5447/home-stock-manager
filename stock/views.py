from django.shortcuts import render

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from decimal import Decimal
from datetime import date
from .models import Product, Batch, Operation, ShoppingListItem, Notification, StorageLocation
from .serializers import *
from .services import StockService, ForecastService

# Create your views here.
class RegisterView(generics.CreateAPIView):
    """Регистрация пользователя"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

class LoginView(TokenObtainPairView):
    """Вход (получение JWT токена)"""
    permission_classes = [AllowAny]

class MeView(generics.RetrieveAPIView):
    """Информация о текущем пользователе"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user

class ProductViewSet(viewsets.ModelViewSet):
    """CRUD для товаров"""
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Product.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def batches(self, request, pk=None):
        """Добавить партию"""
        product = self.get_object()
        serializer = BatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Проверка идемпотентности
        idempotency_key = request.headers.get('Idempotency-Key')
        if idempotency_key:
            if Operation.objects.filter(
                idempotency_key=idempotency_key, 
                product=product
            ).exists():
                return Response(
                    {'message': 'Повторный запрос'}, 
                    status=status.HTTP_200_OK
                )
        
        # Получаем место хранения
        storage = None
        if serializer.validated_data.get('storage_location'):
            storage = get_object_or_404(
                StorageLocation, 
                name=serializer.validated_data['storage_location']
            )
        
        batch = StockService.add_batch(
            product=product,
            quantity=serializer.validated_data['quantity'],
            purchased_at=serializer.validated_data['purchased_at'],
            expires_at=serializer.validated_data.get('expires_at'),
            storage_location=storage,
            price=serializer.validated_data.get('price'),
            idempotency_key=idempotency_key
        )
        
        return Response(
            BatchSerializer(batch).data, 
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def consume(self, request, pk=None):
        """Списать товар"""
        product = self.get_object()
        quantity = Decimal(str(request.data.get('quantity')))
        strategy = request.data.get('strategy', 'expires_first')
        
        # Проверка идемпотентности
        idempotency_key = request.headers.get('Idempotency-Key')
        if idempotency_key:
            if Operation.objects.filter(
                idempotency_key=idempotency_key,
                product=product,
                operation_type='consume'
            ).exists():
                return Response(
                    {'message': 'Повторный запрос'}, 
                    status=status.HTTP_200_OK
                )
        
        try:
            StockService.consume_product(
                product=product,
                quantity=quantity,
                strategy=strategy,
                batch_id=request.data.get('batch_id'),
                comment=request.data.get('comment', '')
            )
            return Response(
                {'message': 'Товар успешно списан'}, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    'code': 'INSUFFICIENT_STOCK',
                    'message': str(e),
                    'details': {
                        'requested': float(quantity),
                        'available': float(product.get_current_stock())
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def forecast(self, request, pk=None):
        """Прогноз расхода"""
        product = self.get_object()
        days = int(request.query_params.get('days', 14))
        forecast = ForecastService.calculate_forecast(product, days)
        forecast['product_id'] = product.id
        return Response(forecast)

class BatchViewSet(viewsets.ModelViewSet):
    """CRUD для партий"""
    serializer_class = BatchSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Batch.objects.filter(product__user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def discard(self, request, pk=None):
        """Выбросить партию"""
        batch = self.get_object()
        quantity = Decimal(str(request.data.get('quantity')))
        reason = request.data.get('reason', 'other')
        
        # Проверка идемпотентности
        idempotency_key = request.headers.get('Idempotency-Key')
        if idempotency_key:
            if Operation.objects.filter(
                idempotency_key=idempotency_key,
                batch=batch,
                operation_type='discard'
            ).exists():
                return Response(
                    {'message': 'Повторный запрос'}, 
                    status=status.HTTP_200_OK
                )
        
        try:
            StockService.discard_batch(batch, quantity, reason)
            return Response(
                {'message': 'Товар выброшен'}, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    'code': 'VALIDATION_ERROR',
                    'message': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

class ShoppingListViewSet(viewsets.ModelViewSet):
    """Список покупок"""
    serializer_class = ShoppingListItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ShoppingListItem.objects.filter(
            product__user=self.request.user,
            is_purchased=False
        )
    
    @action(detail=True, methods=['post'])
    def purchase(self, request, pk=None):
        """Завершить покупку"""
        item = self.get_object()
        
        # Если переданы данные, создаем партию
        if request.data.get('quantity'):
            product = item.product
            storage = None
            if request.data.get('storage_location'):
                storage = get_object_or_404(
                    StorageLocation, 
                    name=request.data['storage_location']
                )
            
            StockService.add_batch(
                product=product,
                quantity=Decimal(str(request.data['quantity'])),
                purchased_at=request.data.get('purchased_at', date.today()),
                expires_at=request.data.get('expires_at'),
                storage_location=storage,
                price=request.data.get('price')
            )
        
        item.is_purchased = True
        item.save()
        
        return Response(
            {'message': 'Покупка завершена'}, 
            status=status.HTTP_200_OK
        )

class NotificationViewSet(viewsets.ModelViewSet):
    """Уведомления"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """Отметить как прочитанное"""
        notification = self.get_object()
        notification.read_at = date.today()
        notification.save()
        return Response({'message': 'Уведомление прочитано'})