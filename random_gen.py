import random

#=====================================================================
# Generates random lottery numbers based on the selected lottery type
# Args: lottery_type (str): The type of lottery (PB, MM, LT, TS)
# Returns: str: Comma-seperated string of 5 unique numbers
#=======================================================================
def generate_random_numbers(lottery_type):

    # POWERBALL
    if lottery_type == "PB": 

        # Pick 5 unique numbers from 1-69
        return ",".join(map(str, sorted(random.sample(range(1, 70), 5))))
    
    # Mega Millions
    elif lottery_type == "MM":

        # Pick 5 unique numbers from 1-70
        return ",".join(map(str, sorted(random.sample(range (1, 71),5))))
    
    # LOTTO TEXAS
    elif lottery_type == "LT":

        # Pick 5 unique numbers from 1-54
        return ",".join(map(str, sorted(random.sample(range(1, 55), 5))))

    # TEXAS TWO STEP
    elif lottery_type == "TS":

        # Pick 5 unique numbers from 1-35
        return ",".join(map(str, sorted(random.sample(range(1, 36), 5))))
    
    # Invalid lottery type
    else:
        raise ValueError("Invalid lottery type")
