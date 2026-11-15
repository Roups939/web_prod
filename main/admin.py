from django.contrib import admin
from .models import Currency, Account, Transaction

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'current_rate')
    search_fields = ('code', 'name')

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'currency', 'balance')
    list_filter = ('currency',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('account', 'transaction_type', 'amount', 'rate_at_moment', 'date')
    list_filter = ('transaction_type', 'date')