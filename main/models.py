from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator

class Currency(models.Model):#валюты и курсы
    code = models.CharField(max_length=3, unique=True, verbose_name="Код валюты")
    name = models.CharField(max_length=50, verbose_name="Название")
    current_rate = models.DecimalField(
        max_digits=10, decimal_places=4, default=0.0, verbose_name="Текущий курс к рублю"
    )
    last_updated = models.DateTimeField(auto_now=True, verbose_name="Последнее обновление")
    cbr_id = models.CharField(max_length=10, blank=True, null=True, verbose_name="ID в ЦБ")

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        verbose_name = "Валюта"
        verbose_name_plural = "Валюты"


class Account(models.Model):#портфель, привязанн к user и currency
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="accounts", 
        verbose_name="Пользователь"
    )
    name = models.CharField(max_length=100, verbose_name="Название счета")
    currency = models.ForeignKey(
        Currency, 
        on_delete=models.PROTECT, 
        verbose_name="Валюта"
    )
    balance = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0.0, 
        verbose_name="Текущий баланс"
    )

    def __str__(self):
        return f"{self.name} ({self.currency.code})"

    class Meta:
        verbose_name = "Счет"
        verbose_name_plural = "Счета"


class Transaction(models.Model):#история операций
    TRANSACTION_TYPES = (
        ('BUY', 'Покупка'),
        ('SELL', 'Продажа'),
    )
    
    account = models.ForeignKey(
        Account, 
        on_delete=models.CASCADE, 
        related_name="transactions", 
        verbose_name="Счет"
    )
    transaction_type = models.CharField(
        max_length=4, 
        choices=TRANSACTION_TYPES, 
        verbose_name="Тип операции"
    )
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(0.01)], 
        verbose_name="Количество валюты"
    )
    
    rate_at_moment = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        verbose_name="Курс на момент операции"
    )
    
    is_manual_rate = models.BooleanField(default=False, verbose_name="Ручной курс")
    
    date = models.DateField(verbose_name="Дата операции")
    
    rate_date = models.DateField(null=True, blank=True, verbose_name="Дата курса")

    def __str__(self):
        return f"{self.get_transaction_type_display()} {self.amount} {self.account.currency.code}"

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"
