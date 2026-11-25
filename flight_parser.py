"""Flight Schedule Parser and Query Tool - command-line entry point.

Run from the project folder, for example:
    python flight_parser.py -i data/db.csv -a data/airports.txt
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime

from csv_loader import parse_files
from query import run_queries
from validator import load_airports

# TODO: put your own details here (plain ASCII, no spaces or underscores)
STUDENT_ID = "000RDB000"
FIRST_NAME = "Firstname"
LAST_NAME = "Lastname"


class RuntimeProblem(Exception):
    """A problem that ends the program with exit code 1."""


def build_parser():
    parser = argparse.ArgumentParser(description="Flight schedule parser and query tool")

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("-i", dest="input_file", metavar="FILE", help="parse a single CSV file")
    source.add_argument("-d", dest="input_folder", metavar="FOLDER", help="parse every .csv file in a folder")
    source.add_argument("-j", dest="json_file", metavar="FILE", help="load an existing JSON database")

    parser.add_argument("-a", dest="airports", metavar="FILE", help="airport list file (needed with -i and -d)")
    parser.add_argument("-o", dest="output", metavar="FILE", help="output path for the JSON database (default: db.json)")
    parser.add_argument("-q", dest="query_file", metavar="FILE", help="JSON file with queries")
    parser.add_argument("-r", dest="response_folder", metavar="FOLDER", default=".",
                        help="folder for the query response file (default: current directory)")
    return parser


def read_arguments(argv):
    parser = build_parser()
    args = parser.parse_args(argv)

    if (args.input_file or args.input_folder) and args.airports is None:
        parser.error("-a is required with -i and -d")
    if args.json_file and args.output is not None:
        parser.error("-o cannot be used with -j")
    return args


def read_json(path, what):
    """Read a JSON file, turn every problem into a RuntimeProblem."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError as err:
        raise RuntimeProblem(f"cannot read {what} '{path}': {err.strerror or err}")
    except ValueError:
        raise RuntimeProblem(f"{what} '{path}' is not valid JSON")


def load_database(path):
    data = read_json(path, "database file")
    if not isinstance(data, list):
        raise RuntimeProblem(f"database file '{path}' must contain a JSON array")
    for item in data:
        if not isinstance(item, dict):
            raise RuntimeProblem(f"database file '{path}' must contain a JSON array of objects")
    return data


def find_csv_files(args):
    """Return the list of CSV paths for -i or -d."""
    if args.input_file:
        if not os.path.isfile(args.input_file):
            raise RuntimeProblem(f"CSV file '{args.input_file}' does not exist")
        return [args.input_file]

    if not os.path.isdir(args.input_folder):
        raise RuntimeProblem(f"folder '{args.input_folder}' does not exist")
    paths = []
    for name in sorted(os.listdir(args.input_folder)):
        full_path = os.path.join(args.input_folder, name)
        if name.endswith(".csv") and os.path.isfile(full_path):
            paths.append(full_path)
    if len(paths) == 0:
        raise RuntimeProblem(f"no .csv files found in '{args.input_folder}'")
    return paths


def write_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as err:
        raise RuntimeProblem(f"cannot write '{path}': {err.strerror or err}")


def run_queries_from_file(args, db):
    queries = read_json(args.query_file, "query file")
    if not isinstance(queries, (dict, list)):
        raise RuntimeProblem(f"query file '{args.query_file}' must contain an object or an array")

    results = run_queries(db, queries)

    now = datetime.now().strftime("%Y%m%d_%H%M")
    file_name = f"response_{STUDENT_ID}_{FIRST_NAME}_{LAST_NAME}_{now}.json"
    write_json(os.path.join(args.response_folder, file_name), results)


def main(argv: list[str] | None = None) -> int:
    """Run the whole program and return the exit code (0, 1 or 2)."""
    try:
        args = read_arguments(argv)
    except SystemExit as err:
        # argparse calls sys.exit(); we want to return the code instead
        if isinstance(err.code, int):
            return err.code
        return 0

    logger = logging.getLogger("flight_parser")
    handler = None

    try:
        if args.json_file:
            db = load_database(args.json_file)
        else:
            paths = find_csv_files(args)
            try:
                airports = load_airports(args.airports)
            except (OSError, UnicodeDecodeError) as err:
                raise RuntimeProblem(f"cannot read airport file '{args.airports}': {err}")

            try:
                db, errors = parse_files(paths, airports)
            except (OSError, UnicodeDecodeError) as err:
                raise RuntimeProblem(f"cannot read CSV file: {err}")

            output = args.output if args.output is not None else "db.json"
            log_path = os.path.join(os.path.dirname(output), "errors.log")

            # set up the logger for errors.log
            logger.setLevel(logging.INFO)
            try:
                handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
            except OSError as err:
                raise RuntimeProblem(f"cannot write '{log_path}': {err.strerror or err}")
            handler.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
            logger.addHandler(handler)

            logger.info("Processed %d file(s): %d valid, %d invalid",
                        len(paths), len(db), len(errors))
            for message in errors:
                logger.warning(message)

            write_json(output, db)
            print(f"{len(db)} valid flights written to {output}, {len(errors)} invalid rows logged")

        if args.query_file:
            run_queries_from_file(args, db)

        return 0

    except RuntimeProblem as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    finally:
        # always remove and close the handler, so the next run starts clean
        if handler is not None:
            logger.removeHandler(handler)
            handler.close()


if __name__ == "__main__":
    sys.exit(main())
