from django.contrib.auth.models import User             #imports built-in user model for user accounts
from django.contrib.auth import authenticate, login, logout  #authenticate -> password, login -> session start, logout -> session end
from django.utils.timezone import now # Import the current date and time
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
    
    if not tickets or len(tickets)>10:              #validate ticket/ ticket count
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

#==================================================
# Admin View // Total Tickets + Revenue
# Accepts GET request from verified admin
# Returns total tickets sold and total revenue
#==================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])

def admin_view(request):
    if not request.user.is_staff:                   #check if the logged in user has admin permissions
        return Response({'error': 'Admin access only.'}, status=status.HTTP_403_FORBIDDEN)

    total_tickets_sold= ElectronicTicket.objects.count()   #counts total tickets sold    
    total_revenue=0

    for game in LotteryTicket.objects.all():                #loop to determine count per ticket type and total price per group of tickets
        count= ElectronicTicket.objects.filter(lottery_type=game.game_type).count()
        total_revenue+= count*game.ticket_price
    
    # Count active ticket types, available games
    active_ticket_types = LotteryTicket.objects.count()
    
    # Return system status report
    return Response({
        'report_date': now().date(),
        'total_tickets_sold': total_tickets_sold,
        'total_revenue': str(total_revenue),
        'active_ticket_types': active_ticket_types})

#==================================================
# Admin View // Add ticket type
# Accepts POST request from verified admin
# and details of ticket to be added
#==================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])

def admin_add_ticket(request):
    if not request.user.is_staff:                   
        return Response({'error': 'Admin access only.'}, status=status.HTTP_403_FORBIDDEN)
    
    game_type = request.data.get("game_type")
    ticket_price = request.data.get("ticket_price")
    prize_amount = request.data.get("prize_amount")

    LotteryTicket.objects.create(game_type=game_type, ticket_price=ticket_price, prize_amount=prize_amount)

    return Response({'message': 'Ticket added successfully!'}, status=status.HTTP_201_CREATED)

#==================================================
# Admin View // Remove ticket type
# Accepts POST request from verified admin
# and details of ticket to be removed
#==================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])

def admin_remove_ticket(request):
    if not request.user.is_staff:                   
        return Response({'error': 'Admin access only.'}, status=status.HTTP_403_FORBIDDEN)
    
    game_type = request.data.get("game_type")

    LotteryTicket.objects.get(game_type=game_type).delete()

    return Response({'message': 'Ticket removed successfully!'}, status=status.HTTP_200_OK)

#==================================================
# Admin View // Update ticket type
# Accepts POST request from verified admin
# and details of ticket to be updated
#==================================================
@api_view(['PUT'])
@permission_classes([IsAuthenticated])

def admin_update_ticket(request):
    if not request.user.is_staff:                   
        return Response({'error': 'Admin access only.'}, status=status.HTTP_403_FORBIDDEN)
    
    game_type = request.data.get("game_type")
    ticket_price = request.data.get("ticket_price")
    prize_amount = request.data.get("prize_amount")

    LotteryTicket.objects.filter(game_type=game_type).update(ticket_price=ticket_price, prize_amount=prize_amount)

    return Response({'message': 'Ticket updated successfully!'}, status=status.HTTP_200_OK)

#==================================================
# Admin View // Run a draw
# Accepts POST request from verified admin
# Runs draw from determine_winners()
#==================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])

def admin_run_draw(request):
    if not request.user.is_staff:                   
        return Response({'error': 'Admin access only.'}, status=status.HTTP_403_FORBIDDEN)
    
    draw_id = request.data.get("draw_id")
    draw = LotteryDraw.objects.get(draw_id=draw_id)

    draw.determine_winners()                          #call determine_winners from models.py

    return Response({'message': 'Draw completed successfully!'}, status=status.HTTP_200_OK)

#==================================================
# Admin View // Publish a draw
# Accepts POST request from verified admin
# Returns draw along with numbers and winners
#==================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])

def admin_publish_draw(request):
    if not request.user.is_staff:                   
        return Response({'error': 'Admin access only.'}, status=status.HTTP_403_FORBIDDEN)
    
    draw_id = request.data.get("draw_id")
    draw = LotteryDraw.objects.get(draw_id=draw_id)

    draw.publish_results()                          #call publish_results() from models.py

    return Response({'message': 'Draw results published!'}, status=status.HTTP_200_OK)

#==================================================
# Profile View
# Accepts GET request from logged in user
# Returns profile page
#==================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])

def profile_page_view(request):

    user = request.user

    #Get profile without crashing
    profile = CustomerProfile.objects.filter(user=user).first()

    return Response({
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'home_address': profile.home_address if profile else "",
        'phone_number': profile.phone_number if profile else "",
    })
