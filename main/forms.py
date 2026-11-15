from django import forms
from .models import Transaction, Account

class TransactionForm(forms.ModelForm):
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
            self.fields['rate_at_moment'].help_text = "Оставьте пустым, чтобы использовать текущий курс ЦБ"

    def clean(self):
        cleaned_data = super().clean()
        rate = cleaned_data.get('rate_at_moment')
        account = cleaned_data.get('account')
        
        if not rate and account:
            cleaned_data['rate_at_moment'] = account.currency.current_rate
            
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