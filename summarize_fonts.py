#!/usr/bin/env python3

# Summarize a number of standard fonts, and some fonts we like, for easy rendering in the diagrams.
from fontTools import ttLib
import glob
import os.path
import pprint
import sys


# For each font, create a table containing normalized widths of all characters.
# To normalize them, divide the horizontal advance by the em width.
# Also store the normalized line width

all_details = {}

for name in glob.glob('fonts/*.ttf'):
    print(f'processing file {name}', file=sys.stderr)
    tt = ttLib.TTFont(name)
    emwidth = tt['head'].unitsPerEm

    linedistance = 1 + tt['hhea'].lineGap/emwidth

    details = {'name': os.path.basename(name),
               'lineheight': linedistance
               }


    map = tt.getBestCmap()
    metrics = tt['hmtx']
    table = {ch: metrics[map[ch]][0]/emwidth for ch in range(32, 127)}
    details['sizes'] = table
    all_details[details['name']] = details

with open('fontsizes.py', 'w') as out:
    out.write(f'font_sizes = {pprint.pformat(all_details)}')
