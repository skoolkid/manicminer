# -*- coding: utf-8 -*-
import sys
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import os
import shutil
import tempfile
from lxml import etree
from xml.dom.minidom import parse
from xml.dom import Node
from unittest import TestCase

sys.path.insert(0, '../utils')

SKOOLKIT_HOME = os.environ.get('SKOOLKIT_HOME')
if not SKOOLKIT_HOME:
    sys.stderr.write('SKOOLKIT_HOME is not set; aborting\n')
    sys.exit(1)
if not os.path.isdir(SKOOLKIT_HOME):
    sys.stderr.write('SKOOLKIT_HOME={}: directory not found\n'.format(SKOOLKIT_HOME))
    sys.exit(1)
sys.path.insert(1, SKOOLKIT_HOME)
from skoolkit import skool2asm, skool2ctl, skool2html, skool2sft, sna2skool

MMZ80 = '../build/manic_miner.z80'
MMREF = '../manic_miner.ref'

XHTML_XSD = os.path.join(SKOOLKIT_HOME, 'XSD', 'xhtml1-strict.xsd')

OUTPUT_MM = """Creating directory {odir}
Using skool file: {skoolfile}
Using ref file: {reffile}
Parsing {skoolfile}
Creating directory {odir}/manic_miner
Copying {SKOOLKIT_HOME}/resources/skoolkit.css to {odir}/manic_miner/skoolkit.css
Copying ../resources/manic_miner.css to {odir}/manic_miner/manic_miner.css
  Writing disassembly files in manic_miner/asm
  Writing manic_miner/maps/all.html
  Writing manic_miner/maps/routines.html
  Writing manic_miner/maps/data.html
  Writing manic_miner/maps/messages.html
  Writing manic_miner/maps/unused.html
  Writing manic_miner/buffers/gbuffer.html
  Writing manic_miner/tables/caverns.html
  Writing manic_miner/reference/credits.html
  Writing manic_miner/reference/changelog.html
  Writing manic_miner/reference/facts.html
  Writing manic_miner/reference/glossary.html
  Writing manic_miner/reference/pokes.html
  Writing manic_miner/index.html"""

def _find_ids_and_hrefs(elements, doc_anchors, doc_hrefs):
    for node in elements:
        if node.nodeType == Node.ELEMENT_NODE:
            element_id = node.getAttribute('id')
            if element_id:
                doc_anchors.add(element_id)
            if node.tagName in ('a', 'link', 'img', 'script'):
                if node.tagName == 'a':
                    element_name = node.getAttribute('name')
                    if element_name:
                        doc_anchors.add(element_name)
                if node.tagName in ('a', 'link'):
                    element_href = node.getAttribute('href')
                    if element_href:
                        doc_hrefs.add(element_href)
                elif node.tagName in ('img', 'script'):
                    element_src = node.getAttribute('src')
                    if element_src:
                        doc_hrefs.add(element_src)
            _find_ids_and_hrefs(node.childNodes, doc_anchors, doc_hrefs)

def _read_files(root_dir):
    all_files = {} # filename -> (element ids and <a> names, hrefs and srcs)
    for root, dirs, files in os.walk(root_dir):
        for f in files:
            fname = os.path.join(root, f)
            all_files[fname] = (set(), set())
            if f.endswith('.html'):
                doc = parse(fname)
                _find_ids_and_hrefs(doc.documentElement.childNodes, *all_files[fname])
    return all_files

def check_links(root_dir):
    missing_files = []
    missing_anchors = []
    all_files = _read_files(root_dir)
    linked = set()
    for fname in all_files:
        for href in all_files[fname][1]:
            if not href.startswith('http://'):
                if href.startswith('#'):
                    link_dest = fname + href
                else:
                    link_dest = os.path.normpath(os.path.join(os.path.dirname(fname), href))
                dest_fname, sep, anchor = link_dest.partition('#')
                linked.add(dest_fname)
                if dest_fname not in all_files:
                    missing_files.append((fname, link_dest))
                elif anchor and anchor not in all_files[dest_fname][0]:
                    missing_anchors.append((fname, link_dest))
    orphans = set()
    for fname in all_files:
        if fname not in linked:
            orphans.add(fname)
    return all_files, orphans, missing_files, missing_anchors

class Stream:
    def __init__(self):
        self.buffer = StringIO()

    def write(self, text):
        self.buffer.write(text)

    def getvalue(self):
        return self.buffer.getvalue()

    def clear(self):
        self.buffer.seek(0)
        self.buffer.truncate()

class DisassembliesTestCase(TestCase):
    def setUp(self):
        self.maxDiff = None
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        sys.stdout = self.out = Stream()
        sys.stderr = self.err = Stream()
        self.tempfiles = []
        self.tempdirs = []

    def tearDown(self):
        for f in self.tempfiles:
            if os.path.isfile(f):
                os.remove(f)
        for d in self.tempdirs:
            if os.path.isdir(d):
                shutil.rmtree(d, True)
        sys.stdout = self.stdout
        sys.stderr = self.stderr

    def _to_lines(self, text):
        # Use rstrip() to remove '\r' characters (useful on Windows)
        lines = [line.rstrip() for line in text.split('\n')]
        if lines[-1] == '':
            lines.pop()
        return lines

    def write_text_file(self, contents='', suffix=''):
        fd, path = tempfile.mkstemp(suffix=suffix, dir='', text=True)
        path = os.path.basename(path.replace(os.path.sep, '/'))
        f = os.fdopen(fd, 'wt')
        self.tempfiles.append(path)
        f.write(contents)
        f.close()
        return path

    def run_skoolkit_command(self, cmd, args, out_lines=True, err_lines=False):
        self.out.clear()
        self.err.clear()
        try:
            cmd(args.split())
        except SystemExit:
            pass
        out = self._to_lines(self.out.getvalue()) if out_lines else self.out.getvalue()
        err = self._to_lines(self.err.getvalue()) if err_lines else self.err.getvalue()
        return out, err

    def write_mm_skool(self):
        import mm2ctl
        ctl = mm2ctl.main(MMZ80)
        options = '-c {}'.format(self.write_text_file(ctl))
        skool, error = self.run_skoolkit_command(sna2skool.main, '{} {}'.format(options, MMZ80), out_lines=False)
        self.assertEqual(len(error), 0)
        return self.write_text_file(skool)

class AsmTestCase(DisassembliesTestCase):
    def write_mm(self, options):
        skoolfile = self.write_mm_skool()
        args = '{} {}'.format(options, skoolfile)
        output, error = self.run_skoolkit_command(skool2asm.main, args, err_lines=True)
        self.assertTrue(any([line.startswith('Parsed {}'.format(skoolfile)) for line in error]))
        self.assertTrue(error[-1].startswith('Wrote ASM to stdout'))

class CtlTestCase(DisassembliesTestCase):
    def write_mm(self, options):
        args = '{} {}'.format(options, self.write_mm_skool())
        output, stderr = self.run_skoolkit_command(skool2ctl.main, args)
        self.assertEqual(stderr, '')

class HtmlTestCase(DisassembliesTestCase):
    def setUp(self):
        DisassembliesTestCase.setUp(self)
        self.odir = 'html-{}'.format(os.getpid())
        self.tempdirs.append(self.odir)

    def _validate_xhtml(self):
        if os.path.isfile(XHTML_XSD):
            with open(XHTML_XSD) as f:
                xmlschema_doc = etree.parse(f)
            xmlschema = etree.XMLSchema(xmlschema_doc)
            for root, dirs, files in os.walk(self.odir):
                for fname in files:
                    if fname[-5:] == '.html':
                        htmlfile = os.path.join(root, fname)
                        try:
                            xhtml = etree.parse(htmlfile)
                        except etree.LxmlError as e:
                            self.fail('Error while parsing {}: {}'.format(htmlfile, e.message))
                        try:
                            xmlschema.assertValid(xhtml)
                        except etree.DocumentInvalid as e:
                            self.fail('Error while validating {}: {}'.format(htmlfile, e.message))

    def _check_links(self):
        all_files, orphans, missing_files, missing_anchors = check_links(self.odir)
        if orphans or missing_files or missing_anchors:
            error_msg = []
            if orphans:
                error_msg.append('Orphaned files: {}'.format(len(orphans)))
                for fname in orphans:
                    error_msg.append('  {}'.format(fname))
            if missing_files:
                error_msg.append('Links to non-existent files: {}'.format(len(missing_files)))
                for fname, link_dest in missing_files:
                    error_msg.append('  {} -> {}'.format(fname, link_dest))
            if missing_anchors:
                error_msg.append('Links to non-existent anchors: {}'.format(len(missing_anchors)))
                for fname, link_dest in missing_anchors:
                    error_msg.append('  {} -> {}'.format(fname, link_dest))
            self.fail('\n'.join(error_msg))

    def write_mm(self, options):
        skoolfile = self.write_mm_skool()
        main_options = '-W ../skoolkit:manicminer.ManicMinerHtmlWriter'
        main_options += ' -c Config/SkoolFile={}'.format(skoolfile)
        main_options += ' -S {} -S {}'.format('{}/resources'.format(SKOOLKIT_HOME), '../resources')
        main_options += ' -d {}'.format(self.odir)
        shutil.rmtree(self.odir, True)

        # Write the disassembly
        output, error = self.run_skoolkit_command(skool2html.main, '{} {} {}'.format(main_options, options, MMREF))
        self.assertEqual(len(error), 0)
        reps = {'odir': self.odir, 'SKOOLKIT_HOME': SKOOLKIT_HOME, 'skoolfile': skoolfile, 'reffile': MMREF}
        self.assertEqual(OUTPUT_MM.format(**reps).split('\n'), output)

        self._validate_xhtml()
        self._check_links()

class SftTestCase(DisassembliesTestCase):
    def write_mm(self, options):
        skoolfile = self.write_mm_skool()
        with open(skoolfile, 'rt') as f:
            orig_skool = f.read().split('\n')
        args = '{} {}'.format(options, skoolfile)
        sft, error = self.run_skoolkit_command(skool2sft.main, args, out_lines=False)
        self.assertEqual(error, '')
        options = '-T {}'.format(self.write_text_file(sft))
        skool, error = self.run_skoolkit_command(sna2skool.main, '{} {}'.format(options, MMZ80))
        self.assertEqual(orig_skool[:-1], skool)
