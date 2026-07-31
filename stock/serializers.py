from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Product, Batch, Operation, ShoppingListItem, Notification, Unit, StorageLocation

class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}
    
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class ProductSerializer(serializers.ModelSerializer):
    """Сериализатор товара"""
    current_stock = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'category', 'default_unit', 'minimum_stock', 
                 'current_stock', 'status', 'created_at']
        read_only_fields = ['created_at']
    
    def get_current_stock(self, obj):
        return obj.get_current_stock()
    
    def get_status(self, obj):
        return obj.get_status()

class BatchSerializer(serializers.ModelSerializer):
    """Сериализатор партии"""
    class Meta:
        model = Batch
        fields = ['id', 'product', 'quantity_initial', 'quantity_remaining', 
                 'purchased_at', 'expires_at', 'storage_location', 'price', 
                 'is_discarded', 'created_at']
        read_only_fields = ['created_at']
    
    def validate(self, data):
        """Проверка дат"""
        if data.get('expires_at') and data.get('purchased_at'):
            if data['expires_at'] < data['purchased_at']:
                raise serializers.ValidationError(
                    "Срок годности не может быть раньше даты покупки"
                )
        return data

class OperationSerializer(serializers.ModelSerializer):
    """Сериализатор операции"""
    operation_type_display = serializers.CharField(
        source='get_operation_type_display', 
        read_only=True
    )
    
    class Meta:
        model = Operation
        fields = ['id', 'product', 'batch', 'operation_type', 'operation_type_display',
                 'quantity', 'created_at', 'comment']
        read_only_fields = ['created_at']

class ShoppingListItemSerializer(serializers.ModelSerializer):
    """Сериализатор списка покупок"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = ShoppingListItem
        fields = ['id', 'product', 'product_name', 'recommended_quantity', 
                 'reason', 'priority', 'added_automatically', 'is_purchased', 
                 'created_at']
        read_only_fields = ['created_at']

class NotificationSerializer(serializers.ModelSerializer):
    """Сериализатор уведомлений"""
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = ['id', 'type', 'type_display', 'product', 'batch', 
                 'message', 'created_at', 'read_at']
        read_only_fields = ['created_at']