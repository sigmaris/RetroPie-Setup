#!/usr/bin/env python3
"""
Gets the best KMS mode for a given MAME machine/game, currently only works with
super-resolution KMS modes (e.g. 1920x240) as it only checks height and refresh

Outputs: <width> <height> <p(rogressive) or i(nterlaced)> <refresh> <rotation> <aspect>
"""
import argparse
import collections
import os
import re
import sqlite3
import subprocess
import sys

BASEDIR = os.path.dirname(__file__)
KMSMode = collections.namedtuple('KMSMode', ('width', 'height', 'refresh', 'interlaced'))
KMSMODE_RE = re.compile(r"(\d+)x(\d+)(i?)@(\d+)")
SQL = """
SELECT display, width, height, rotate, refresh
FROM machines
WHERE name = ?
"""


def list_kms_modes():
    proc = subprocess.Popen(
        [os.path.join(BASEDIR, 'listmodes')], stdout=subprocess.PIPE
    )
    modes = []
    for line in proc.stdout:
        m = KMSMODE_RE.match(line.decode())
        if m:
            modes.append(KMSMode(
                width=int(m.group(1)),
                height=int(m.group(2)),
                refresh=int(m.group(4)),
                interlaced=(m.group(3) == 'i'),
            ))
        else:
            raise Exception("Unrecognised KMS mode: {}".format(line))
    return modes


def find_best_mode(kms_modes, width, height, refresh):
    # Try and find mode with height >= wanted height
    tall_enough_modes = sorted(
        (m for m in kms_modes if m.height >= height),
        key=lambda m: (m.height, -m.width)  # wider modes first for SuperRes
    )
    min_refresh_diff = 0.0
    best_mode = None
    for kms_mode in tall_enough_modes:
        kms_refresh = kms_mode.refresh
        if kms_mode.interlaced:
            kms_refresh /= 2
        refresh_diff = abs(kms_refresh - refresh)
        if (best_mode is None or refresh_diff < min_refresh_diff):
            best_mode = kms_mode
            min_refresh_diff = refresh_diff
    return best_mode


def main(args):
    if not os.path.isfile(args.mamedb):
        raise Exception("Missing MAME video mode DB: {}".format(args.mamedb))

    conn = sqlite3.connect(args.mamedb)

    for row in conn.execute(SQL, (args.machine,)):
        display, width, height, rotate, refresh = row
        if display != 'raster':
            raise Exception("Unsupported display: {}".format(display))
        break
    else:
        raise Exception("Machine/Game not found: {}".format(args.machine))

    kms_modes = list_kms_modes()
    if rotate in (90, 270):
        vertical = True
        wanted_w, wanted_h = height, width
    else:
        vertical = False
        wanted_w, wanted_h = width, height
    best_mode = find_best_mode(kms_modes, wanted_w, wanted_h, refresh)
    if vertical:
        # a 3:4 vertical game scaled down to 4:3 monitor is 2.25 units wide
        # and 2.25 is 0.5625 of a 4 unit wide monitor
        aspect = best_mode.width * 0.5625 / best_mode.height
    else:
        aspect = best_mode.width / best_mode.height
    if best_mode:
        print("{m.width} {m.height} {interlaced} {m.refresh} {rotate} {aspect:.2f}".format(
            m=best_mode, interlaced=('i' if best_mode.interlaced else 'p'),
            rotate=rotate, aspect=aspect
        ))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-m', '--mamedb', default=os.path.join(BASEDIR, 'mamevideo.db'),
        help="Path to video SQLite DB generated from MAME"
    )
    parser.add_argument('machine', help="machine name")

    try:
        main(parser.parse_args())
    except Exception as exc:
        sys.stderr.write(str(exc) + "\n")
        sys.exit(1)
