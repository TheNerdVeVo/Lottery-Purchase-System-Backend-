from django.contrib.auth.models import User             #imports built-in user model for user accounts
from django.contrib.auth import authenticate, login, logout  #authenticate -> password, login -> session start, logout -> session end
from rest_framework.decorators import api_view, permission_classes  #decorators that mark functs as api endpoints
from rest_framework.permissions import IsAuthenticated, AllowAny   #IsAuth -> only logged in users can use ep, AllowAny -> anyone can use ep
from rest_framework.response import Response  
from rest_framework import status   #returns full HTTP status code 
from .models import LotteryTicket, Order, ElectronicTicket, LotteryDraw, CustomerProfile 
from .forms import CustomerRegistrationForm
from .random_gen import generate_random_numbers

#==================================================
# Register View
# Accepts POST requests with user registration data
# Returns success message or form error
#==================================================
@api_view(['POST'])
@permission_classes([AllowAny])                     #anyone can create account

def register(request):
    form = CustomerRegistrationForm(request.data)
    if form.is_valid():                             #check if all input data is correct
        form.save()                                 #save user and profile to db
        return Response({'message': 'Account created successfully!'}, status=status.HTTP_201_CREATED)
    return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

#==================================================
# Login View
# Accepts POST requests with username and password
# Returns success message or error
#==================================================
@api_view(['POST'])
@permission_classes([AllowAny])

def login_view(request):
    username = request.data.get('username')         #retrieve username
    password = request.data.get('password')         #retrieve password
    user = authenticate(request, username=username, password=password)

    if user:
        login(request, user)                        #if authentication was successful, start session
        return Response({'message': 'Login successful!'})
    return Response({'error': 'Incorrect username and/or password!'}, status=status.HTTP_401_UNAUTHORIZED)

#==================================================
# Logout View
# Accepts POST requests from authenticated user
# Ends user session
#==================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])              #only allow logged in users

def logout_view(request):
    logout(request)                                 #end user session
    return Response({'message': 'Logged out successfully!'})

#==================================================
# Get_Lottery_Games View
# Returns a list of all available lottery games
# including name, price, and prize amount
#==================================================
@api_view(['GET'])
@permission_classes([AllowAny])                     #anyone can browse tickets

def get_lottery_games(request):
    games = LotteryTicket.objects.all()
    data = [
        {
        'game_type': game.game_type,
        'name': game.get_game_type_display(),
        'ticket_price': str(game.ticket_price),
        'prize_amount': str(game.prize_amount),
        }
        for game in games
    ]
    return Response(data)

#==================================================
# Purchase Tickets View
# Accepts a POST request with payment method and
# list of tickets to purchase (max -> 10)
#==================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])

def purchase_tickets(request):
    payment_method = request.data.get("payment_method")
    tickets = request.data.get('tickets', [])

    if not payment_method:                          #validate payment method
        return Response({'error': 'Please input payment method'}, status=status.HTTP_400_BAD_REQUEST)
    
    if not tickets or len(tickets)>10:
        return Response({'error': 'Maximum 10 tickets allowed per purchase'}, status=status.HTTP_400_BAD_REQUEST)
    
    order = Order.objects.create(user=request.user, payment_method=payment_method)  #create order

    for ticket in tickets:
        lottery_type = ticket.get('lottery_type')   #get type of lottery per ticket
        numbers = ticket.get('numbers') or generate_random_numbers(lottery_type)
        ElectronicTicket.objects.create(transaction=order, lottery_type=lottery_type, numbers=numbers)
    
    return Response({'message': 'Purchase successful!', 'confirmation_number': order.confirmation_number},
                    status=status.HTTP_201_CREATED)

#==================================================
# User Tickets View
# Returns all tickets purchased by logged in user
# along with their order confirmation number
#==================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])

def user_tickets(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('tickets')
    data = []

    for order in orders:
        for ticket in order.tickets.all():
            data.append({
                'ticket_number': ticket.ticket_number,
                'lottery_type': ticket.get_lottery_type_display(),
                'numbers': ticket.numbers,
                'winner': ticket.winner,
                'prize': str(ticket.calculated_prize),
                'confirmation_number': order.confirmation_number,
                'purchased_at': order.created_at,
            })
    return Response(data)

#==================================================
# Winning Numbers History View
# Returns all completed and published draws
# along with their winning numbers
#==================================================
@api_view(['GET'])
@permission_classes([AllowAny])

def winning_numbers(request):
    draws = LotteryDraw.objects.filter(draw_status=LotteryDraw.DrawStatus.PUBLISHED)
    data=[
        {
            'draw_id': draw.draw_id,
            'game': draw.game.get_game_type_display(),
            'draw_date': draw.draw_date,
            'winning_numbers': draw.winning_numbers,
            'prize_amount': str(draw.prize_amount),
        }
        for draw in draws
    ]

    return Response(data)
