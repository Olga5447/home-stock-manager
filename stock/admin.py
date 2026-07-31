from django.contrib import admin
from .models import Product, Batch, Operation, ShoppingListItem, Notification, Unit, StorageLocation

# Register your models here.
@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name']

@admin.register(StorageLocation)
class StorageLocationAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'category', 'minimum_stock', 'get_current_stock']
    list_filter = ['category', 'user']
    search_fields = ['name']

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ['product', 'quantity_remaining', 'purchased_at', 'expires_at', 'storage_location']
    list_filter = ['storage_location', 'is_discarded']

@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = ['product', 'operation_type', 'quantity', 'created_at']
    list_filter = ['operation_type']

@admin.register(ShoppingListItem)
class ShoppingListItemAdmin(admin.ModelAdmin):
    list_display = ['product', 'recommended_quantity', 'is_purchased']
    list_filter = ['is_purchased']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'message', 'created_at', 'read_at']
    list_filter = ['type', 'read_at']