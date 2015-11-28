#!/usr/bin/env python
import sys
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import os
import argparse
from collections import OrderedDict

try:
    from skoolkit.snapshot import get_snapshot
    from skoolkit import tap2sna, sna2skool
except ImportError:
    SKOOLKIT_HOME = os.environ.get('SKOOLKIT_HOME')
    if not SKOOLKIT_HOME:
        sys.stderr.write('SKOOLKIT_HOME is not set; aborting\n')
        sys.exit(1)
    if not os.path.isdir(SKOOLKIT_HOME):
        sys.stderr.write('SKOOLKIT_HOME={}; directory not found\n'.format(SKOOLKIT_HOME))
        sys.exit(1)
    sys.path.insert(0, SKOOLKIT_HOME)
    from skoolkit.snapshot import get_snapshot
    from skoolkit import tap2sna, sna2skool

MANICMINER_HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = '{}/build'.format(MANICMINER_HOME)
MM_Z80 = '{}/manic_miner.z80'.format(BUILD_DIR)

def get_screen_buffer_address_table(snapshot):
    lines = ['w 33536 Screen buffer address lookup table ']
    lines.append('D 33536 Used by the routines at #R35140, #R36344, #R36469, #R36593, #R37173 and #R37503. The value of the Nth entry (0<=N<=127) in this lookup table is the screen buffer address for the point with pixel coordinates (x,y)=(0,N), with the origin (0,0) at the top-left corner.')
    lines.append('@ 33536 label=SBUFADDRS')
    y = 0
    for addr in range(33536, 33792, 2):
        lines.append('W {} y={}'.format(addr, y))
        y += 1
    lines.append('i 33792')
    return '\n'.join(lines)

def _write_horizontal_guardians(lines, snapshot, start):
    lines.append('N {} The next 28 bytes are copied to #R32958 and define the horizontal guardians.'.format(start))
    terminated = False
    index = 1
    for a in range(start, start + 28, 7):
        terminated = terminated or snapshot[a] == 255
        unused = terminated or snapshot[a] == 0
        suffix = ''
        ab_addr = snapshot[a + 1] + 256 * snapshot[a + 2]
        show_details = False
        if 23552 <= ab_addr < 24064:
            speed = 'slow' if snapshot[a] & 128 else 'normal'
            x = ab_addr % 32
            y = (ab_addr - 23552) // 32
            min_x = snapshot[a + 5] % 32
            max_x = snapshot[a + 6] % 32
            suffix += ': y={}, initial x={}, {}<=x<={}, speed={}'.format(y, x, min_x, max_x, speed)
            show_details = True
        if unused:
            suffix += ' (unused)'
        if show_details:
            lines.append('M {},7 Horizontal guardian {}{}'.format(a, index, suffix))
            lines.append('B {},1'.format(a))
            lines.append('W {},2'.format(a + 1))
            lines.append('B {},4,1'.format(a + 3))
        else:
            lines.append('B {},7 Horizontal guardian {}{}'.format(a, index, suffix))
        index += 1
    lines.append('B {},1 Terminator'.format(start + 28))

def _write_vertical_guardians(lines, snapshot, start):
    lines.append('N {} The next 28 bytes are copied to #R32989 and define the vertical guardians.'.format(start))
    terminated = False
    index = 1
    for a in range(start, start + 28, 7):
        terminated = terminated or snapshot[a] == 255
        unused = terminated or snapshot[a] == 0
        suffix = ''
        if unused:
            suffix += ' (unused)'
        else:
            y = snapshot[a + 2]
            x = snapshot[a + 3]
            y_inc = snapshot[a + 4]
            if y_inc >= 128:
                y_inc -= 256
            min_y = snapshot[a + 5]
            max_y = snapshot[a + 6]
            y_inc_prefix = '' if start == 59101 else 'initial '
            suffix += ': x={}, initial y={}, {}<=y<={}, {}y-increment={}'.format(x, y, min_y, max_y, y_inc_prefix, y_inc)
        lengths = '7' if unused else '7,1'
        lines.append('B {},{} Vertical guardian {}{}'.format(a, lengths, index, suffix))
        index += 1

def _get_teleport_code(cavern_num):
    code = ''
    key = 1
    while cavern_num:
        if cavern_num & 1:
            code += str(key)
        cavern_num //= 2
        key += 1
    return code + '6'

def get_caverns(snapshot):
    lines = []

    for a in range(45056, 65536, 1024):
        cavern_num = a // 1024 - 44
        cavern = snapshot[a:a + 1024]
        cavern_name = ''.join([chr(b) for b in cavern[512:544]]).strip()
        lines.append('b {} {} (teleport: {})'.format(a, cavern_name, _get_teleport_code(cavern_num)))
        lines.append('@ {} label=CAVERN{}'.format(a, cavern_num))
        lines.append('D {} Used by the routine at #R34436.'.format(a))
        lines.append('D {0} #UDGTABLE {{ #CALL:cavern({0}) }} TABLE#'.format(a))
        lines.append('D {} The first 512 bytes are the attributes that define the layout of the cavern.'.format(a))
        lines.append('B {},512,8 Attributes'.format(a))

        # Cavern name
        lines.append('N {} The next 32 bytes are copied to #R32768 and specify the cavern name.'.format(a + 512))
        lines.append('T {},32 Cavern name'.format(a + 512))

        # Block graphics
        attrs = snapshot[a + 544:a + 608:9]
        tile_usage = [' (unused)'] * 8
        for b in snapshot[a:a + 512]:
            if b in attrs:
                tile_usage[attrs.index(b)] = ''
        udg_table = '#UDGTABLE {{ #tiles{} }} TABLE#'.format(cavern_num)
        lines.append('N {} The next 72 bytes are copied to #R32800 and contain the attributes and graphic data for the tiles used to build the cavern.'.format(a + 544))
        lines.append('N {} {}'.format(a + 544, udg_table))
        lines.append('B {},9,9 Background{}'.format(a + 544, tile_usage[0]))
        lines.append('B {},9,9 Floor{}'.format(a + 553, tile_usage[1]))
        lines.append('B {},9,9 Crumbling floor{}'.format(a + 562, tile_usage[2]))
        lines.append('B {},9,9 Wall{}'.format(a + 571, tile_usage[3]))
        lines.append('B {},9,9 Conveyor{}'.format(a + 580, tile_usage[4]))
        lines.append('B {},9,9 Nasty 1{}'.format(a + 589, tile_usage[5]))
        lines.append('B {},9,9 Nasty 2{}'.format(a + 598, tile_usage[6]))
        lines.append('B {},9,9 Extra{}'.format(a + 607, tile_usage[7]))

        # Miner Willy's start position
        lines.append("@ {} ignoreua:m".format(a + 616))
        lines.append("N {} The next seven bytes are copied to #GBUF32872,32878 and specify Miner Willy's initial location and appearance in the cavern.".format(a + 616))
        lines.append("B {} Pixel y-coordinate * 2 (see #R32872)".format(a + 616))
        lines.append("B {} Animation frame (see #R32873)".format(a + 617))
        direction = ('right', 'left')[snapshot[a + 618]]
        lines.append("B {} Direction and movement flags: facing {} (see #R32874)".format(a + 618, direction))
        lines.append("B {} Airborne status indicator (see #R32875)".format(a + 619))
        ab_addr = snapshot[a + 620] + 256 * snapshot[a + 621]
        x = ab_addr % 32
        y = (ab_addr - 23552) // 32
        lines.append("W {} Location in the attribute buffer at #R23552: ({},{}) (see #R32876)".format(a + 620, y, x))
        lines.append("B {} Jumping animation counter (see #R32878)".format(a + 622))

        # Conveyor
        lines.append('N {} The next four bytes are copied to #R32879 and specify the direction, location and length of the{} conveyor.'.format(a + 623, tile_usage[4]))
        direction = 'left' if snapshot[a + 623] == 0 else 'right'
        sb_addr = snapshot[a + 624] + 256 * snapshot[a + 625]
        x = sb_addr % 32
        y = 8 * ((sb_addr - 28672) // 2048) + (sb_addr % 256) // 32
        length = snapshot[a + 626]
        lines.append('B {} Direction ({})'.format(a + 623, direction))
        lines.append('W {} Location in the screen buffer at #R28672: ({},{})'.format(a + 624, y, x))
        lines.append('B {} Length'.format(a + 626))

        # Border colour
        lines.append('N {} The next byte is copied to #R32883 and specifies the border colour.'.format(a + 627))
        lines.append('B {} Border colour'.format(a + 627))

        # Byte 628
        lines.append('N {} The next byte is copied to #R32884, but is not used.'.format(a + 628))
        lines.append('B {} Unused'.format(a + 628))

        # Items
        lines.append('N {} The next 25 bytes are copied to #R32885 and specify the location and initial colour of the items in the cavern.'.format(a + 629))
        terminated = False
        for i, addr in enumerate(range(a + 629, a + 654, 5)):
            terminated = terminated or snapshot[addr] == 255
            unused = terminated or snapshot[addr] == 0
            suffix = ''
            ab_addr = snapshot[addr + 1] + 256 * snapshot[addr + 2]
            show_details = False
            if 23552 <= ab_addr < 24064:
                x = ab_addr % 32
                y = (ab_addr - 23552) // 32
                suffix += ' at ({},{})'.format(y, x)
                show_details = True
            if unused:
                suffix += ' (unused)'
            if show_details:
                lines.append('M {},5 Item {}{}'.format(addr, i + 1, suffix))
                lines.append('B {},1'.format(addr))
                lines.append('W {},2'.format(addr + 1))
                lines.append('B {},2,1'.format(addr + 3))
            else:
                lines.append('B {},5 Item {}{}'.format(addr, i + 1, suffix))
        lines.append('B {} Terminator'.format(a + 654))

        # Portal
        lines.append('N {} The next 37 bytes are copied to #R32911 and define the portal graphic and its location.'.format(a + 655))
        lines.append('N {} #UDGTABLE {{ #portal{} }} TABLE#'.format(a + 655, cavern_num))
        lines.append('B {},1 Attribute'.format(a + 655))
        lines.append('B {},32,8 Graphic data'.format(a + 656))
        ab_addr = snapshot[a + 688] + 256 * snapshot[a + 689]
        ab_x = ab_addr % 32
        ab_y = (ab_addr - 23552) // 32
        lines.append('W {} Location in the attribute buffer at #R23552: ({},{})'.format(a + 688, ab_y, ab_x))
        sb_addr = snapshot[a + 690] + 256 * snapshot[a + 691]
        sb_x = sb_addr % 32
        sb_y = 8 * ((sb_addr - 24576) // 2048) + (sb_addr % 256) // 32
        lines.append('W {} Location in the screen buffer at #R24576: ({},{})'.format(a + 690, sb_y, sb_x))

        # Item
        lines.append('N {} The next eight bytes are copied to #R32948 and define the item graphic.'.format(a + 692))
        lines.append('N {} #UDGTABLE {{ #item{} }} TABLE#'.format(a + 692, cavern_num))
        lines.append('B {},8 Item graphic data'.format(a + 692))

        # Air
        lines.append('N {} The next byte is copied to #R32956 and specifies the initial air supply in the cavern.'.format(a + 700))
        lines.append('B {} Air'.format(a + 700))

        # Game clock
        lines.append('N {} The next byte is copied to #R32957 and initialises the game clock.'.format(a + 701))
        lines.append('B {} Game clock'.format(a + 701))

        # Horizontal guardians
        _write_horizontal_guardians(lines, snapshot, a + 702)

        # Bytes 731 and 732
        prefix = 'The next two bytes are copied to #R32987 and #R32988'
        if cavern_num == 4:
            lines.append("N {} {} and specify Eugene's initial direction and pixel y-coordinate.".format(a + 731, prefix))
            lines.append('B {},1 Initial direction (down)'.format(a + 731))
            lines.append('B {},1 Initial pixel y-coordinate'.format(a + 732))
        elif cavern_num in (7, 11):
            lines.append("N {} {}; the first byte specifies the Kong Beast's initial status, but the second byte is not used.".format(a + 731, prefix))
            lines.append('B {},1 Initial status (on the ledge)'.format(a + 731))
            lines.append('B {},1 Unused'.format(a + 732))
        else:
            lines.append('N {} {} but are not used.'.format(a + 731, prefix))
            lines.append('B {},2 Unused'.format(a + 731))

        # Special graphics and vertical guardians
        if cavern_num in (0, 1, 2, 4):
            if cavern_num == 4:
                lines.append('N {} The next three bytes are unused.'.format(a + 733))
                lines.append('B {},3 Unused'.format(a + 733))
            else:
                lines.append('N {} The next byte is copied to #R32989 and indicates that there are no vertical guardians in this cavern.'.format(a + 733))
                lines.append('B {},1 Terminator'.format(a + 733))
                lines.append('N {} The next two bytes are unused.'.format(a + 734))
                lines.append('B {},2 Unused'.format(a + 734))
            if cavern_num == 0:
                lines.append('@ 45792 label=SWORDFISH')
                desc = 'swordfish graphic that appears in #R64512(The Final Barrier) when the game is completed'
                udgarray_macro = '#UDGARRAY2,69,4,2;45792;45793;45808,70;45809,71(swordfish)'
                comment = 'Swordfish graphic data'
            elif cavern_num == 1:
                lines.append('@ 46816 label=PLINTH')
                desc = 'plinth graphic that appears on the Game Over screen'
                udgarray_macro = '#UDGARRAY2,71,4,2;46816-46833-1-16(plinth)'
                comment = 'Plinth graphic data'
            elif cavern_num == 2:
                lines.append('@ 47840 label=BOOT')
                desc = 'boot graphic that appears on the Game Over screen (see #R35210). It also appears at the bottom of the screen next to the remaining lives when #FACT#6031769(cheat mode) is activated (see #R34608)'
                udgarray_macro = '#UDGARRAY2,71,4,2;47840-47857-1-16(boot)'
                comment = 'Boot graphic data'
            else:
                lines.append('@ 49888 label=EUGENEG')
                desc = 'Eugene graphic'
                udgarray_macro = '#UDGARRAY2,23,4,2;49888-49905-1-16(eugene)'
                comment = 'Eugene graphic data'
            lines.append('N {} The next 32 bytes define the {}.'.format(a + 736, desc))
            lines.append('N {} #UDGTABLE {{ {} }} TABLE#'.format(a + 736, udgarray_macro))
            lines.append('B {},32,8 {}'.format(a + 736, comment))
        else:
            _write_vertical_guardians(lines, snapshot, a + 733)
            start = a + 761
            if snapshot[start] == 255:
                lines.append('B {},1 Terminator'.format(start))
                start += 1
            unused = a + 768 - start
            lines.append('N {} The next {} bytes are unused.'.format(start, unused))
            lines.append('B {},{} Unused'.format(start, unused))

        # Guardian graphic data
        gg_addr = a + 768
        gg_table = '#UDGTABLE { '
        macros = []
        for addr in range(gg_addr, gg_addr + 256, 32):
            sprite_index = (addr & 224) // 32
            img_fname = '{}_guardian{}'.format(cavern_name.lower().replace(' ', '_'), sprite_index)
            if cavern_num in (7, 11) and sprite_index < 4:
                attr = 68 # Kong Beast
            elif cavern_num == 13:
                attr = snapshot[a + 733] # Skylab
            elif cavern_num in (8, 10, 12, 14, 16, 17, 18, 19) and sprite_index < 4:
                attr = snapshot[a + 733] # Vertical guardian
            else:
                attr = snapshot[a + 702] # Horizontal guardian
            macros.append('#UDGARRAY2,{},4,2;{}-{}-1-16({})'.format(attr, addr, addr + 17, img_fname))
        gg_table += ' | '.join(macros) + ' } TABLE#'
        lines.append('N {} The next 256 bytes are copied to #R33024 and define the guardian graphics.'.format(gg_addr))
        lines.append('N {} {}'.format(gg_addr, gg_table))
        lines.append('B {},256,8 Guardian graphic data'.format(gg_addr))

    return '\n'.join(lines)

def run(subcommand):
    func = functions[subcommand][0]
    if not os.path.isdir(BUILD_DIR):
        os.mkdir(BUILD_DIR)
    if not os.path.isfile(MM_Z80):
        tap2sna.main(('-d', BUILD_DIR, '@{}/manic_miner.t2s'.format(MANICMINER_HOME)))
    ctlfile = '{}/{}.ctl'.format(BUILD_DIR, subcommand)
    with open(ctlfile, 'wt') as f:
        f.write(func(get_snapshot(MM_Z80)))
    stdout = sys.stdout
    sys.stdout = StringIO()
    sna2skool.main(('-c', ctlfile, MM_Z80))
    skool = sys.stdout.getvalue()
    sys.stdout = stdout
    for line in skool.split('\n')[2:-1]:
        print(line)

###############################################################################
# Begin
###############################################################################
functions = OrderedDict((
    ('caverns', (get_caverns, 'Caverns (45056-65535)')),
    ('sbat', (get_screen_buffer_address_table, 'Screen buffer address table (33536-33791)'))
))
subcommands = '\n'.join('  {} - {}'.format(k, v[1]) for k, v in functions.items())
parser = argparse.ArgumentParser(
    usage='%(prog)s SUBCOMMAND',
    description="Produce a skool file snippet for Manic Miner. SUBCOMMAND must be one of:\n\n{}".format(subcommands),
    formatter_class=argparse.RawTextHelpFormatter,
    add_help=False
)
parser.add_argument('subcommand', help=argparse.SUPPRESS, nargs='?')
namespace, unknown_args = parser.parse_known_args()
if unknown_args or namespace.subcommand not in functions:
    parser.exit(2, parser.format_help())
run(namespace.subcommand)
