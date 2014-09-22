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

def _write_guardians(lines, snapshot, start, g_type):
    term = start + 28
    for addr in range(start, start + 28, 7):
        if snapshot[addr] == 255:
            term = addr
            break
    num_guardians = (term - start) // 7
    g_type_lower = g_type.lower()
    if num_guardians:
        lines.append('D {} The next {} bytes define the {} guardian{}.'.format(start, num_guardians * 7, g_type_lower, 's' if num_guardians > 1 else ''))
        addr = start
        if num_guardians > 1:
            for i in range(num_guardians):
                suffix = ' (unused)' if snapshot[addr] == 0 else ''
                lines.append('B {},7 {} guardian {}{}'.format(addr, g_type, i + 1, suffix))
                addr += 7
        else:
            lines.append('B {},7 {} guardian'.format(addr, g_type))
            addr += 7
    else:
        lines.append('D {} There are no {} guardians in this room.'.format(start, g_type_lower))
    if num_guardians < 4:
        lines.append('B {},1 Terminator'.format(term))
        return term + 1
    return term

def get_caverns(snapshot):
    lines = []

    for a in range(45056, 65536, 1024):
        cavern_num = a // 1024 - 44
        cavern = snapshot[a:a + 1024]
        cavern_name = ''.join([chr(b) for b in cavern[512:544]]).strip()
        lines.append('b {} {}'.format(a, cavern_name))
        lines.append('D {} Used by the routine at #R34436.'.format(a))
        lines.append('D {0} #UDGTABLE {{ #CALL:cavern({0}) }} TABLE#'.format(a))
        lines.append('D {} The first 512 bytes are the attributes that define the layout of the cavern.'.format(a))
        lines.append('B {},512,16 Attributes'.format(a))

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
        lines.append('D {} The next 25 bytes specify the colour and location of the items in the cavern.'.format(a + 629))
        terminated = False
        for i, addr in enumerate(range(a + 629, a + 654, 5)):
            attr = snapshot[addr]
            if attr == 255:
                terminated = True
            suffix = ' (unused)' if terminated or attr == 0 else ''
            lines.append('B {},5 Item {}{}'.format(addr, i + 1, suffix))
        lines.append('B {}'.format(a + 654))

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
        end = _write_guardians(lines, snapshot, a + 702, 'Horizontal')

        # Special graphics and vertical guardians
        if cavern_num in (0, 1, 2, 4):
            lines.append('B {},{},16 Unused'.format(end, a + 736 - end))
            if cavern_num == 0:
                desc = 'swordfish graphic that appears in The Final Barrier when the game is completed'
            elif cavern_num == 1:
                desc = 'plinth graphic that appears on the Game Over screen (see #R35199)'
            elif cavern_num == 2:
                desc = 'boot graphic that appears on the Game Over screen (see #R35210). It also appears at the bottom of the screen next to the remaining lives when cheat mode is activated (see #R34608)'
            else:
                desc = 'Eugene graphic'
            lines.append('D {} The next 32 bytes define the {}.'.format(a + 736, desc))
            lines.append('D {} #UDGTABLE {{ #UDGARRAY2,56,4,2;{}-{}-1-16(special{}) }} TABLE#'.format(a + 736, a + 736, a + 753, cavern_num))
            lines.append('B {},32,16'.format(a + 736))
        else:
            lines.append('B {},{},16 Unused'.format(end, a + 733 - end))
            end = _write_guardians(lines, snapshot, a + 733, 'Vertical')
            lines.append('B {},{},16 Unused'.format(end, a + 768 - end))

        # Guardian graphic data
        gg_addr = a + 768
        gg_table = '#UDGTABLE { '
        macros = []
        for addr in range(gg_addr, gg_addr + 256, 32):
            img_fname = '{}_guardian{}'.format(cavern_name.lower().replace(' ', '_'), (addr & 224) // 32)
            macros.append('#UDGARRAY2,56,4,2;{}-{}-1-16({})'.format(addr, addr + 17, img_fname))
        gg_table += ' | '.join(macros) + ' } TABLE#'
        lines.append('D {} The next 256 bytes are guardian graphic data.'.format(gg_addr))
        lines.append('D {} {}'.format(gg_addr, gg_table))
        lines.append('B {},256,16'.format(gg_addr))

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
