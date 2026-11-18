#!/usr/bin/env python3
import sys
import os
import argparse

SKOOLKIT_HOME = os.environ.get('SKOOLKIT_HOME')
if not SKOOLKIT_HOME:
    sys.stderr.write('SKOOLKIT_HOME is not set; aborting\n')
    sys.exit(1)
if not os.path.isdir(SKOOLKIT_HOME):
    sys.stderr.write('SKOOLKIT_HOME={}; directory not found\n'.format(SKOOLKIT_HOME))
    sys.exit(1)
sys.path.insert(0, SKOOLKIT_HOME)

MANICMINER_HOME = os.environ.get('MANICMINER_HOME')
if not MANICMINER_HOME:
    sys.stderr.write('MANICMINER_HOME is not set; aborting\n')
    sys.exit(1)
if not os.path.isdir(MANICMINER_HOME):
    sys.stderr.write('MANICMINER_HOME={}; directory not found\n'.format(MANICMINER_HOME))
    sys.exit(1)

from skoolkit.graphics import Frame, Udg, scr_udgs
from skoolkit.image import ImageWriter
from skoolkit.snapshot import get_snapshot

class ManicMiner:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.font = {c: snapshot[15360 + 8 * c:15368 + 8 * c] for c in range(32, 122)}

    def _place_items(self, udg_array, addr):
        item_udg_data = self.snapshot[addr + 692:addr + 700]
        for a in range(addr + 629, addr + 653, 5):
            attr = self.snapshot[a]
            if attr == 255:
                break
            if attr == 0:
                continue
            ink, paper = attr & 7, (attr // 8) & 7
            if ink == paper:
                ink = max(3, (ink + 1) & 7)
                attr = (attr & 248) + ink
            x, y = self._get_coords(a + 1)
            udg_array[y][x] = Udg(attr, item_udg_data)

    def _place_guardians(self, udg_array, addr):
        cavern_no = (addr - 45056) // 1024

        # Horizontal guardians
        for a in range(addr + 702, addr + 730, 7):
            attr = self.snapshot[a]
            if attr == 255:
                break
            if not attr:
                continue
            sprite_index = self.snapshot[a + 4]
            if cavern_no >= 7 and cavern_no not in (9, 15):
                sprite_index |= 4
            sprite = self._get_graphic(addr + 768 + 32 * sprite_index, attr & 127)
            x, y = self._get_coords(a + 1)
            self._place_graphic(udg_array, sprite, x, y * 8)

        if cavern_no == 4:
            # Eugene
            attr = (self.snapshot[addr + 544] & 248) + 7
            sprite = self._get_graphic(addr + 736, attr)
            self._place_graphic(udg_array, sprite, 15, 0)
        elif cavern_no in (7, 11):
            # Kong Beast
            attr = 68
            sprite = self._get_graphic(addr + 768, attr)
            self._place_graphic(udg_array, sprite, 15, 0)
        else:
            # Regular vertical guardians
            for a in range(addr + 733, addr + 761, 7):
                attr = self.snapshot[a]
                if attr == 255:
                    break
                sprite_index = self.snapshot[a + 1]
                sprite = self._get_graphic(addr + 768 + 32 * sprite_index, attr)
                pixel_y = self.snapshot[a + 2] & 127
                x = self.snapshot[a + 3]
                self._place_graphic(udg_array, sprite, x, pixel_y, bleed=True)

        # Light beam in Solar Power Generator
        if cavern_no == 18:
            beam_udg = Udg(119, (0,) * 8)
            for y in range(15):
                udg_array[y][23] = beam_udg

    def _place_willy(self, udg_array, addr):
        attr = (self.snapshot[addr + 544] & 248) + 7
        sprite_index = self.snapshot[addr + 617]
        direction = self.snapshot[addr + 618]
        willy = self._get_graphic(33280 + 128 * direction + 32 * sprite_index, attr)
        x, y = self._get_coords(addr + 620)
        self._place_graphic(udg_array, willy, x, y * 8)

    def _get_cavern_udgs(self, addr, guardians=1, willy=1):
        # Collect block graphics
        block_graphics = {}
        bg_udg = Udg(self.snapshot[addr + 544], self.snapshot[addr + 545:addr + 553])
        block_graphics[bg_udg.attr] = bg_udg
        for a in range(addr + 553, addr + 616, 9):
            attr = self.snapshot[a]
            block_graphics[attr] = Udg(attr, self.snapshot[a + 1:a + 9])

        # Build the cavern UDG array
        udg_array = []
        for a in range(addr, addr + 512, 32):
            udg_array.append([block_graphics.get(attr, bg_udg) for attr in self.snapshot[a:a + 32]])
        if addr == 64512:
            # The Final Barrier (top half)
            udg_array[:8] = scr_udgs(self.snapshot, 0, 0, 32, 8, 40960, 64512)

        # Cavern name
        name_udgs = [Udg(48, self.font[b]) for b in self.snapshot[addr + 512:addr + 544]]
        udg_array.append(name_udgs)

        self._place_items(udg_array, addr)
        if guardians:
            self._place_guardians(udg_array, addr)
        if willy:
            self._place_willy(udg_array, addr)

        # Portal
        attr = self.snapshot[addr + 655]
        portal_udgs = self._get_graphic(addr + 656, attr)
        x, y = self._get_coords(addr + 688)
        udg_array[y][x:x + 2] = portal_udgs[0]
        udg_array[y + 1][x:x + 2] = portal_udgs[1]

        return udg_array

    def _get_graphic(self, addr, attr):
        # Build a 16x16 graphic
        udgs = []
        for offsets in ((0, 1), (16, 17)):
            o1, o2 = offsets
            udgs.append([])
            for a in (addr + o1, addr + o2):
                udgs[-1].append(Udg(attr, self.snapshot[a:a + 16:2]))
        return udgs

    def _get_coords(self, addr):
        p1, p2 = self.snapshot[addr:addr + 2]
        x = p1 & 31
        y = 8 * (p2 & 1) + (p1 & 224) // 32
        return x, y

    def _place_graphic(self, udg_array, graphic, x, pixel_y, bg_attr=None, bleed=False):
        if pixel_y & 7:
            graphic = self._shift_graphic(graphic, pixel_y & 7)
        elif bleed:
            blank_udg = Udg(graphic[0][0].attr, [0] * 8)
            graphic.append([blank_udg] * len(graphic[0]))
        y = pixel_y // 8
        for i, row in enumerate(graphic):
            for j, udg in enumerate(row):
                old_udg = udg_array[y + i][x + j]
                if bg_attr is None or old_udg.attr == bg_attr:
                    new_attr = (old_udg.attr & 56) | (udg.attr & 71)
                else:
                    new_attr = old_udg.attr
                new_data = [old_udg.data[k] | udg.data[k] for k in range(8)]
                udg_array[y + i][x + j] = Udg(new_attr, new_data)

    def _shift_graphic(self, graphic, y_delta):
        attr = graphic[0][0].attr
        blank_udg = Udg(attr, [0] * 8)
        width = len(graphic[0])
        prev_row = [blank_udg] * width
        shifted_graphic = []
        for row in graphic + [[blank_udg] * width]:
            shifted_graphic.append([])
            for i, udg in enumerate(row):
                shifted_udg_data = prev_row[i].data[-y_delta:] + udg.data[:-y_delta]
                shifted_graphic[-1].append(Udg(attr, shifted_udg_data))
                prev_row[i] = udg
        return shifted_graphic

def _do_pokes(specs, snapshot):
    for spec in specs:
        addr, val = spec.split(',', 1)
        step = 1
        if '-' in addr:
            addr1, addr2 = addr.split('-', 1)
            addr1 = int(addr1)
            if '-' in addr2:
                addr2, step = [int(i) for i in addr2.split('-', 1)]
            else:
                addr2 = int(addr2)
        else:
            addr1 = int(addr)
            addr2 = addr1
        addr2 += 1
        value = int(val)
        for a in range(addr1, addr2, step):
            snapshot[a] = value

def _place_willy(mm, cavern, spec):
    cavern_addr = 45056 + 1024 * cavern
    udg_array = mm._get_cavern_udgs(cavern_addr, 1, 0)
    if spec:
        values = []
        for n in spec.split(','):
            try:
                values.append(int(n))
            except ValueError:
                values.append(None)
        values += [None] * (3 - len(values))
        x, y, frame = values
        if x is not None and y is not None:
            willy = mm._get_graphic(33280 + 32 * (frame or 0), 7)
            bg_attr = mm.snapshot[cavern_addr + 544]
            mm._place_graphic(udg_array, willy, x, y * 8, bg_attr)
    return udg_array

def run(imgfname, options):
    snapshot = get_snapshot('{}/build/manic_miner.z80'.format(MANICMINER_HOME))
    with open(f'{SKOOLKIT_HOME}/skoolkit/resources/48.rom', 'rb') as f:
        snapshot[:0x4000] = f.read()
    _do_pokes(options.pokes, snapshot)
    mm = ManicMiner(snapshot)
    udg_array = _place_willy(mm, options.cavern, options.willy)
    if options.geometry:
        wh, xy = options.geometry.split('+', 1)
        width, height = [int(n) for n in wh.split('x')]
        x, y = [int(n) for n in xy.split('+')]
        udg_array = [row[x:x + width] for row in udg_array[y:y + height]]
    frame = Frame(udg_array, options.scale)
    image_writer = ImageWriter()
    with open(imgfname, "wb") as f:
        image_writer.write_image([frame], f)

###############################################################################
# Begin
###############################################################################
parser = argparse.ArgumentParser(
    usage='mmimage.py [options] FILE.png',
    description="Create an image of a cavern in Manic Miner.",
    formatter_class=argparse.RawTextHelpFormatter,
    add_help=False
)
parser.add_argument('imgfname', help=argparse.SUPPRESS, nargs='?')
group = parser.add_argument_group('Options')
group.add_argument('-c', dest='cavern', type=int, default=0,
                   help='Create an image of this cavern (default: 0)')
group.add_argument('-g', dest='geometry', metavar='WxH+X+Y',
                   help='Create an image with this geometry')
group.add_argument('-p', dest='pokes', metavar='A[-B[-C]],V', action='append', default=[],
                   help="Do POKE N,V for N in {A, A+C, A+2C,...B} (this option may be\n"
                        "used multiple times)")
group.add_argument('-s', dest='scale', type=int, default=2,
                   help='Set the scale of the image (default: 2)')
group.add_argument('-w', dest='willy', metavar='X,Y[,F]',
                   help="Place Willy at (X,Y) with animation frame F (0-7)\n")
namespace, unknown_args = parser.parse_known_args()
if unknown_args or not namespace.imgfname:
    parser.exit(2, parser.format_help())
run(namespace.imgfname, namespace)
