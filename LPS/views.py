from decimal import Decimal
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import (
    LotteryTicket, Order, ElectronicTicket, LotteryDraw,
    CustomerProfile, Notification,
)
from .forms import CustomerRegistrationForm
from .random_gen import generate_random_numbers


# -------------------- helpers --------------------

def _serialize_game(g):
    return {
        'game_type': g.game_type,
        'name': g.get_game_type_display(),
        'ticket_price': str(g.ticket_price),
        'prize_amount': str(g.prize_amount),
    }


def _serialize_ticket(t, order):
    return {
        'ticket_number': t.ticket_number,
        'lottery_type': t.lottery_type,
        'lottery_name': t.get_lottery_type_display(),
        'numbers': t.numbers,
        'winner': t.winner,
        'prize': str(t.calculated_prize),
        'confirmation_number': order.confirmation_number,
        'purchased_at': order.created_at.isoformat(),
        'order_id': order.id,
    }


# -------------------- auth --------------------

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    form = CustomerRegistrationForm(request.data)
    if form.is_valid():
        user = form.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {'message': 'Account created successfully!', 'token': token.key,
             'username': user.username, 'is_admin': user.is_staff},
            status=status.HTTP_201_CREATED,
        )
    return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(request, username=username, password=password)

    if user:
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'message': 'Login successful!',
            'token': token.key,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'is_admin': user.is_staff,
        })
    return Response({'error': 'Incorrect username and/or password!'},
                    status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    Token.objects.filter(user=request.user).delete()
    return Response({'message': 'Logged out successfully!'})


# -------------------- profile --------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    u = request.user
    try:
        prof = u.customerprofile
        addr, phone = prof.home_address, prof.phone_number
    except CustomerProfile.DoesNotExist:
        addr, phone = '', ''
    return Response({
        'username': u.username,
        'first_name': u.first_name,
        'last_name': u.last_name,
        'email': u.email,
        'home_address': addr,
        'phone_number': phone,
        'is_admin': u.is_staff,
    })


# -------------------- games --------------------

@api_view(['GET'])
@permission_classes([AllowAny])
def get_lottery_games(request):
    return Response([_serialize_game(g) for g in LotteryTicket.objects.all()])


@api_view(['GET'])
@permission_classes([AllowAny])
def get_lottery_game(request, game_type):
    g = get_object_or_404(LotteryTicket, game_type=game_type)
    return Response(_serialize_game(g))


# -------------------- purchase --------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase_tickets(request):
    payment_method = request.data.get('payment_method')
    tickets = request.data.get('tickets', [])

    if not payment_method:
        return Response({'error': 'Please input payment method'},
                        status=status.HTTP_400_BAD_REQUEST)
    if not tickets or len(tickets) > 10:
        return Response({'error': 'Maximum 10 tickets allowed per purchase'},
                        status=status.HTTP_400_BAD_REQUEST)

    # ensure a scheduled draw exists for each ticket type (auto-create one a week out)
    needed_types = {t.get('lottery_type') for t in tickets}
    for gt in needed_types:
        try:
            game = LotteryTicket.objects.get(game_type=gt)
        except LotteryTicket.DoesNotExist:
            return Response({'error': f'Unknown game type {gt}'},
                            status=status.HTTP_400_BAD_REQUEST)
        has_open = LotteryDraw.objects.filter(
            game=game,
            draw_status=LotteryDraw.DrawStatus.SCHEDULED,
            draw_date__gte=date.today(),
        ).exists()
        if not has_open:
            LotteryDraw.objects.create(
                game=game,
                draw_date=date.today() + timedelta(days=7),
                winning_numbers='',
                prize_amount=game.prize_amount,
                draw_status=LotteryDraw.DrawStatus.SCHEDULED,
            )

    order = Order.objects.create(user=request.user, payment_method=payment_method)

    for ticket in tickets:
        lottery_type = ticket.get('lottery_type')
        numbers = ticket.get('numbers') or generate_random_numbers(lottery_type)
        ElectronicTicket.objects.create(
            transaction=order, lottery_type=lottery_type, numbers=numbers,
        )

    return Response(
        {'message': 'Purchase successful!',
         'confirmation_number': order.confirmation_number,
         'order_id': order.id},
        status=status.HTTP_201_CREATED,
    )


# -------------------- user-facing tickets / orders --------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_tickets(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('tickets')
    data = []
    for order in orders:
        for t in order.tickets.all():
            data.append(_serialize_ticket(t, order))
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_orders(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('tickets').order_by('-created_at')
    return Response([
        {
            'order_id': o.id,
            'confirmation_number': o.confirmation_number,
            'payment_method': o.get_payment_method_display(),
            'created_at': o.created_at.isoformat(),
            'ticket_count': o.tickets.count(),
        }
        for o in orders
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return Response({
        'order_id': order.id,
        'confirmation_number': order.confirmation_number,
        'payment_method': order.get_payment_method_display(),
        'created_at': order.created_at.isoformat(),
        'tickets': [_serialize_ticket(t, order) for t in order.tickets.all()],
    })


# -------------------- winning numbers --------------------

@api_view(['GET'])
@permission_classes([AllowAny])
def winning_numbers(request):
    draws = LotteryDraw.objects.filter(
        draw_status=LotteryDraw.DrawStatus.PUBLISHED
    ).order_by('-draw_date')
    return Response([
        {
            'draw_id': d.draw_id,
            'game_type': d.game.game_type,
            'game': d.game.get_game_type_display(),
            'draw_date': d.draw_date.isoformat(),
            'winning_numbers': d.winning_numbers,
            'prize_amount': str(d.prize_amount),
        }
        for d in draws
    ])


# -------------------- admin --------------------

def _admin_required(user):
    return user.is_staff


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_view(request):
    if not _admin_required(request.user):
        return Response({'error': 'Admin access only.'}, status=status.HTTP_403_FORBIDDEN)

    total_tickets_sold = ElectronicTicket.objects.count()
    total_revenue = Decimal('0.00')
    for game in LotteryTicket.objects.all():
        count = ElectronicTicket.objects.filter(lottery_type=game.game_type).count()
        total_revenue += count * game.ticket_price

    return Response({
        'total_tickets_sold': total_tickets_sold,
        'total_revenue': str(total_revenue),
        'total_orders': Order.objects.count(),
        'total_users': User.objects.filter(is_staff=False).count(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_add_ticket(request):
    if not _admin_required(request.user):
        return Response({'error': 'Admin access only.'}, status=status.HTTP_403_FORBIDDEN)
    LotteryTicket.objects.create(
        game_type=request.data.get('game_type'),
        ticket_price=request.data.get('ticket_price'),
        prize_amount=request.data.get('prize_amount'),
    )
    return Response({'message': 'Ticket added successfully!'}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_remove_ticket(request):
    if not _admin_required(request.user):
        return Response({'error': 'Admin access only.'}, status=status.HTTP_403_FORBIDDEN)
    LotteryTicket.objects.filter(game_type=request.data.get('game_type')).delete()
    return Response({'message': 'Ticket removed successfully!'})


@api_view(['PUT', 'POST'])
@permission_classes([IsAuthenticated])
def admin_update_ticket(request):
    if not _admin_required(request.user):
        return Response({'error': 'Admin access only.'}, status=status.HTTP_403_FORBIDDEN)
    LotteryTicket.objects.filter(game_type=request.data.get('game_type')).update(
        ticket_price=request.data.get('ticket_price'),
        prize_amount=request.data.get('prize_amount'),
    )
    return Response({'message': 'Ticket updated successfully!'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_run_draw(request):
    """Run a draw for a given game_type: pick winning numbers, score tickets, publish."""
    if not _admin_required(request.user):
        return Response({'error': 'Admin access only.'}, status=status.HTTP_403_FORBIDDEN)

    game_type = request.data.get('game_type')
    game = get_object_or_404(LotteryTicket, game_type=game_type)
    winning = request.data.get('winning_numbers') or generate_random_numbers(game_type)

    draw = LotteryDraw.objects.filter(
        game=game, draw_status=LotteryDraw.DrawStatus.SCHEDULED,
    ).order_by('draw_date').first()
    if not draw:
        draw = LotteryDraw.objects.create(
            game=game, draw_date=date.today(), winning_numbers=winning,
            prize_amount=game.prize_amount,
            draw_status=LotteryDraw.DrawStatus.SCHEDULED,
        )
    else:
        draw.winning_numbers = winning
        draw.save()

    draw.determine_winners()
    draw.publish_results()

    return Response({
        'message': 'Draw completed and published.',
        'draw_id': draw.draw_id,
        'winning_numbers': draw.winning_numbers,
    })
