from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views import generic
from decimal import Decimal
from .models import Account, Transaction, Currency
from .forms import TransactionForm
from .forms import AccountForm
from django.core.management import call_command
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from .api_cbr import get_rate_on_date


class RegisterView(generic.CreateView):
    form_class = UserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')

@login_required
def dashboard(request):
    accounts = Account.objects.filter(user=request.user).select_related('currency')
    
    total_balance_rub = Decimal('0.00')
    total_profit_rub = Decimal('0.00')

    for account in accounts:
        current_value_rub = account.balance * account.currency.current_rate
        
        transactions = account.transactions.all()
        invested_rub = Decimal('0.00')
        for t in transactions:
            if t.transaction_type == 'BUY':
                invested_rub += (t.amount * t.rate_at_moment)
            elif t.transaction_type == 'SELL':
                invested_rub -= (t.amount * t.rate_at_moment)
        
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

    currencies = {c.code: c.cbr_id for c in Currency.objects.all()}
    return render(request, 'main/add_transaction.html', {'form': form, 'currencies': currencies})

def home(request):
    top_currencies = Currency.objects.order_by('-current_rate')[:5]
    
    return render(request, 'main/home.html', {
        'top_currencies': top_currencies
    })

@login_required
def add_account(request):
    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
            account.save()
            messages.success(request, 'Счет успешно создан!')
            return redirect('dashboard')
    else:
        form = AccountForm()
    
    return render(request, 'main/add_account.html', {'form': form})

@staff_member_required
def update_rates(request):
    try:
        call_command('fetch_rates')
        messages.success(request, 'Курсы успешно обновлены!')
    except Exception as e:
        messages.error(request, f'Ошибка обновления: {e}')
    return redirect('home')

@login_required
def account_detail(request, pk):
    account = get_object_or_404(Account, pk=pk, user=request.user)
    transactions = account.transactions.all().order_by('-date')
    current_value_rub = account.balance * account.currency.current_rate
    
    invested_rub = Decimal('0.00')
    for t in transactions:
        if t.transaction_type == 'BUY':
            invested_rub += (t.amount * t.rate_at_moment)
        elif t.transaction_type == 'SELL':
            invested_rub -= (t.amount * t.rate_at_moment)
            
    profit_rub = current_value_rub - invested_rub

    context = {
        'account': account,
        'transactions': transactions,
        'current_value_rub': current_value_rub,
        'profit_rub': profit_rub,
    }
    return render(request, 'main/account_detail.html', context)

@login_required
def get_cbr_rate(request):
    date_str = request.GET.get('date')
    cbr_id = request.GET.get('cbr_id')
    
    if not date_str or not cbr_id:
        return JsonResponse({'error': 'Не передана дата или ID валюты'}, status=400)
        
    try:
        from datetime import datetime
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        rate = get_rate_on_date(cbr_id, target_date)
        
        if rate:
            return JsonResponse({'rate': str(rate)})
        else:
            return JsonResponse({'error': 'Курс не найден'}, status=404)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def add_transaction(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.date = form.cleaned_data['date'] 
            
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
        initial_account = request.GET.get('account')
        form = TransactionForm(user=request.user, initial={'account': initial_account})
    
    # ВОТ ЭТА СТРОКА ДОЛЖНА БЫТЬ ИМЕННО ТАКОЙ:
    currencies = {
        c.code: {
            'cbr_id': c.cbr_id, 
            'name': c.name
        } for c in Currency.objects.all()
    }
    
    return render(request, 'main/add_transaction.html', {
        'form': form, 
        'currencies': currencies
    })