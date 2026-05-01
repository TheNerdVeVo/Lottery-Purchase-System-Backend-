from django.urls import path
from LPS import views

urlpatterns = [
    path('api/register/', views.register, name='register'),
    path('api/login/', views.login_view, name='login'),
    path('api/logout/', views.logout_view, name='logout'),
    path('api/profile/', views.profile_view, name='profile'),

    path('api/lottery-games/', views.get_lottery_games, name='lottery-games'),
    path('api/lottery-games/<str:game_type>/', views.get_lottery_game, name='lottery-game'),

    path('api/purchase-tickets/', views.purchase_tickets, name='purchase-tickets'),
    path('api/user-tickets/', views.user_tickets, name='user-tickets'),
    path('api/user-orders/', views.user_orders, name='user-orders'),
    path('api/orders/<int:order_id>/', views.order_detail, name='order-detail'),

    path('api/winning-numbers/', views.winning_numbers, name='winning-numbers'),

    path('api/admin-view/', views.admin_view, name='admin-view'),
    path('api/admin-add-ticket/', views.admin_add_ticket, name='admin-add-ticket'),
    path('api/admin-remove-ticket/', views.admin_remove_ticket, name='admin-remove-ticket'),
    path('api/admin-update-ticket/', views.admin_update_ticket, name='admin-update-ticket'),
    path('api/admin-run-draw/', views.admin_run_draw, name='admin-run-draw'),
]
