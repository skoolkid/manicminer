#!/usr/bin/env python
import sys
import os
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
build_dir = '{}/build'.format(parent_dir)

SKOOLKIT_HOME = os.environ.get('SKOOLKIT_HOME')
if SKOOLKIT_HOME:
    if not os.path.isdir(SKOOLKIT_HOME):
        sys.stderr.write('SKOOLKIT_HOME={}: directory not found\n'.format(SKOOLKIT_HOME))
        sys.exit(1)
    sys.path.insert(0, SKOOLKIT_HOME)
    from skoolkit import skool2asm, skool2html, sna2skool, tap2sna
else:
    try:
        from skoolkit import skool2asm, skool2html, sna2skool, tap2sna
    except ImportError:
        sys.stderr.write('Error: SKOOLKIT_HOME is not set, and SkoolKit is not installed\n')
        sys.exit(1)

sys.stderr.write("Found SkoolKit in {}\n".format(skool2html.PACKAGE_DIR))

import mm2ctl

def write_skool():
    if not os.path.isdir(build_dir):
        os.mkdir(build_dir)

    # Write manic_miner.z80
    mmz80 = os.path.join(build_dir, 'manic_miner.z80')
    if not os.path.isfile(mmz80):
        tap2sna.main(('-d', build_dir, '@{}/manic_miner.t2s'.format(parent_dir)))

    # Write manic_miner.ctl
    ctlfile = os.path.join(build_dir, 'manic_miner.ctl')
    with open(ctlfile, 'wt') as f:
        f.write(mm2ctl.main(mmz80))

    # Write manic_miner.skool
    stdout = sys.stdout
    sys.stdout = StringIO()
    sna2skool.main(('-c', ctlfile, mmz80))
    skoolfile = os.path.join(build_dir, 'manic_miner.skool')
    with open(skoolfile, 'wt') as f:
        f.write(sys.stdout.getvalue())
    sys.stdout = stdout

    return skoolfile

def run_skool2asm():
    args = sys.argv[1:] + [write_skool()]
    skool2asm.main(args)

def run_skool2html():
    writer_class = '{}/skoolkit:manicminer.ManicMinerHtmlWriter'.format(parent_dir)
    skool2html_options = '-d {}/html'.format(build_dir)
    skool2html_options += ' -S {0}/resources -S {1} -S {1}/resources'.format(SKOOLKIT_HOME, parent_dir)
    skool2html_options += ' -W {}'.format(writer_class)
    args = skool2html_options.split() + sys.argv[1:] + [write_skool()]
    skool2html.main(args)
