from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from LPS.models import LotteryTicket, LotteryDraw, CustomerProfile


GAMES = [
    ("PB", Decimal("2.00"), Decimal("50000000.00")),
    ("MM", Decimal("2.00"), Decimal("40000000.00")),
    ("LT", Decimal("1.00"), Decimal("10000000.00")),
    ("TS", Decimal("1.50"), Decimal("1000000.00")),
]


class Command(BaseCommand):
    help = "Seed LPS with the 4 lottery games, default admin user, and a scheduled draw per game."

    def handle(self, *args, **opts):
        # admin user
        if not User.objects.filter(username="admin").exists():
            admin = User.objects.create_superuser(
                username="admin", email="admin@lps.gov", password="admin123",
                first_name="System", last_name="Administrator",
            )
            CustomerProfile.objects.get_or_create(
                user=admin,
                defaults={"home_address": "Texas Lottery HQ, Austin TX",
                          "phone_number": "5125551000"},
            )
            self.stdout.write(self.style.SUCCESS("Created admin / admin123"))
        else:
            self.stdout.write("admin user already exists")

        # games
        for gt, price, prize in GAMES:
            obj, created = LotteryTicket.objects.update_or_create(
                game_type=gt,
                defaults={"ticket_price": price, "prize_amount": prize},
            )
            self.stdout.write(f"{'created' if created else 'updated'} game {gt}")

            # ensure one scheduled draw a week out
            if not LotteryDraw.objects.filter(
                game=obj,
                draw_status=LotteryDraw.DrawStatus.SCHEDULED,
                draw_date__gte=date.today(),
            ).exists():
                LotteryDraw.objects.create(
                    game=obj,
                    draw_date=date.today() + timedelta(days=7),
                    winning_numbers="",
                    prize_amount=prize,
                    draw_status=LotteryDraw.DrawStatus.SCHEDULED,
                )

        self.stdout.write(self.style.SUCCESS("Seed complete."))
