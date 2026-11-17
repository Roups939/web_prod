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
from django.views.decorators.http import require_POST
import pandas as pd
from datetime import date, timedelta
from .api_cbr import get_rate_on_date
from decimal import Decimal, ROUND_HALF_UP


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
            if transaction.rate_at_moment:
                transaction.rate_at_moment = transaction.rate_at_moment.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP) 
            if not form.cleaned_data.get('rate_at_moment'):
                 pass
            transaction.rate_date = transaction.date
            account = transaction.account
            if request.POST.get('rate_at_moment'):
                transaction.is_manual_rate = True
            else:
                transaction.is_manual_rate = False
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

@login_required
@require_POST
def delete_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, account__user=request.user)
    account = transaction.account
    
    if transaction.transaction_type == 'BUY':
        account.balance -= transaction.amount
    elif transaction.transaction_type == 'SELL':
        account.balance += transaction.amount
    
    account.save()
    
    transaction.delete()
    messages.success(request, 'Транзакция удалена, баланс счета обновлен.')
    
    return redirect('account_detail', pk=account.pk)

@login_required
@require_POST
def delete_account(request, pk):
    account = get_object_or_404(Account, pk=pk, user=request.user)
    account_name = account.name
    
    account.delete()
    messages.success(request, f'Счет "{account_name}" и все его операции были удалены.')
    
    return redirect('dashboard')

@login_required
def edit_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, account__user=request.user)
    account = transaction.account
    
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction, user=request.user)
        if form.is_valid():
            old_amount = transaction.amount
            old_type = transaction.transaction_type
            if old_type == 'BUY':
                account.balance -= old_amount
            elif old_type == 'SELL':
                account.balance += old_amount
            
            updated_transaction = form.save(commit=False)
            updated_transaction.date = form.cleaned_data['date']
            
            if updated_transaction.transaction_type == 'BUY':
                account.balance += updated_transaction.amount
            elif updated_transaction.transaction_type == 'SELL':
                account.balance -= updated_transaction.amount
            
            updated_transaction.save()
            account.save()
            
            messages.success(request, 'Транзакция успешно обновлена!')
            return redirect('account_detail', pk=account.pk)
    else:
        form = TransactionForm(
            instance=transaction, 
            user=request.user, 
            initial={'date': transaction.date}
        )
    
    currencies = {c.code: {'cbr_id': c.cbr_id, 'name': c.name} for c in Currency.objects.all()}
    
    return render(request, 'main/add_transaction.html', {
        'form': form, 
        'currencies': currencies,
        'is_edit': True
    })

@login_required
def currency_chart(request, code):
    currency = get_object_or_404(Currency, code=code)
    
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    date_list = pd.date_range(start=start_date, end=end_date).date
    
    data = []
    for d in date_list:
        rate = get_rate_on_date(currency.cbr_id, d)
        if rate:
            data.append({'date': d.strftime('%Y-%m-%d'), 'rate': float(rate)})
    
    df = pd.DataFrame(data)
    
    chart_data = df.to_dict(orient='records') if not df.empty else []
    
    return render(request, 'main/chart.html', {
        'currency': currency,
        'chart_data': chart_data
    })