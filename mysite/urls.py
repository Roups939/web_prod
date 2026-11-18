from django.contrib import admin
from django.urls import path, include
from main import views
from main.views import RegisterView


urlpatterns = [
    path('admin/', admin.site.urls), 
    path('', views.home, name='home'),#главная
    path('dashboard/', views.dashboard, name='dashboard'),#кабинет
    path('add/', views.add_transaction, name='add_transaction'),
    path('add-account/', views.add_account, name='add_account'),
    path('register/', RegisterView.as_view(), name='register'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('update-rates/', views.update_rates, name='update_rates'),
    path('account/<int:pk>/', views.account_detail, name='account_detail'),
    path('api/get-rate/', views.get_cbr_rate, name='get_cbr_rate'),
    path('transaction/<int:pk>/delete/', views.delete_transaction, name='delete_transaction'),
    path('account/<int:pk>/delete/', views.delete_account, name='delete_account'),
    path('transaction/<int:pk>/edit/', views.edit_transaction, name='edit_transaction'),
    path('chart/<str:code>/', views.currency_chart, name='currency_chart'),
]