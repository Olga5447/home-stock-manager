from decimal import Decimal
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Sum
from django.core.exceptions import ValidationError
from .models import Product, Batch, Operation

class StockService:
    """Сервис управления запасами"""
    
    @staticmethod
    def add_batch(product, quantity, purchased_at, expires_at=None, 
                  storage_location=None, price=None, idempotency_key=None):
        """Добавить партию"""
        with transaction.atomic():
            batch = Batch.objects.create(
                product=product,
                quantity_initial=quantity,
                quantity_remaining=quantity,
                purchased_at=purchased_at,
                expires_at=expires_at,
                storage_location=storage_location,
                price=price
            )
            
            Operation.objects.create(
                product=product,
                batch=batch,
                operation_type='purchase',
                quantity=quantity,
                idempotency_key=idempotency_key
            )
            
            return batch
    
    @staticmethod
    def consume_product(product, quantity, strategy='expires_first', 
                        batch_id=None, comment=''):
        """Списать товар"""
        with transaction.atomic():
            # Проверяем доступное количество
            available = product.get_current_stock()
            if available < quantity:
                raise ValidationError(
                    f"Недостаточно товара. Доступно: {available}"
                )
            
            remaining = quantity
            
            # Получаем партии для списания
            batches = Batch.objects.select_for_update().filter(
                product=product,
                quantity_remaining__gt=0,
                is_discarded=False
            )
            
            # Выбираем стратегию
            if strategy == 'expires_first':
                batches = batches.filter(expires_at__isnull=False).order_by('expires_at')
            elif strategy == 'oldest_first':
                batches = batches.order_by('purchased_at')
            elif strategy == 'manual' and batch_id:
                batches = batches.filter(id=batch_id)
            
            # Списываем
            for batch in batches:
                if remaining <= 0:
                    break
                
                consume = min(batch.quantity_remaining, remaining)
                batch.quantity_remaining -= consume
                batch.save()
                
                Operation.objects.create(
                    product=product,
                    batch=batch,
                    operation_type='consume',
                    quantity=consume,
                    comment=comment
                )
                
                remaining -= consume
            
            if remaining > 0:
                raise ValidationError(f"Не удалось списать {remaining}")
            
            return True
    
    @staticmethod
    def discard_batch(batch, quantity, reason):
        """Выбросить товар"""
        with transaction.atomic():
            if batch.quantity_remaining < quantity:
                raise ValidationError(
                    f"Недостаточно товара. Доступно: {batch.quantity_remaining}"
                )
            
            batch.quantity_remaining -= quantity
            if batch.quantity_remaining == 0:
                batch.is_discarded = True
            batch.save()
            
            Operation.objects.create(
                product=batch.product,
                batch=batch,
                operation_type='discard',
                quantity=quantity,
                comment=f"Причина: {reason}"
            )
            
            return True

class ForecastService:
    """Сервис прогнозирования"""
    
    @staticmethod
    def calculate_forecast(product, days=14):
        """Рассчитать прогноз"""
        operations = Operation.objects.filter(
            product=product,
            operation_type='consume'
        ).order_by('-created_at')
        
        if operations.count() < 3:
            return {
                'estimated_depletion_date': None,
                'confidence': 'insufficient_data'
            }
        
        # Берем последние N дней
        cutoff = date.today() - timedelta(days=days)
        recent = operations.filter(created_at__date__gte=cutoff)
        
        if recent.count() < 3:
            recent = operations[:5]
            days_analyzed = (date.today() - recent.last().created_at.date()).days or 1
        else:
            days_analyzed = days
        
        total = recent.aggregate(total=Sum('quantity'))['total'] or Decimal('0')
        avg_daily = total / max(days_analyzed, 1)
        current = product.get_current_stock()
        
        if avg_daily == 0 or current == 0:
            return {
                'estimated_depletion_date': None,
                'confidence': 'insufficient_data'
            }
        
        days_remaining = int(current / avg_daily)
        
        return {
            'current_stock': current,
            'average_daily_consumption': avg_daily,
            'estimated_days_remaining': days_remaining,
            'estimated_depletion_date': date.today() + timedelta(days=days_remaining),
            'confidence': 'high' if recent.count() > 10 else 'medium' if recent.count() > 5 else 'low',
            'based_on_days': days_analyzed
        }