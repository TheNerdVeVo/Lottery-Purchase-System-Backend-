import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date

# Generate a short unique confirmation number for an order
def generate_confirmation_number():
    return str(uuid.uuid4()).replace("-","")[:12].upper()

# Generate a unique ticket id
def generate_ticket_number():
    return "T-" + str(uuid.uuid4()).replace("-", "")[:10].upper()

#==============================================================
# Lottery Model
# Stores available lottery, pricing, and prize amounts
# Such as Powerball, Mega Millions, Lotto Texas, Texas Two Step
#==============================================================
class LotteryTicket(models.Model):

    # Different lottery game types
    class GameType(models.TextChoices):
        POWERBALL = "PB", "Powerball"
        MEGA_MILLIONS = "MM", "Mega Millions"
        LOTTO_TEXAS = "LT", "Lotto Texas"
        TEXAS_TWO_STEP = "TS", "Texas Two Step"

    # Type of lottery (must be unique so only one entry per game)
    game_type = models.CharField(max_length = 2, choices = GameType.choices, unique = True)

    # Cost of a single ticket
    ticket_price = models.DecimalField(max_digits = 8, decimal_places = 2)

    # Maximum prize amount for the lottery
    prize_amount = models.DecimalField(max_digits = 12, decimal_places = 2)

    # String representation
    def __str__(self):
        return f"{self.get_game_type_display()} - ${self.ticket_price} - Prize ${self.prize_amount}"

#=======================================
# Customer Profile Model
# Extends Django's built-in User model
# Stores additional customer information
#========================================
class CustomerProfile(models.Model):

    # One to one relationship with Django User
    user = models.OneToOneField(User, on_delete = models.CASCADE)
    
    # Customer's home address
    home_address = models.CharField(max_length = 255)

    # Customer's phone number
    phone_number = models.CharField(max_length = 20)

    # Display full name of the user
    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

#===============================================
# Order Model
# Represents a purchase made by a customer
#===============================================
class Order(models.Model):

    # Payment methods
    class PaymentMethod(models.TextChoices):
        PAYPAL = "PP", "PayPal"
        VENMO = "VN", "Venmo"
        BANK = "BK", "Linked Bank Account"

    # Customer who placed the order
    user = models.ForeignKey(User, on_delete = models.CASCADE)

    # Payment method used
    payment_method = models.CharField(max_length = 2, choices = PaymentMethod.choices)

    # Unique confirmation number 
    confirmation_number = models.CharField(max_length = 20, unique = True, default = generate_confirmation_number, editable = False)

    #Timestamp when order is created
    created_at = models.DateTimeField(auto_now_add = True)

    # Limit tickets per transaction to 10
    def clean(self):
        if self.pk and self.tickets.count() > 10:
            raise ValidationError("A maximum of 10 tickets is allowed per transaction.")
    
    # String representation
    def __str__(self):
        return f"{self.confirmation_number} - {self.user.username} - {self.get_payment_method_display()}"

#=================================================
# ElectronicTicket Model, actual purchased ticket
#=================================================
class ElectronicTicket(models.Model):

    # Link ticket to an order
    transaction = models.ForeignKey(Order, on_delete = models.CASCADE, related_name = "tickets") # allows transaction.tickets access

    # Unique ticket number
    ticket_number = models.CharField(max_length = 20, unique = True, default = generate_ticket_number, editable = False)

    # Type of lottery the ticket belongs to
    lottery_type = models.CharField(max_length = 2, choices = LotteryTicket.GameType.choices)

    # Stores numbers
    numbers = models.CharField(max_length = 50)

    # Indicates if the ticket is a winner
    winner = models.BooleanField(default = False)

    # Link to the draw that the ticket belongs to
    draw = models.ForeignKey("LotteryDraw", on_delete = models.CASCADE, related_name = "tickets", null = True, blank = True)

    # Prize calulated after draw
    calculated_prize = models.DecimalField(max_digits = 12, decimal_places=2, default = Decimal("0.00"))

    # Limit tickets per order
    def clean(self):
        if self.transaction_id:
            current_count = self.transaction.tickets.exclude(pk = self.pk).count()
            if current_count >= 10:
                raise ValidationError("You cannot add more than 10 tickets to one transaction.")

    # Auto-assign ticket to the next available draw
    def save(self, *args, **kwargs):

        if not self.draw:
            self.draw = LotteryDraw.objects.filter(game__game_type = self.lottery_type, draw_status = LotteryDraw.DrawStatus.SCHEDULED, draw_date__gte = date.today()).order_by("draw_date").first()

            if not self.draw:
                raise ValidationError("No upcoming draw found for this lottery type.")
        self.full_clean() 
        super().save(*args, **kwargs)

    # String representation
    def __str__(self):
        return f"{self.ticket_number} ({self.get_lottery_type_display()})"

#=============================================
# Notification Model
# Stores messages sent to users
#=============================================
class Notification(models.Model):
    
    # Help categorize notifications
    class NotificationType(models.TextChoices):

        PURCHASE = "purchase", "Purchase Confirmation"
        DRAW_RESULT = "draw_result", "Draw Result"
        WINNER = "winner", "Winner"
        GENERAL = "general", "General"

    # Unique ID for each notification
    notification_id = models.UUIDField(primary_key = True, default = uuid.uuid4, editable = False)

    # User who receives the notification
    recipient = models.ForeignKey(User, on_delete = models.CASCADE, related_name = "notifications")
    
    # Their associated order, related to their purchase
    order = models.ForeignKey(Order, on_delete = models.CASCADE, related_name = "notifications", null = True, blank = True)
    
    # Their associated draw, related to lottery results
    draw = models.ForeignKey("LotteryDraw", on_delete = models.CASCADE, related_name = "notifications", null = True, blank = True)
    
    # Email of the recipient
    recipient_email = models.EmailField()
    
    # Main message content shown to the user
    message = models.TextField()
   
    # Timestamp was created and sent
    date_sent = models.DateTimeField(auto_now_add = True)
    
    # Type or category of the notification
    notification_type = models.CharField(max_length = 20, choices = NotificationType.choices, default = NotificationType.GENERAL)
    
    # Shows whether the user read the notification
    is_read = models.BooleanField(default = False)

    # Returns the notification message
    def create_message(self):
        return self.message
        
    def log_notification(self):
        return f"Notification sent to {self.recipient_email}"
        
    def mark_as_read(self):
        self.is_read = True
        self.save()

    def send_email(self):
        pass

    def __str__(self):
        return f"{self.notification_type} - {self.recipient.username}"
        
#=================================
# LotteryDraw Model (Weekly Draw)
#=================================
class LotteryDraw(models.Model):

    # Status of draw lifecycle
    class DrawStatus(models.TextChoices):

        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        PUBLISHED = "published", "Published"

    # Unique draw ID
    draw_id = models.AutoField(primary_key = True)

    # Date of the draw 
    draw_date = models.DateField()

    # Lottery game associated with this draw
    game = models.ForeignKey(LotteryTicket, on_delete = models.CASCADE, related_name = "draws")

    # Winning numbers stored as a string
    winning_numbers = models.CharField(max_length = 50)

    # Total prize pool for this draw
    prize_amount = models.DecimalField(max_digits = 12, decimal_places = 2)

    # Current status of the draw
    draw_status = models.CharField(max_length = 20, choices = DrawStatus.choices, default = DrawStatus.SCHEDULED)


    # Converts winning numbers string into list
    def get_winning_numbers_list(self):
        
        return [int(num.strip()) for num in self.winning_numbers.split(",")]

    # Compares the ticket numbers to the winning numbers
    # and calculates the prize based on match count
    # Rules:
    # 5 matches = 100%
    # 4 matches = 20%
    # 3 matches = 5%
    # 2 matches = 1%
    # 1 or 0 = 0%
    def calculate_prize(self, ticket):

        # Convert winning numbers to a set for comparison
        winning_numbers = set(self.get_winning_numbers_list())

        # Extract ONLY the main numbers from ticket
        ticket_numbers = set(int(num.strip()) for num in ticket.numbers.strip("[]").split(","))

        # Count how many numbers match
        matches = len(winning_numbers.intersection(ticket_numbers))

        # Apply prize rules
        if matches == 5:
            return self.prize_amount * Decimal("1.00")
        elif matches == 4:
            return self.prize_amount * Decimal("0.20")
        elif matches == 3:
            return self.prize_amount * Decimal("0.05")
        elif matches == 2:
            return self.prize_amount * Decimal("0.01")
        else:
            return Decimal("0.00")
    
    # Loops through all tikets for this game
    # determines if each ticket is a winner
    # Updates:
    # - winner (True/False)
    # - calculated_prize
    def determine_winners(self):

        # Get all tickets
        tickets = self.tickets.all()

        for ticket in tickets:

            # Calculate prize for each ticket
            prize = self.calculate_prize(ticket)

            # Mark as winner if prize > 0
            ticket.winner = prize > 0

            # Store calculated prize
            ticket.calculated_prize = prize

            # Save updated ticket
            ticket.save()

        # Mark draw as completed after processing
        self.draw_status = self.DrawStatus.COMPLETED
        self.save()

    # Marks the draw as published so results are visible to users
    def publish_results(self):

        # Make sure draw is completed before publishing
        if self.draw_status != self.DrawStatus.COMPLETED:
            raise ValidationError("Draw must be completed before publishing results.")

        self.draw_status = self.DrawStatus.PUBLISHED
        self.save()

        for ticket in self.tickets.all():
            if ticket.winner:
                message = f"Congratulations! Ticket {ticket.ticket_number} won ${ticket.calculated_prize}."
                notification_type = Notification.NotificationType.WINNER
            else:
                message = f"Results are published. Ticket {ticket.ticket_number} did not win."
                notification_type = Notification.NotificationType.DRAW_RESULT
            
            Notification.objects.create(recipient = ticket.transaction.user, order = ticket.transaction, draw = self, recipient_email = ticket.transaction.user.email, message = message, notification_type = notification_type)
    # String representation of the draw for admin display
    def __str__(self):
        return f"{self.game.get_game_type_display()} Draw {self.draw_id} - {self.draw_date}"

