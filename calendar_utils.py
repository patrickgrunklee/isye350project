"""
Calendar Utilities for Warehouse Optimization Model
Handles calendar-based lead times and days-on-hand aging

SIMPLIFIED VERSION:
- Fixed 21 business days per month (same as Model 0.1)
- Lead times and days-on-hand are specified in CALENDAR days
- Convert calendar days to business day offsets using 5/7 ratio (weekends)

Author: Claude Code
Date: 2025
"""

import math

# Fixed business days per month
BUSINESS_DAYS_PER_MONTH = 21
TOTAL_MONTHS = 120

def calendar_days_to_business_days(calendar_days):
    """
    Convert calendar days to business days (approximately).

    Assumes 5 business days per 7 calendar days (excludes weekends).

    Args:
        calendar_days: Number of calendar days (includes weekends)

    Returns:
        Number of business days (rounded)
    """
    business_days = calendar_days * (5.0 / 7.0)
    return int(round(business_days))


def add_business_days(month, day, business_days_offset):
    """
    Add business days to a (month, day) position.

    Args:
        month: Current month (1-120)
        day: Current business day (1-21)
        business_days_offset: Number of business days to add

    Returns:
        (new_month, new_day) or None if outside planning horizon
    """
    # Convert to absolute business day
    absolute_day = (month - 1) * BUSINESS_DAYS_PER_MONTH + day

    # Add offset
    new_absolute_day = absolute_day + business_days_offset

    # Check bounds
    if new_absolute_day < 1:
        return None  # Before planning horizon

    max_days = TOTAL_MONTHS * BUSINESS_DAYS_PER_MONTH
    if new_absolute_day > max_days:
        return None  # After planning horizon

    # Convert back to (month, day)
    new_month = ((new_absolute_day - 1) // BUSINESS_DAYS_PER_MONTH) + 1
    new_day = ((new_absolute_day - 1) % BUSINESS_DAYS_PER_MONTH) + 1

    return (new_month, new_day)


def get_delivery_date(order_month, order_day, lead_time_calendar_days):
    """
    Calculate when delivery arrives based on order date and calendar-day lead time.

    Args:
        order_month: Month order is placed (1-120)
        order_day: Business day order is placed (1-21)
        lead_time_calendar_days: Lead time in calendar days

    Returns:
        (delivery_month, delivery_day) or None if outside horizon
    """
    business_days_offset = calendar_days_to_business_days(lead_time_calendar_days)
    return add_business_days(order_month, order_day, business_days_offset)


def get_available_shipment_date(arrival_month, arrival_day, days_on_hand_calendar_days):
    """
    Calculate when inventory can be shipped based on days-on-hand aging requirement.

    Args:
        arrival_month: Month inventory arrived (1-120)
        arrival_day: Business day inventory arrived (1-21)
        days_on_hand_calendar_days: Required aging period in calendar days

    Returns:
        (available_month, available_day) when inventory can ship
    """
    business_days_offset = calendar_days_to_business_days(days_on_hand_calendar_days)
    return add_business_days(arrival_month, arrival_day, business_days_offset)


def get_order_placement_date(delivery_month, delivery_day, lead_time_calendar_days):
    """
    Calculate when order must be placed to arrive on target date.

    Args:
        delivery_month: Target delivery month (1-120)
        delivery_day: Target delivery business day (1-21)
        lead_time_calendar_days: Lead time in calendar days

    Returns:
        (order_month, order_day) when order must be placed
    """
    business_days_offset = calendar_days_to_business_days(lead_time_calendar_days)
    return add_business_days(delivery_month, delivery_day, -business_days_offset)


if __name__ == "__main__":
    # Test the calendar functions
    print("Testing Simplified Calendar Utilities")
    print("="*80)

    print("\nCalendar to Business Day Conversions:")
    print("-"*80)
    test_cases = [3, 5, 7, 10, 15, 28, 34, 37, 42, 46]
    for cal_days in test_cases:
        bus_days = calendar_days_to_business_days(cal_days)
        print(f"  {cal_days:2d} calendar days = {bus_days:2d} business days ({bus_days*100/cal_days:.1f}% of calendar)")

    print("\n\nLead Time Examples:")
    print("-"*80)

    # Example 1: SKUW1 to Columbus (34 day lead time)
    print("\nSKUW1 to Columbus (34 calendar day lead time):")
    order_date = (1, 5)  # Month 1, Day 5
    delivery = get_delivery_date(1, 5, 34)
    if delivery:
        print(f"  Order placed: Month {order_date[0]}, Day {order_date[1]}")
        print(f"  Delivery arrives: Month {delivery[0]}, Day {delivery[1]}")
        bus_days_elapsed = (delivery[0]-1)*21 + delivery[1] - ((order_date[0]-1)*21 + order_date[1])
        print(f"  Business days elapsed: {bus_days_elapsed}")

    # Example 2: SKUE1 to Columbus (37 day lead time, 46 day DoH)
    print("\nSKUE1 to Columbus (37 day lead time, 46 day DoH):")
    order_date = (1, 10)
    delivery = get_delivery_date(1, 10, 37)
    if delivery:
        print(f"  Order placed: Month {order_date[0]}, Day {order_date[1]}")
        print(f"  Delivery arrives: Month {delivery[0]}, Day {delivery[1]}")

        available = get_available_shipment_date(delivery[0], delivery[1], 46)
        if available:
            print(f"  Available to ship: Month {available[0]}, Day {available[1]}")
            total_bus_days = (available[0]-1)*21 + available[1] - ((order_date[0]-1)*21 + order_date[1])
            print(f"  Total business days (order → available): {total_bus_days}")

    print("\n\nReverse Calculation (When to order):")
    print("-"*80)

    # Want delivery on Month 3, Day 15 with 34 day lead time
    target_delivery = (3, 15)
    order_needed = get_order_placement_date(3, 15, 34)
    if order_needed:
        print(f"  Target delivery: Month {target_delivery[0]}, Day {target_delivery[1]}")
        print(f"  Must order by: Month {order_needed[0]}, Day {order_needed[1]}")

    print("\n\nBoundary Tests:")
    print("-"*80)

    # Test going past Month 120
    result = get_delivery_date(120, 15, 34)
    print(f"  Order Month 120, Day 15 + 34 days: {result} (should be None)")

    # Test going before Month 1
    result = get_order_placement_date(1, 5, 34)
    print(f"  Need delivery Month 1, Day 5 - 34 days: {result} (may be None)")

    print("\n" + "="*80)
