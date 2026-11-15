from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views import generic
from decimal import Decimal
from .models import Account, Transaction, Currency
from .forms import TransactionForm


class RegisterView(generic.CreateView):
    form_class = UserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')

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

@login_required
def add_transaction(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save(commit=False)
            account = transaction.account
            if transaction.transaction_type == 'BUY':
                account.balance += transaction.amount
            elif transaction.transaction_type == 'SELL':
                account.balance -= transaction.amount
            
            transaction.save()
            account.save()
            messages.success(request, 'Транзакция успешно добавлена!')
            return redirect('dashboard')
    else:
        form = TransactionForm(user=request.user)
    
    return render(request, 'main/add_transaction.html', {'form': form})