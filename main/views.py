from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse_lazy
from django.views import generic
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, timedelta

import pandas as pd

from .models import Account, Transaction, Currency
from .forms import TransactionForm, AccountForm
from .api_cbr import get_rate_on_date
from django.core.management import call_command


class RegisterView(generic.CreateView):
    form_class = UserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')


def home(request):# берёт из базы 5 валют с самым высоким кусом и возвращает html страницу со списком top_currencies
    top_currencies = Currency.objects.order_by('-current_rate')[:5]
    return render(request, 'main/home.html', {'top_currencies': top_currencies})


@login_required
def dashboard(request):#берет из базы все счета текущего пользователя, проходит по каждому счету циклом
    accounts = Account.objects.filter(user=request.user).select_related('currency')
    
    total_balance_rub = Decimal('0.00')
    total_profit_rub = Decimal('0.00')

    for account in accounts:
        current_value_rub = account.balance * account.currency.current_rate#текущая стоимость в рублях
        transactions = account.transactions.all()#вложенные средства
        invested_rub = Decimal('0.00')
        for t in transactions:
            if t.transaction_type == 'BUY':
                invested_rub += (t.amount * t.rate_at_moment)#cчитает текущую стоимость счета в рублях: баланс * текущий_курс_валюты
            elif t.transaction_type == 'SELL':
                invested_rub -= (t.amount * t.rate_at_moment)#cчитает вложенные средства, суммирует все покупки и вычитает продажи.
        
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
def add_account(request):#создание нового кошелька
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


@login_required
def account_detail(request, pk):#показ детали конкретного счёта
    account = get_object_or_404(Account, pk=pk, user=request.user)#счет только текущего пользователя
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
def add_transaction(request):#операция покапки/продажи
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.date = form.cleaned_data['date']
            
            if transaction.rate_at_moment:
                transaction.rate_at_moment = transaction.rate_at_moment.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
            
            transaction.is_manual_rate = bool(request.POST.get('rate_at_moment'))#определение, ручной ли курс
            transaction.rate_date = transaction.date
            
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
    
    currencies = {c.code: {'cbr_id': c.cbr_id, 'name': c.name} for c in Currency.objects.all()}
    return render(request, 'main/add_transaction.html', {'form': form, 'currencies': currencies})


@login_required
def edit_transaction(request, pk):#редактирование существующей транзакции
    transaction = get_object_or_404(Transaction, pk=pk, account__user=request.user)
    account = transaction.account
    
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction, user=request.user)
        if form.is_valid():
            if transaction.transaction_type == 'BUY':
                account.balance -= transaction.amount
            elif transaction.transaction_type == 'SELL':
                account.balance += transaction.amount
            
            updated_transaction = form.save(commit=False)
            updated_transaction.date = form.cleaned_data['date']
            updated_transaction.is_manual_rate = bool(request.POST.get('rate_at_moment'))
            
            if updated_transaction.transaction_type == 'BUY':
                account.balance += updated_transaction.amount
            elif updated_transaction.transaction_type == 'SELL':
                account.balance -= updated_transaction.amount
            
            updated_transaction.save()
            account.save()
            messages.success(request, 'Транзакция успешно обновлена!')
            return redirect('account_detail', pk=account.pk)
    else:
        form = TransactionForm(instance=transaction, user=request.user, initial={'date': transaction.date})
    
    currencies = {c.code: {'cbr_id': c.cbr_id, 'name': c.name} for c in Currency.objects.all()}
    return render(request, 'main/add_transaction.html', {'form': form, 'currencies': currencies, 'is_edit': True})


@login_required
@require_POST
def delete_transaction(request, pk):#удаление операции
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
def delete_account(request, pk):#удаление счёта
    account = get_object_or_404(Account, pk=pk, user=request.user)
    account.delete()
    return redirect('dashboard')


@staff_member_required
def update_rates(request):#management-команда fetch_rates из админ панели
    try:
        call_command('fetch_rates')
        messages.success(request, 'Курсы успешно обновлены!')
    except Exception as e:
        messages.error(request, f'Ошибка обновления: {e}')
    return redirect('home')


@login_required
def get_cbr_rate(request):#AJAX-эндпоинт 
    date_str = request.GET.get('date')
    cbr_id = request.GET.get('cbr_id')
    
    if not date_str or not cbr_id:
        return JsonResponse({'error': 'Не передана дата или ID валюты'}, status=400)
        
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        rate = get_rate_on_date(cbr_id, target_date)
        
        if rate:
            return JsonResponse({'rate': str(rate)})
        return JsonResponse({'error': 'Курс не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def currency_chart(request, code):#генерация данных для графика
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