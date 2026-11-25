"""Running queries against the flight database."""
from validator import parse_datetime

RECORD_KEYS = ["flight_id", "origin", "destination",
               "departure_datetime", "arrival_datetime", "price"]
ALLOWED_KEYS = RECORD_KEYS + ["min_price", "sort_by", "order", "limit"]

def is_number(value):
    """int or float, but not bool (True and False are ints in Python)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)

def is_valid_query(query):
    """Check keys and value types of a query."""
    if not isinstance(query, dict):
        return False

    for key in query:
        if key not in ALLOWED_KEYS:
            return False

    for key in ("flight_id", "origin", "destination"):
        if key in query and not isinstance(query[key], str):
            return False

    for key in ("departure_datetime", "arrival_datetime"):
        if key in query:
            if not isinstance(query[key], str):
                return False
            if parse_datetime(query[key]) is None:
                return False

    for key in ("price", "min_price"):
        if key in query and not is_number(query[key]):
            return False

    if "sort_by" in query:
        if not isinstance(query["sort_by"], str) or query["sort_by"] not in RECORD_KEYS:
            return False

    if "order" in query:
        if "sort_by" not in query:
            return False
        if not isinstance(query["order"], str) or query["order"] not in ("asc", "desc"):
            return False

    if "limit" in query:
        limit = query["limit"]
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
            return False

    return True


def flight_matches(flight, query):
    """True if the flight passes every condition in the query."""
    # Datetimes are zero-padded 'YYYY-MM-DD HH:MM', so comparing them as
    # strings gives the same result as comparing them as dates.
    if "flight_id" in query and flight["flight_id"] != query["flight_id"]:
        return False
    if "origin" in query and flight["origin"] != query["origin"]:
        return False
    if "destination" in query and flight["destination"] != query["destination"]:
        return False
    if "departure_datetime" in query and flight["departure_datetime"] < query["departure_datetime"]:
        return False
    if "arrival_datetime" in query and flight["arrival_datetime"] > query["arrival_datetime"]:
        return False
    if "price" in query and flight["price"] > query["price"]:
        return False
    if "min_price" in query and flight["price"] < query["min_price"]:
        return False
    return True


def run_query(db: list[dict], query: dict) -> dict:
    """Return one response entry for one query object.

    Valid query: {"query": query, "matches": [...]}
    Invalid query: {"query": query, "error": "INVALID_QUERY", "matches": []}
    """
    if not is_valid_query(query):
        return {"query": query, "error": "INVALID_QUERY", "matches": []}

    matches = []
    for flight in db:
        if flight_matches(flight, query):
            matches.append(flight)

    if "sort_by" in query:
        reverse = query.get("order", "asc") == "desc"
        # sorted() is stable, also with reverse=True, so equal values
        # keep their database order
        matches = sorted(matches, key=lambda flight: flight[query["sort_by"]], reverse=reverse)

    if "limit" in query:
        matches = matches[:query["limit"]]

    return {"query": query, "matches": matches}


def run_queries(db: list[dict], queries: dict | list) -> list[dict]:
    """Accept one query object or a list of them; always return a list."""
    if not isinstance(queries, list):
        queries = [queries]

    results = []
    for query in queries:
        results.append(run_query(db, query))
    return results
