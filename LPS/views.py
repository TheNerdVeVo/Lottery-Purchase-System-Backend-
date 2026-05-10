from decimal import Decimal
from datetime import date, timedelta, datetime

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.db.models import Sum, Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
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


def _get_or_create_profile(user):
    prof, _ = CustomerProfile.objects.get_or_create(
        user=user,
        defaults={'home_address': '', 'phone_number': ''},
    )
    return prof


def _reset_spending_window_if_stale(profile):
    """Spending window resets every 7 days from window_start."""
    today = date.today()
    if profile.spending_window_start is None:
        profile.spending_window_start = today
        profile.spending_window_total = Decimal('0.00')
        profile.save()
        return
    if (today - profile.spending_window_start).days >= 7:
        profile.spending_window_start = today
        profile.spending_window_total = Decimal('0.00')
        profile.save()


# -------------------- auth --------------------

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    form = CustomerRegistrationForm(request.data)
    if form.is_valid():
        user = form.save()
        token, _ = Token.objects.get_or_create(user=user)
        # Phase 3: ensure profile exists with default wallet/limits
        _get_or_create_profile(user)
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

@api_view(['GET', 'PATCH', 'PUT', 'POST'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    u = request.user
    prof = _get_or_create_profile(u)
    _reset_spending_window_if_stale(prof)

    if request.method in ('PATCH', 'PUT', 'POST'):
        data = request.data or {}
        # name (split full name on first space if provided as full_name)
        if 'full_name' in data:
            full = (data.get('full_name') or '').strip()
            first, _, last = full.partition(' ')
            u.first_name = first
            u.last_name = last or first
        else:
            if 'first_name' in data:
                u.first_name = (data.get('first_name') or '').strip()
            if 'last_name' in data:
                u.last_name = (data.get('last_name') or '').strip()

        # email — must be unique
        new_email = (data.get('email') or '').strip().lower()
        if new_email and new_email != u.email.lower():
            if User.objects.filter(email__iexact=new_email).exclude(pk=u.pk).exists():
                return Response({'error': 'That email is already in use by another account.'},
                                status=status.HTTP_400_BAD_REQUEST)
            u.email = new_email
            # username == email convention for non-admin accounts
            if not u.is_staff:
                u.username = new_email

        u.save()

        if 'home_address' in data:
            prof.home_address = (data.get('home_address') or '').strip()
        if 'phone_number' in data:
            prof.phone_number = (data.get('phone_number') or '').strip()
        prof.save()

    return Response({
        'username': u.username,
        'first_name': u.first_name,
        'last_name': u.last_name,
        'email': u.email,
        'home_address': prof.home_address,
        'phone_number': prof.phone_number,
        'is_admin': u.is_staff,
        'wallet_balance': str(prof.wallet_balance),
        'weekly_spending_limit': str(prof.weekly_spending_limit),
        'spending_window_start': prof.spending_window_start.isoformat() if prof.spending_window_start else None,
        'spending_window_total': str(prof.spending_window_total),
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

    profile = _get_or_create_profile(request.user)
    _reset_spending_window_if_stale(profile)

    # compute total cost
    total_cost = Decimal('0.00')
    needed_types = set()
    for t in tickets:
        gt = t.get('lottery_type')
        try:
            game = LotteryTicket.objects.get(game_type=gt)
        except LotteryTicket.DoesNotExist:
            return Response({'error': f'Unknown game type {gt}'},
                            status=status.HTTP_400_BAD_REQUEST)
        total_cost += game.ticket_price
        needed_types.add(gt)

    # === Phase 3: check spending limit ===
    if profile.weekly_spending_limit > 0:
        projected = profile.spending_window_total + total_cost
        if projected > profile.weekly_spending_limit:
            remaining = profile.weekly_spending_limit - profile.spending_window_total
            return Response({
                'error': (f'Purchase blocked: would exceed your weekly spending limit of '
                          f'${profile.weekly_spending_limit}. You have ${remaining} left this week.'),
                'limit': str(profile.weekly_spending_limit),
                'spent_this_week': str(profile.spending_window_total),
                'attempted': str(total_cost),
            }, status=status.HTTP_400_BAD_REQUEST)

    # === Phase 3: if payment method is wallet, check + deduct balance ===
    if payment_method == 'WL':
        if profile.wallet_balance < total_cost:
            return Response({
                'error': (f'Insufficient wallet balance. Have ${profile.wallet_balance}, '
                          f'need ${total_cost}. Please top up.'),
                'balance': str(profile.wallet_balance),
                'needed': str(total_cost),
            }, status=status.HTTP_400_BAD_REQUEST)
        profile.wallet_balance -= total_cost
        # Wallet purchases use BK in DB since WL isn't a stored choice
        payment_method = 'BK'

    # ensure a scheduled draw exists
    for gt in needed_types:
        game = LotteryTicket.objects.get(game_type=gt)
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

    # === Phase 3: update spending window + save profile ===
    profile.spending_window_total += total_cost
    profile.save()

    # === Phase 3: create a purchase notification ===
    Notification.objects.create(
        recipient=request.user,
        order=order,
        recipient_email=request.user.email,
        message=f'Order {order.confirmation_number} confirmed: {len(tickets)} ticket(s) for ${total_cost}.',
        notification_type=Notification.NotificationType.PURCHASE,
    )

    return Response(
        {'message': 'Purchase successful!',
         'confirmation_number': order.confirmation_number,
         'order_id': order.id,
         'total_cost': str(total_cost),
         'wallet_balance': str(profile.wallet_balance)},
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
            'claimed': o.claimed,
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
        'claimed': order.claimed,
        'claimed_at': order.claimed_at.isoformat() if order.claimed_at else None,
        'tickets': [_serialize_ticket(t, order) for t in order.tickets.all()],
    })


# === Phase 3: persistent claim ===
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def claim_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    # only winners can claim
    has_winner = any(t.winner for t in order.tickets.all())
    if not has_winner:
        return Response({'error': 'No winning tickets in this order.'},
                        status=status.HTTP_400_BAD_REQUEST)
    if order.claimed:
        return Response({'error': 'Already claimed.'},
                        status=status.HTTP_400_BAD_REQUEST)

    total_winnings = sum((t.calculated_prize for t in order.tickets.all()), Decimal('0.00'))

    order.claimed = True
    order.claimed_at = timezone.now()
    order.save()

    # === Phase 3: credit winnings to wallet ===
    profile = _get_or_create_profile(request.user)
    profile.wallet_balance += total_winnings
    profile.save()

    Notification.objects.create(
        recipient=request.user,
        order=order,
        recipient_email=request.user.email,
        message=f'Prize claimed for order {order.confirmation_number}: ${total_winnings} credited to wallet.',
        notification_type=Notification.NotificationType.WINNER,
    )

    return Response({
        'message': 'Prize claimed and credited to wallet.',
        'amount_credited': str(total_winnings),
        'new_balance': str(profile.wallet_balance),
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


# -------------------- Phase 3: notifications --------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_list(request):
    qs = Notification.objects.filter(recipient=request.user).order_by('-date_sent')
    only_unread = request.query_params.get('unread') == '1'
    if only_unread:
        qs = qs.filter(is_read=False)
    return Response([
        {
            'id': str(n.notification_id),
            'message': n.message,
            'type': n.notification_type,
            'is_read': n.is_read,
            'date_sent': n.date_sent.isoformat(),
            'order_id': n.order.id if n.order else None,
        }
        for n in qs
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_unread_count(request):
    n = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return Response({'unread': n})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notifications_mark_read(request, notification_id):
    try:
        n = Notification.objects.get(notification_id=notification_id, recipient=request.user)
    except Notification.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    n.is_read = True
    n.save()
    return Response({'ok': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notifications_mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return Response({'ok': True})


# -------------------- Phase 3: wallet --------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wallet_balance(request):
    profile = _get_or_create_profile(request.user)
    return Response({'balance': str(profile.wallet_balance)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def wallet_topup(request):
    try:
        amount = Decimal(str(request.data.get('amount', '0')))
    except Exception:
        return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
    if amount <= 0:
        return Response({'error': 'Amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)
    if amount > Decimal('1000.00'):
        return Response({'error': 'Maximum top-up is $1000 per transaction'},
                        status=status.HTTP_400_BAD_REQUEST)

    profile = _get_or_create_profile(request.user)
    profile.wallet_balance += amount
    profile.save()

    Notification.objects.create(
        recipient=request.user,
        recipient_email=request.user.email,
        message=f'Wallet topped up by ${amount}. New balance: ${profile.wallet_balance}.',
        notification_type=Notification.NotificationType.GENERAL,
    )

    return Response({
        'message': f'Topped up ${amount}',
        'balance': str(profile.wallet_balance),
    })


# -------------------- Phase 3: spending limits --------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_spending_limit(request):
    try:
        limit = Decimal(str(request.data.get('limit', '0')))
    except Exception:
        return Response({'error': 'Invalid limit'}, status=status.HTTP_400_BAD_REQUEST)
    if limit < 0:
        return Response({'error': 'Limit cannot be negative'},
                        status=status.HTTP_400_BAD_REQUEST)

    profile = _get_or_create_profile(request.user)
    profile.weekly_spending_limit = limit
    if profile.spending_window_start is None:
        profile.spending_window_start = date.today()
    profile.save()
    return Response({
        'message': f'Weekly spending limit set to ${limit}' + (' (no limit)' if limit == 0 else ''),
        'limit': str(limit),
    })


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


# === Phase 3: detailed analytics ===
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_analytics(request):
    if not _admin_required(request.user):
        return Response({'error': 'Admin access only.'}, status=status.HTTP_403_FORBIDDEN)

    # tickets sold per game
    by_game = []
    for game in LotteryTicket.objects.all():
        tickets_for_game = ElectronicTicket.objects.filter(lottery_type=game.game_type)
        count = tickets_for_game.count()
        winners = tickets_for_game.filter(winner=True).count()
        revenue = count * game.ticket_price
        win_rate = (winners / count * 100) if count else 0.0
        by_game.append({
            'game_type': game.game_type,
            'name': game.get_game_type_display(),
            'tickets_sold': count,
            'winners': winners,
            'revenue': str(revenue),
            'win_rate_pct': round(win_rate, 2),
        })

    # revenue per day (last 14 days)
    today = date.today()
    daily = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        orders_today = Order.objects.filter(created_at__date=d).prefetch_related('tickets')
        rev = Decimal('0.00')
        ticket_count = 0
        for o in orders_today:
            for t in o.tickets.all():
                try:
                    g = LotteryTicket.objects.get(game_type=t.lottery_type)
                    rev += g.ticket_price
                except LotteryTicket.DoesNotExist:
                    pass
                ticket_count += 1
        daily.append({
            'date': d.isoformat(),
            'revenue': str(rev),
            'tickets': ticket_count,
        })

    # claims summary
    total_winning_orders = sum(
        1 for o in Order.objects.all() if any(t.winner for t in o.tickets.all())
    )
    claimed = Order.objects.filter(claimed=True).count()

    return Response({
        'by_game': by_game,
        'daily': daily,
        'claims': {
            'winning_orders': total_winning_orders,
            'claimed': claimed,
            'unclaimed': total_winning_orders - claimed,
        },
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
    """
    Run a draw for a given game_type. Phase 3: admin can pass winning_numbers
    explicitly to force a specific outcome (for demo).
    """
    if not _admin_required(request.user):
        return Response({'error': 'Admin access only.'}, status=status.HTTP_403_FORBIDDEN)

    game_type = request.data.get('game_type')
    game = get_object_or_404(LotteryTicket, game_type=game_type)
    forced = (request.data.get('winning_numbers') or '').strip()
    winning = forced if forced else generate_random_numbers(game_type)

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

    # Phase 3: do scoring inline with proper decimal quantization
    # (the model's calculate_prize returns 4-decimal values which fail field validation)
    winning_set = set(int(n.strip()) for n in winning.split(',') if n.strip().lstrip('-').isdigit())
    multipliers = {5: Decimal('1.00'), 4: Decimal('0.20'),
                   3: Decimal('0.05'), 2: Decimal('0.01')}
    cents = Decimal('0.01')

    for ticket in draw.tickets.all():
        ticket_set = set(int(n.strip()) for n in ticket.numbers.split(',')
                         if n.strip().lstrip('-').isdigit())
        matches = len(winning_set & ticket_set)
        mult = multipliers.get(matches, Decimal('0.00'))
        prize = (draw.prize_amount * mult).quantize(cents)
        ticket.winner = prize > 0
        ticket.calculated_prize = prize
        # bypass the model's full_clean (it triggers the auto-assign-draw logic
        # which we don't need at scoring time)
        ElectronicTicket.objects.filter(pk=ticket.pk).update(
            winner=ticket.winner, calculated_prize=ticket.calculated_prize,
        )

    draw.draw_status = LotteryDraw.DrawStatus.COMPLETED
    draw.save()

    # publish + create notifications
    draw.draw_status = LotteryDraw.DrawStatus.PUBLISHED
    draw.save()
    for ticket in draw.tickets.all():
        if ticket.winner:
            msg = f'🏆 Congratulations! Ticket {ticket.ticket_number} won ${ticket.calculated_prize}.'
            nt = Notification.NotificationType.WINNER
        else:
            msg = f'Results published. Ticket {ticket.ticket_number} did not win this draw.'
            nt = Notification.NotificationType.DRAW_RESULT
        Notification.objects.create(
            recipient=ticket.transaction.user,
            order=ticket.transaction,
            draw=draw,
            recipient_email=ticket.transaction.user.email,
            message=msg,
            notification_type=nt,
        )

    return Response({
        'message': 'Draw completed and published.',
        'draw_id': draw.draw_id,
        'winning_numbers': draw.winning_numbers,
        'forced': bool(forced),
    })
