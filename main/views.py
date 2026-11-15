from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import Account, Transaction, Currency
from decimal import Decimal

@login_required
def dashboard(request):
    #все счета текущего пользователя
    accounts = Account.objects.filter(user=request.user).select_related('currency')
    
    total_balance_rub = Decimal('0.00')
    total_profit_rub = Decimal('0.00')

    #общая сумма и прибыль по каждому счету
    for account in accounts:
        #стоимость счета в рублях
        current_value_rub = account.balance * account.currency.current_rate
        
        #sum покупок - sum продаж
        transactions = account.transactions.all()
        invested_rub = Decimal('0.00')
        for t in transactions:
            if t.transaction_type == 'BUY':
                invested_rub += (t.amount * t.rate_at_moment)
            elif t.transaction_type == 'SELL':
                invested_rub -= (t.amount * t.rate_at_moment)
        
        #gрибыль
        profit_rub = current_value_rub - invested_rub
        
        account.current_value_rub = current_value_rub
        account.profit_rub = profit_rub
        
        total_balance_rub += current_value_rub
        total_profit_rub += profit_rub

    context = {
        'accounts': accounts,
        'total_balance_rub': total_balance_rub,
        'total_profit_rub': total_profit_rub,
    }
    
    return render(request, 'main/dashboard.html', context)