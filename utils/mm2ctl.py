#!/usr/bin/env python
import sys
import os

try:
    from skoolkit.snapshot import get_snapshot
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

def get_screen_buffer_address_table():
    lines = []
    y = 0
    for addr in range(33536, 33792, 2):
        lines.append('W {} y={}'.format(addr, y))
        y += 1
    return '\n'.join(lines)

def _write_horizontal_guardians(lines, snapshot, start):
    lines.append('D {} The next 28 bytes are copied to #R32958 and define the horizontal guardians.'.format(start))
    terminated = False
    index = 1
    for a in range(start, start + 28, 7):
        terminated = terminated or snapshot[a] == 255
        unused = terminated or snapshot[a] == 0
        suffix = ''
        ab_addr = snapshot[a + 1] + 256 * snapshot[a + 2]
        if 23552 <= ab_addr < 24064:
            speed = 'slow' if snapshot[a] & 128 else 'normal'
            x = ab_addr % 32
            y = (ab_addr - 23552) // 32
            min_x = snapshot[a + 5] % 32
            max_x = snapshot[a + 6] % 32
            suffix += ': y={}, initial x={}, {}<=x<={}, speed={}'.format(y, x, min_x, max_x, speed)
        if unused:
            suffix += ' (unused)'
        lines.append('M {},7 Horizontal guardian {}{}'.format(a, index, suffix))
        lines.append('B {},1'.format(a))
        lines.append('W {},2'.format(a + 1))
        lines.append('B {},4,1'.format(a + 3))
        index += 1
    lines.append('B {},1 Terminator'.format(start + 28))

def _write_vertical_guardians(lines, snapshot, start):
    lines.append('D {} The next 28 bytes are copied to #R32989 and define the vertical guardians.'.format(start))
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
        lines.append('B {},7,1 Vertical guardian {}{}'.format(a, index, suffix))
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
        lines.append('D {} Used by the routine at #R34436.'.format(a))
        lines.append('D {0} #UDGTABLE {{ #CALL:cavern({0}) }} TABLE#'.format(a))
        lines.append('D {} The first 512 bytes are the attributes that define the layout of the cavern.'.format(a))
        lines.append('B {},512,8 Attributes'.format(a))

        # Cavern name
        lines.append('D {} The next 32 bytes contain the cavern name.'.format(a + 512))
        lines.append('T {},32 Cavern name'.format(a + 512))

        # Block graphics
        udgs = []
        attrs = []
        for addr, tile_type in ((a + 544, 'background'), (a + 553, 'floor'), (a + 562, 'crumbling_floor'), (a + 571, 'wall'), (a + 580, 'conveyor'), (a + 589, 'nasty1'), (a + 598, 'nasty2'), (a + 607, 'spare')):
            attr = snapshot[addr]
            attrs.append(attr)
            udgs.append('#UDG{},{}({}_{})'.format(addr + 1, attr, tile_type, cavern_num))
        tile_usage = [' (unused)'] * 8
        for b in snapshot[a:a + 512]:
            if b in attrs:
                tile_usage[attrs.index(b)] = ''
        udg_table = '#UDGTABLE { ' + ' | '.join(udgs) + ' } TABLE#'
        lines.append('D {} The next 72 bytes contain the attributes and graphic data for the tiles used to build the room.'.format(a + 544))
        lines.append('D {} {}'.format(a + 544, udg_table))
        lines.append('B {},9,9 Background{}'.format(a + 544, tile_usage[0]))
        lines.append('B {},9,9 Floor{}'.format(a + 553, tile_usage[1]))
        lines.append('B {},9,9 Crumbling floor{}'.format(a + 562, tile_usage[2]))
        lines.append('B {},9,9 Wall{}'.format(a + 571, tile_usage[3]))
        lines.append('B {},9,9 Conveyor{}'.format(a + 580, tile_usage[4]))
        lines.append('B {},9,9 Nasty 1{}'.format(a + 589, tile_usage[5]))
        lines.append('B {},9,9 Nasty 2{}'.format(a + 598, tile_usage[6]))
        lines.append('B {},9,9 Spare{}'.format(a + 607, tile_usage[7]))

        # Miner Willy's start position
        lines.append("D {} The next 7 bytes specify Miner Willy's initial location and appearance in the cavern.".format(a + 616))
        lines.append("B {} Pixel y-coordinate * 2".format(a + 616))
        lines.append("B {} Sprite".format(a + 617))
        lines.append("B {} Direction".format(a + 618))
        lines.append("B {} Jump flag".format(a + 619))
        lines.append("B {} Coordinates".format(a + 620))
        lines.append("B {} Distance jumped".format(a + 622))

        # Conveyor
        lines.append('D {} The next 4 bytes define the direction, location and length of the conveyor.'.format(a + 623))
        direction = 'left' if snapshot[a + 623] == 0 else 'right'
        p1, p2 = snapshot[a + 624:a + 626]
        x = p1 & 31
        y = p2 & 8 + (p1 & 224) // 32
        length = snapshot[a + 626]
        lines.append('B {} Conveyor direction ({}), location (x={}, y={}) and length ({})'.format(a + 623, direction, x, y, length))

        # Border colour
        lines.append('D {} The next byte specifies the border colour.'.format(a + 627))
        lines.append('B {} Border colour'.format(a + 627))
        lines.append('B {} Unused'.format(a + 628))

        # Items
        lines.append('D {} The next 25 bytes are copied to #R32885 and specify the colour and location of the items in the cavern.'.format(a + 629))
        terminated = False
        for i, addr in enumerate(range(a + 629, a + 654, 5)):
            terminated = terminated or snapshot[addr] == 255
            suffix = ''
            ab_addr = snapshot[addr + 1] + 256 * snapshot[addr + 2]
            if 23552 <= ab_addr < 24064:
                x = ab_addr % 32
                y = (ab_addr - 23552) // 32
                suffix += ' at ({},{})'.format(y, x)
            if terminated:
                suffix += ' (unused)'
            lines.append('M {},5 Item {}{}'.format(addr, i + 1, suffix))
            lines.append('B {},1'.format(addr))
            lines.append('W {},2'.format(addr + 1))
            lines.append('B {},2,1'.format(addr + 3))
        lines.append('B {} Terminator'.format(a + 654))

        # Portal
        attr = snapshot[a + 655]
        lines.append('D {} The next 37 bytes define the portal graphic and its location.'.format(a + 655))
        lines.append('D {} #UDGTABLE {{ #UDGARRAY2,{},4,2;{}-{}-1-16(portal{:02d}) }} TABLE#'.format(a + 655, attr, a + 656, a + 673, cavern_num))
        lines.append('B {},1 Attribute'.format(a + 655))
        lines.append('B {},32,8 Graphic data'.format(a + 656))
        p1, p2 = snapshot[a + 688:a + 690]
        x = p1 & 31
        y = 8 * (p2 & 1) + (p1 & 224) // 32
        lines.append('B {},4 Location (x={}, y={})'.format(a + 688, x, y))

        # Item
        attr = snapshot[a + 629]
        lines.append('D {} The next 8 bytes define the item graphic.'.format(a + 692))
        lines.append('D {0} #UDGTABLE {{ #UDG{0},{1}(item{2:02d}) }} TABLE#'.format(a + 692, attr, cavern_num))
        lines.append('B {},8 Item graphic data'.format(a + 692))

        # Air
        lines.append('D {} The next two bytes define the initial air supply in the cavern.'.format(a + 700))
        lines.append('B {} Air'.format(a + 700))

        # Horizontal guardians
        _write_horizontal_guardians(lines, snapshot, a + 702)

        # Bytes 731 and 732
        prefix = 'The next two bytes are copied to #R32987 and #R32988'
        if cavern_num == 4:
            lines.append("D {} {} and define Eugene's initial direction and pixel y-coordinate.".format(a + 731, prefix))
            lines.append('B {},1 Initial direction (down)'.format(a + 731))
            lines.append('B {},1 Initial pixel y-coordinate'.format(a + 732))
        elif cavern_num in (7, 11):
            lines.append("D {} {}; the first byte defines the Kong Beast's initial status, but the second byte is not used.".format(a + 731, prefix))
            lines.append('B {},1 Initial status (on the ledge)'.format(a + 731))
            lines.append('B {},1 Unused'.format(a + 732))
        else:
            lines.append('D {} {} but are not used.'.format(a + 731, prefix))
            lines.append('B {},2 Unused'.format(a + 731))

        # Special graphics and vertical guardians
        if cavern_num in (0, 1, 2, 4):
            if cavern_num == 4:
                lines.append('D {} The next three bytes are unused.'.format(a + 733))
                lines.append('B {},3 Unused'.format(a + 733))
            else:
                lines.append('D {} The next byte is copied to #R32989 and indicates that there are no vertical guardians in this room.'.format(a + 733))
                lines.append('B {},1 Terminator'.format(a + 733))
                lines.append('D {} The next two bytes are unused.'.format(a + 734))
                lines.append('B {},2 Unused'.format(a + 734))
            if cavern_num == 0:
                desc = 'swordfish graphic that appears in #R64512(The Final Barrier) when the game is completed (see #R36937)'
                udgarray_macro = '#UDGARRAY2,69,4,2;45792;45793;45808,70;45809,71(swordfish)'
            elif cavern_num == 1:
                desc = 'plinth graphic that appears on the Game Over screen (see #R35199)'
                udgarray_macro = '#UDGARRAY2,71,4,2;46816-46833-1-16(plinth)'
            elif cavern_num == 2:
                desc = 'boot graphic that appears on the Game Over screen (see #R35210). It also appears at the bottom of the screen next to the remaining lives when cheat mode is activated (see #R34608)'
                udgarray_macro = '#UDGARRAY2,71,4,2;47840-47857-1-16(boot)'
            else:
                desc = 'Eugene graphic'
                udgarray_macro = '#UDGARRAY2,23,4,2;49888-49905-1-16(eugene)'
            lines.append('D {} The next 32 bytes define the {}.'.format(a + 736, desc))
            lines.append('D {} #UDGTABLE {{ {} }} TABLE#'.format(a + 736, udgarray_macro))
            lines.append('B {},32,8'.format(a + 736))
        else:
            _write_vertical_guardians(lines, snapshot, a + 733)
            start = a + 761
            if snapshot[start] == 255:
                lines.append('B {},1 Terminator'.format(start))
                start += 1
            unused = a + 768 - start
            lines.append('D {} The next {} bytes are unused.'.format(start, unused))
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
        lines.append('D {} The next 256 bytes are guardian graphic data.'.format(gg_addr))
        lines.append('D {} {}'.format(gg_addr, gg_table))
        lines.append('B {},256,8'.format(gg_addr))

    return '\n'.join(lines)

def get_ctl(snapshot):
    template = ''
    cft = '{}/manic_miner.cft'.format(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(cft) as f:
        for line in f:
            if not line.startswith('#'):
                template += line
    return template.format(
        sba_table=get_screen_buffer_address_table(),
        caverns=get_caverns(snapshot)
    )

def show_usage():
    sys.stderr.write("""Usage: {} manic_miner.[sna|z80|szx]

  Generate a control file for Manic Miner.
""".format(os.path.basename(sys.argv[0])))
    sys.exit(1)

def main(snapshot):
    return get_ctl(get_snapshot(snapshot))

if __name__ == '__main__':
    if len(sys.argv) != 2:
        show_usage()
    sys.stdout.write(main(sys.argv[1]))
