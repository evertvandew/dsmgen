#!/usr/bin/env python3
""" Script to generate """
import os, os.path, shutil
import subprocess
from dataclasses import dataclass, field
import argparse
from typing import Any, List
import re
import sys


parser = argparse.ArgumentParser(__doc__)
parser.add_argument('master_file')
parser.add_argument('--css', nargs='?', default='pandoc.css')
parser.add_argument('--test', action='store_true')
parser.add_argument('--images', action='store_true')
parser.add_argument('--all', action='store_true')
parser.add_argument('--split_level', default='2')

args = parser.parse_args()


do_all = args.all or not(args.test or args.images)


def test(source: str):
    """ Extract all the code snippets, compile and run them """
    fname = '/tmp/test_source.rs'
    failures = []
    def snippets(source):
        it = re.finditer(r'^```([a-z+]*)$', source, flags=re.M)
        try:
            while m := next(it):
                m2 = next(it)
                code = source[m.end():m2.start()]
                yield code
        except StopIteration:
            pass
        return
    
    for i, code in enumerate(snippets(source)):
        if os.path.exists(fname):
            os.remove(fname)
        with open(fname, 'w') as out:
            out.write(code)
        result = subprocess.run(f'rustc {fname}', shell=True, cwd=os.path.dirname(fname))
        if result.returncode != 0:
            print(f"Could not compile example {i+1}", file=sys.stderr)
            failures.append(i)
            continue
        result = subprocess.run(os.path.splitext(fname)[0])
        if result.returncode != 0:
            print(f"Running example {i+1} returned an error code", file=sys.stderr)
            failures.append(i)
            continue
    
        print(f"Successfully tested {i+1}")
    if failures:
        print(f"The following tests failed: {failures}")
    else:
        print("All test code was run successfully")



master_file = args.master_file
if not os.path.exists(master_file):
    raise f"File {master_file} does not exists"

use_original_heading = False

# Create the output directory if it doesn't exist yet
if not os.path.exists('html'):
    os.mkdir('html')

# Copy the original source file and the stylesheet to the html directory
shutil.copy(master_file, 'html')
shutil.copy(args.css, 'html')
os.chdir('html')

# Generate the PlantUML diagrams from the source
if args.images or do_all:
    subprocess.run(f'plantuml {master_file}', shell=True)

# Replace the plantuml definitions with the code to include the images.
data = open(master_file).read()

parts = re.split("^@startuml.*?^@enduml", data, flags=re.MULTILINE + re.DOTALL)
base_name = os.path.splitext(os.path.basename(master_file))[0]
replacements = [f'![]({base_name}.png)'] + [f'\n![]({base_name}_{cnt:03}.png)\n' for cnt in range(1, len(parts)-1)] + ['']
result = '\n'.join('%s\n%s'%i for i in zip(parts, replacements))



if args.test or do_all:
    test(result)



# Extract the metadata for replication to all subdocuments
metadata = (m := re.match(r'(^%.*$\n)+', result, flags=re.M)) and m.group() or ''
result = result[len(metadata):]

# For ease of manipulations wrap the various headers into a simple data structure
@dataclass
class Header:
    heading: str
    original: str
    level: int
    count: int
    parent: Any
    start: int
    subheadings: List[Any] = field(default_factory=list)
    text: str = ''
    
    def iterate(self):
        if self.level != 0:
            yield self
        for h in self.subheadings:
            yield from h.iterate()
    def __iter__(self):
        return self.iterate()
    def getNumber(self):
        if self.parent and self.level > 1:
            return f'{self.parent.getNumber()}.{self.count}'
        return str(self.count)
    def getNumberedHeading(self):
        return f'{self.getNumber()} {self.heading}'
    def getFileName(self):
        return f'{self.getNumberedHeading().replace(" ", "_")}.html'

    def __hash__(self):
        return id(self)

    @staticmethod
    def splitHeaders(text, level, max_level, parent=None):
        print('Max level:', max_level)
        if level > max_level:
            return []
        
        headers = list(re.finditer('^' + '#'*level + r'\s(.*?)$', text, flags=re.M))
        if use_original_heading:
            start = [m.start() for m in headers]
        else:
            start = [m.end() for m in headers]
        end = [m.start() for m in headers[1:]] + [len(text)]
        texts = [text[s:e] for s, e in zip(start, end)]
        result = [Header(
            heading=h.groups()[0],
            text=texts[i],
            level=level,
            count=i+1,
            parent=parent,
            original=texts[i],
            start=h.start()) for i, h in enumerate(headers)]
        for i, r in enumerate(result):
            r.subheadings = Header.splitHeaders(texts[i], level+1, max_level, parent=r)
            if r.subheadings:
                r.text = r.text[:r.subheadings[0].start]
        return result
                
    @staticmethod
    def new_doc(text, split_level):
        doc = Header(heading='', original=text, level=0, count=0, parent=None, start=0)
        chapters = Header.splitHeaders(text, 1, split_level, doc)
        doc.subheadings = chapters
        doc.text = text[:doc.subheadings[0].start]
        return doc

doc = Header.new_doc(result, int(args.split_level))

# Write a table of contents having links to each part, for easy navigation.
def getToc(heading):
    result = []
    if heading.heading:
        result.append(f'<li><a href={heading.getFileName()}>{heading.getNumberedHeading()}</a></li>')
    if heading.subheadings:
        result.append('\n<ul>\n')
        for h in heading.subheadings:
            result.append(getToc(h))
        result.append('</ul>\n')
    return '\n'.join(result)

with open('toc.inc', 'w') as out:
    out.write(getToc(doc))

        
# For each page, determine which pages it should navigate to.
@dataclass
class NavLinks:
    back: int
    forward: int
    up: int

filename_list = [h.getFileName() for h in doc]

nav_links = {h: NavLinks(
        back = 'index.html' if i == 0 else filename_list[i-1],
        forward = None if i >= len(filename_list)-1 else filename_list[i+1],
        up = None if h.level==1 else h.parent.getFileName()
    ) for i, h in enumerate(doc)}

nav_widgets = {h: '<table><tr><td class="prev">' +
                  f'<a href="{l.back}">Prev</a>' +
                  f'</td><td><a href="{l.up or "index.html"}">Up</a></td><td class="next">' +
                  (f'<a href="{l.forward}">Next</a>' if l.forward else '') + '</td></tr></table>'
               for h, l in [(_, nav_links[_]) for _ in doc.iterate() if _ in nav_links]}


section_template = '''{metadata}<div class="navheader">{nav_widget}</div><hr/>

{heading}

{text}
{toc}
<hr/><div class="navfooter">{nav_widget}</div>'''

def generateSection(text, fname):
    subprocess.run(f'pandoc -s --css pandoc.css --highlight-style pygments --filter pandoc-citeproc --from=markdown --to=html -o {fname}', shell=True,
                   input=text,
                   encoding='utf8')

for h in doc.iterate():
    if h.level == 0:
        continue
    toc = getToc(h) if h.subheadings else '\n'
    txt = section_template.format(
            heading='#'*h.level + f' {h.getNumberedHeading()}',
            text=h.text,
            nav_widget=nav_widgets[h],
            toc=toc,
            # Only use the document title for the chapters and sections.
            metadata=f'{metadata.splitlines()[0]}\n'
          )
    generateSection(txt, h.getFileName())

# Generate an index.html
txt = f'''{metadata}# Introduction

{doc.text}

# Contents

{getToc(doc)}

# About the author

Evert van de Waal (1967) started programming on the ZX-Spectrum in 1982.
After graduating from Twente University with an MSc in Electronics (1993), he became a software consultant developing mainly embedded software, usually as software architect or lead designer.

His main languages have been C/C++ and Python, and he is enthusiastic about the benefits of Rust over C++.

Contact Evert as "books AT vdwi-software.nl".
'''
generateSection(txt, 'index.html')
