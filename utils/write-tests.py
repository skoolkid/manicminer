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

SKOOL = 'sources/mm.skool'

SNAPSHOT = 'build/manic_miner.z80'

OUTPUT = """Using skool file: {skoolfile}
Using ref files: sources/mm.ref, sources/bugs.ref, sources/changelog.ref, sources/facts.ref, sources/pokes.ref
Parsing {skoolfile}
Creating directory {odir}/manic_miner
Copying {SKOOLKIT_HOME}/skoolkit/resources/skoolkit.css to {odir}/manic_miner/skoolkit.css
Copying sources/mm.css to {odir}/manic_miner/mm.css
  Writing disassembly files in manic_miner/asm
  Writing manic_miner/maps/all.html
  Writing manic_miner/maps/routines.html
  Writing manic_miner/maps/data.html
  Writing manic_miner/maps/messages.html
  Writing manic_miner/maps/unused.html
  Writing manic_miner/buffers/gbuffer.html
  Writing manic_miner/reference/bugs.html
  Writing manic_miner/reference/changelog.html
  Writing manic_miner/reference/facts.html
  Writing manic_miner/reference/glossary.html
  Writing manic_miner/reference/pokes.html
  Writing manic_miner/tables/caverns.html
  Writing manic_miner/reference/credits.html
  Writing manic_miner/index.html"""

HTML_WRITER = 'sources:manicminer.ManicMinerHtmlWriter'

ASM_WRITER = 'sources:manicminer.ManicMinerAsmWriter'

write_tests(SKOOL, SNAPSHOT, OUTPUT, HTML_WRITER, ASM_WRITER)
