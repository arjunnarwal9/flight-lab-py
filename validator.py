"""Checking single CSV rows and loading the airport list."""
import math
import re
from datetime import datetime

DATETIME_FORMAT = "%Y-%m-%d %H:%M"


def load_airports(path: str) -> set[str]:
    """Read the airport list file and return the set of codes."""
    airports = set()
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            code = line.strip()
            # skip blank lines and comment lines
            if code == "" or code.startswith("#"):
                continue
            airports.add(code)
    return airports


def parse_datetime(text):
    """Return a datetime if text is exactly 'YYYY-MM-DD HH:MM', else None.

    The regex makes sure the format is exact (zero-padded, one space, ASCII
    digits only). strptime then checks that the date and time really exist.
    """
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}", text) is None:
        return None
    try:
        return datetime.strptime(text, DATETIME_FORMAT)
    except ValueError:
        return None


def is_valid_airport(code, airports):
    """3 uppercase ASCII letters and present in the airport list."""
    if re.fullmatch(r"[A-Z]{3}", code) is None:
        return False
    return code in airports


def validate_row(fields: list[str], airports: set[str]) -> str | None:
    """Return None if the row is valid, otherwise the first error code."""
    # 1. field count
    if len(fields) != 6:
        return "WRONG_FIELD_COUNT"

    fields = [field.strip() for field in fields]

    # 2. empty fields
    for field in fields:
        if field == "":
            return "MISSING_FIELD"

    flight_id, origin, destination, departure, arrival, price = fields

    # 3. flight id: 2-8 ASCII letters or digits
    if re.fullmatch(r"[A-Za-z0-9]{2,8}", flight_id) is None:
        return "INVALID_FLIGHT_ID"

    # 4. and 5. airports
    if not is_valid_airport(origin, airports):
        return "INVALID_ORIGIN"
    if not is_valid_airport(destination, airports):
        return "INVALID_DESTINATION"

    # 6. same airport
    if origin == destination:
        return "SAME_ORIGIN_DESTINATION"

    # 7. and 8. dates
    departure_time = parse_datetime(departure)
    if departure_time is None:
        return "INVALID_DEPARTURE"
    arrival_time = parse_datetime(arrival)
    if arrival_time is None:
        return "INVALID_ARRIVAL"

    # 9. arrival must be later than departure
    if arrival_time <= departure_time:
        return "ARRIVAL_NOT_AFTER_DEPARTURE"

    # 10. price must be a finite number
    try:
        price_value = float(price)
    except ValueError:
        return "INVALID_PRICE"
    if not math.isfinite(price_value):
        return "INVALID_PRICE"

    # 11. price must be positive
    if price_value <= 0:
        return "NON_POSITIVE_PRICE"

    return None

def to_record(fields: list[str]) -> dict:
    """Turn a valid row into a flight record dictionary."""
    fields = [field.strip() for field in fields]
    return {
        "flight_id": fields[0],
        "origin": fields[1],
        "destination": fields[2],
        "departure_datetime": fields[3],
        "arrival_datetime": fields[4],
        "price": float(fields[5]),
    }