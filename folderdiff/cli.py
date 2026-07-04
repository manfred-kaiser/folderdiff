"""Command line interface for folderdiff."""

import argparse
import sys

from folderdiff import FileCompare


def main() -> None:
    """Run the folderdiff command line tool."""
    parser = argparse.ArgumentParser(description="folder compare tool")
    parser.add_argument(
        "directories",
        metavar="FILES",
        nargs=2,
        help="directory to create sha256 sums",
    )
    parser.add_argument(
        "--prefix",
        dest="prefix",
        help="remove the prefix from the source or destination folder",
    )

    args = parser.parse_args()

    hashlist_src = FileCompare(args.directories[0], args.prefix)
    hashlist_dest = FileCompare(args.directories[1], args.prefix)

    try:
        result = hashlist_src.compare(hashlist_dest)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)

    result.print_result()

    if not result:
        sys.exit(1)
