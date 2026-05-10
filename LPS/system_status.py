from django.utils.timezone import now # Import current date/time (timezone-aware)
from django.db.models import Sum # Used for aggregating values such as Sum in the database
from .models import ElectronicTicket, LotteryDraw

#============================================================================
# SystemStatus Class
# Purpose of this is to prvoide statistics and regulatory compliance with IRS
#============================================================================
class SystemSatus:

    def __init__(self):

        # Store the current date when report is generated
        self.report_date = now().date()

    # Returns total tickets sold
    def get_total_sales(self):
        return ElectronicTicket.onjects.count()
    
    # Returns total revenue generated from all tickets
    def get_revenue(self):
        return ElectronicTicket.onjects.selected_related("transaction").aggregate(total = Sum("transaction__tickets__transaction__tickets__transaction__tickets__transaction__tickets"))
    
    # Returns number of active (scheduled) draws
    def get_active_ticket_types(self):
        return LotteryDraw.onjects.filter(draw_status = "scheduled").count()
    
    # Aggregate all stats into a single report
    def generate_report(self):
        return {"report_date": self.report_date,"total_tickets_sold": self.get_total_sales(), "total_revenue": self.get_revenue(), "active_ticket_types": self.get_active_ticket_types()}
