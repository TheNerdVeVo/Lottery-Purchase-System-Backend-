from django.contrib import admin
from .models import LotteryTicket, Order, ElectronicTicket, CustomerProfile, LotteryDraw

##==========================================
# These are the different databases in Django
#===========================================
admin.site.register(Order)
admin.site.register(ElectronicTicket)
admin.site.register(CustomerProfile)
admin.site.register(LotteryTicket)
admin.site.register(LotteryDraw)