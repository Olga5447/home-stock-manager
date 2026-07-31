from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal

# Create your models here.
class Unit(models.Model):
    """Единицы измерения"""
    UNIT_CHOICES = [
        ('piece', 'штука'),
        ('gram', 'грамм'),
        ('kilogram', 'килограмм'),
        ('milliliter', 'миллилитр'),
        ('liter', 'литр'),
        ('package', 'упаковка'),
    ]
    name = models.CharField(max_length=20, choices=UNIT_CHOICES, unique=True)
    display_name = models.CharField(max_length=50)
    
    def __str__(self):
        return self.display_name

class StorageLocation(models.Model):
    """Места хранения"""
    LOCATION_CHOICES = [
        ('fridge', 'Холодильник'),
        ('freezer', 'Морозильник'),
        ('cabinet', 'Кухонный шкаф'),
        ('pantry', 'Кладовая'),
        ('bathroom', 'Ванная'),
        ('other', 'Другое'),
    ]
    name = models.CharField(max_length=50, choices=LOCATION_CHOICES, unique=True)
    
    def __str__(self):
        return dict(self.LOCATION_CHOICES)[self.name]

class Product(models.Model):
    """Товар"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True)
    default_unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    minimum_stock = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'name']  # У одного пользователя не может быть двух товаров с одинаковым именем
    
    def __str__(self):
        return f"{self.name}"
    
    def get_current_stock(self):
        """Получить текущий остаток"""
        result = self.batches.filter(is_discarded=False).aggregate(
            total=models.Sum('quantity_remaining')
        )
        return result['total'] or Decimal('0')
    
    def get_status(self):
        """Получить статус товара"""
        stock = self.get_current_stock()
        if stock == 0:
            return 'out_of_stock'
        if stock < self.minimum_stock:
            return 'low'
        return 'enough'

class Batch(models.Model):
    """Партия товара"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='batches')
    quantity_initial = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    quantity_remaining = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    purchased_at = models.DateField()
    expires_at = models.DateField(null=True, blank=True)
    storage_location = models.ForeignKey(StorageLocation, on_delete=models.SET_NULL, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    is_discarded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['expires_at']  # Сортировка по сроку годности
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity_remaining} {self.product.default_unit.name}"

class Operation(models.Model):
    """Операция с запасом"""
    OPERATION_TYPES = [
        ('purchase', 'Покупка'),
        ('consume', 'Расход'),
        ('discard', 'Выбрасывание'),
        ('correction', 'Корректировка'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='operations')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='operations', null=True, blank=True)
    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    created_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.get_operation_type_display()} - {self.product.name} - {self.quantity}"

class ShoppingListItem(models.Model):
    """Элемент списка покупок"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='shopping_list_items')
    recommended_quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    reason = models.TextField()
    priority = models.CharField(
        max_length=10,
        choices=[('low', 'Низкий'), ('medium', 'Средний'), ('high', 'Высокий')],
        default='medium'
    )
    added_automatically = models.BooleanField(default=False)
    is_purchased = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Notification(models.Model):
    """Уведомление"""
    NOTIFICATION_TYPES = [
        ('expiring_soon', 'Скоро истекает'),
        ('expired', 'Просрочен'),
        ('low_stock', 'Низкий остаток'),
        ('will_end_soon', 'Скоро закончится'),
        ('waste_risk', 'Риск выбрасывания'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']