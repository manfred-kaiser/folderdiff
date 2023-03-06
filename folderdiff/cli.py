# -*- coding: utf-8 -*-

import argparse
import sys
from folderdiff import FileCompare


def main():
    parser = argparse.ArgumentParser(description='folder compare tool')
    parser.add_argument(
        'directories',
        metavar='FILES',
        nargs=2,
        help='directory to create sha256 sums'
    )
    parser.add_argument(
        '--prefix',
        dest="prefix",
        help="remove the profix from the source or destination folder"
    )

    args = parser.parse_args()

    hashlist_src = FileCompare(args.directories[0], args.prefix)
    hashlist_dest = FileCompare(args.directories[1], args.prefix)

    result = hashlist_src.compare(hashlist_dest)
    result.print_result()

    if not result:
        sys.exit(1)
