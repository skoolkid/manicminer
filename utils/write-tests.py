#!/usr/bin/env python3
import sys
import os

SKOOLKIT_HOME = os.environ.get('SKOOLKIT_HOME')
if not SKOOLKIT_HOME:
    sys.stderr.write('SKOOLKIT_HOME is not set; aborting\n')
    sys.exit(1)
if not os.path.isdir(SKOOLKIT_HOME):
    sys.stderr.write('SKOOLKIT_HOME={}: directory not found\n'.format(SKOOLKIT_HOME))
    sys.exit(1)
sys.path.insert(0, '{}/tools'.format(SKOOLKIT_HOME))
from testwriter import write_tests

SKOOL = 'mm.skool'

SNAPSHOT = 'build/manic_miner.z80'

OUTPUT = """Using ref files: mm.ref, bugs.ref, changelog.ref, facts.ref, pokes.ref, sound.ref
Parsing {skoolfile}
Output directory: {odir}/manic_miner
Copying {SKOOLKIT_HOME}/skoolkit/resources/skoolkit.css to skoolkit.css
Copying mm.css to mm.css
Writing disassembly files in asm
Writing maps/all.html
Writing maps/routines.html
Writing maps/data.html
Writing maps/messages.html
Writing maps/unused.html
Writing buffers/gbuffer.html
Writing reference/bugs.html
Writing reference/changelog.html
Writing reference/facts.html
Writing reference/glossary.html
Writing reference/pokes.html
Writing tables/caverns.html
Writing reference/credits.html
Writing sound/sound.html
Writing index.html"""

write_tests(SKOOL, SNAPSHOT, OUTPUT)
