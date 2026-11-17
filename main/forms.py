from django import forms
from .models import Transaction, Account
from datetime import date
from main.api_cbr import get_rate_on_date

class TransactionForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control bg-dark text-white border-success'}),
        initial=date.today,
        label="Дата операции"
    )

    class Meta:
        model = Transaction
        fields = ['account', 'transaction_type', 'amount', 'rate_at_moment']
        widgets = {
            'account': forms.Select(attrs={'class': 'form-control bg-dark text-white border-success'}),
            'transaction_type': forms.Select(attrs={'class': 'form-control bg-dark text-white border-success'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control bg-dark text-white border-success', 'step': '0.01'}),
            'rate_at_moment': forms.NumberInput(attrs={'class': 'form-control bg-dark text-white border-success', 'step': '0.0001'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(TransactionForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['account'].queryset = Account.objects.filter(user=user)
            
        self.fields['rate_at_moment'].required = False
        self.fields['rate_at_moment'].help_text = "Оставьте пустым, чтобы взять курс ЦБ на выбранную дату"
        self.fields['transaction_type'].empty_label = None

    def clean(self):
        cleaned_data = super().clean()
        rate = cleaned_data.get('rate_at_moment')
        account = cleaned_data.get('account')
        op_date = cleaned_data.get('date')
        transaction_type = cleaned_data.get('transaction_type')
        amount = cleaned_data.get('amount')

        if transaction_type == 'SELL' and account and amount:
            if amount > account.balance:
                raise forms.ValidationError(
                    f"Недостаточно средств. На счете только {account.balance} {account.currency.code}."
                )
            
        if not rate and account and op_date:
            cbr_id = account.currency.cbr_id
            if not cbr_id:
                raise forms.ValidationError("Для этой валюты нет данных в ЦБ. Введите курс вручную.")
            
            from main.api_cbr import get_rate_on_date
            fetched_rate = get_rate_on_date(cbr_id, op_date)
            if fetched_rate:
                cleaned_data['rate_at_moment'] = fetched_rate
            else:
                raise forms.ValidationError("Не удалось получить курс ЦБ. Введите вручную.")
                
        return cleaned_data

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['name', 'currency']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Например: Долларовый депозит'}),
            'currency': forms.Select(),
        }
        labels = {
            'name': 'Название счета',
            'currency': 'Валюта',
        }