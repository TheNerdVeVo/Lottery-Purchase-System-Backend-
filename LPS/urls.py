from django.urls import path
from LPS import views

#==================================================
# URL Patterns
# Creates URL links for each API view in views.py
#==================================================
urlpatterns = [
    path('api/register/', views.register, name='register'),
    path('api/login/', views.login_view, name='login'),
    path('api/logout/', views.logout_view, name='logout'),
    path('api/lottery-games/', views.get_lottery_games, name='lottery-games'),
    path('api/purchase-tickets/', views.purchase_tickets, name='purchase-tickets'),
    path('api/user-tickets/', views.user_tickets, name='user-tickets'),
    path('api/winning-numbers/', views.winning_numbers, name='winning-numbers'),
]