# -*- coding: utf-8 -*-

# Copyright 2012, 2014-2016 Richard Dymond (rjdymond@gmail.com)
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.

from skoolkit.skoolasm import AsmWriter
from skoolkit.skoolhtml import HtmlWriter, Frame, Udg
from skoolkit.skoolmacro import parse_ints, parse_image_macro

def parse_gbuf(text, index):
    # #GBUFfrom[,to]
    return parse_ints(text, index, 2, (None,))

class ManicMinerHtmlWriter(HtmlWriter):
    def init(self):
        self.font = {}
        for b, h in self.get_dictionary('Font').items():
            self.font[b] = [int(h[i:i + 2], 16) for i in range(0, 16, 2)]
        self.cavern_names = self._get_cavern_names()
        self.addr_anchor_fmt = self.get_dictionary('Game')['AddressAnchor']

    def cavern(self, cwd, address, scale=2, fname=None, x=0, y=0, w=32, h=17, guardians=1, animate=0):
        if fname is None:
            fname = self.cavern_names[address].lower().replace(' ', '_')
        img_path = self.image_path(fname, 'ScreenshotImagePath')
        if self.need_image(img_path):
            cavern_udgs = self._get_cavern_udgs(address, guardians)
            img_udgs = [cavern_udgs[i][x:x + w] for i in range(y, y + min(h, 17 - y))]
            if animate:
                direction = self.snapshot[address + 623]
                sb_addr = self.snapshot[address + 624] + 256 * self.snapshot[address + 625]
                conveyor_x = sb_addr % 32 - x
                conveyor_y = 8 * ((sb_addr - 28672) // 2048) + (sb_addr % 256) // 32 - y
                length = self.snapshot[address + 626]
                frames = self._animate_conveyor(img_udgs, direction, conveyor_x, conveyor_y, length, scale)
                self.write_animated_image(img_path, frames)
            else:
                self.write_image(img_path, img_udgs, scale=scale)
        return self.img_element(cwd, img_path)

    def expand_gbuf(self, text, index, cwd):
        end, addr_from, addr_to = parse_gbuf(text, index)
        link_text = '#N{}'.format(addr_from)
        if addr_to is not None:
            link_text += '-' + '#N{}'.format(addr_to)
        return end, '#LINK:GameStatusBuffer#{}({})'.format(addr_from, link_text)

    def expand_willy(self, text, index, cwd):
        # #WILLYcavern,x,y,sprite[,left,top,width,height,scale](fname)
        names = ('cavern', 'x', 'y', 'sprite', 'left', 'top', 'width', 'height', 'scale')
        defaults = (0, 0, 32, 17, 2)
        end, crop_rect, fname, frame, alt, params = parse_image_macro(text, index, defaults, names)
        cavern, x, y, sprite, left, top, width, height, scale = params
        cavern_addr = 45056 + 1024 * cavern
        cavern_udgs = self._get_cavern_udgs(cavern_addr)
        willy = self._get_graphic(33280 + 32 * sprite, 7)
        cavern_bg = self.snapshot[cavern_addr + 544]
        self._place_graphic(cavern_udgs, willy, x, y // 8, y % 8, cavern_bg)
        img_udgs = [cavern_udgs[i][left:left + width] for i in range(top, top + min(height, 17 - top))]
        frames = [Frame(img_udgs, scale, 0, *crop_rect, name=frame)]
        return end, self.handle_image(frames, fname, cwd, alt, 'ScreenshotImagePath')

    def _animate_conveyor(self, udgs, direction, x, y, length, scale):
        mask = 0
        delay = 10
        frame1 = Frame(udgs, scale, mask, delay=delay)
        frames = [frame1]

        if y < 0 or y >= len(udgs) or x + length < 0 or x >= len(udgs[0]):
            return frames
        min_x = max(x, 0)
        max_x = min(x + length, len(udgs[0]))
        length_t = max_x - min_x

        base_udg = prev_udg = udgs[y][min_x]
        while True:
            next_udg = prev_udg.copy()
            data = next_udg.data
            if direction:
                data[0] = (data[0] >> 2) + (data[0] & 3) * 64
                data[2] = ((data[2] << 2) & 255) + (data[2] >> 6)
            else:
                data[0] = ((data[0] << 2) & 255) + (data[0] >> 6)
                data[2] = (data[2] >> 2) + (data[2] & 3) * 64
            if next_udg.data == base_udg.data:
                break
            next_udgs = [row[:] for row in udgs]
            next_udgs[y][min_x:max_x] = [next_udg] * length_t
            frames.append(Frame(next_udgs, scale, mask, delay=delay))
            prev_udg = next_udg
        return frames

    def caverns(self, cwd):
        lines = [
            '#TABLE(default,centre,centre,,centre)',
            '{ =h No. | =h Address | =h Name | =h Teleport }'
        ]
        for cavern_num in range(20):
            address = 45056 + 1024 * cavern_num
            cavern_name = self.cavern_names[address]
            teleport_code = self._get_teleport_code(cavern_num)
            lines.append('{{ #N{0} | #N{1} | #R{1}({2}) | {3} }}'.format(cavern_num, address, cavern_name, teleport_code))
        lines.append('TABLE#')
        return ''.join(lines)

    def wall_bug_img(self, cwd, index):
        fname = 'through_the_wall{}'.format(index)
        img_path = self.image_path(fname, 'ScreenshotImagePath')
        if self.need_image(img_path):
            cavern = self._get_cavern_udgs(49152)
            x, y, sprite_index, y_delta = (
                (23, 11, 0, 5),
                (22, 12, 3, 0),
                (22, 12, 2, 4),
                (22, 13, 2, 0),
            )[index - 1]
            willy = self._get_graphic(33408 + 32 * sprite_index, 23)
            self._place_graphic(cavern, willy, x, y, y_delta, 16)
            udg_array = [row[20:28] for row in cavern[11:16]]
            self.write_image(img_path, udg_array, scale=2)
        return self.img_element(cwd, img_path)

    def ttwa_img(self, cwd, cavern, x, y, frame, fname):
        img_path = self.image_path(fname, 'ScreenshotImagePath')
        if self.need_image(img_path):
            cavern_addr = 45056 + 1024 * cavern
            cavern_udgs = self._get_cavern_udgs(cavern_addr, 0)
            willy = self._get_graphic(33280 + 32 * frame, 23)
            bg_attr = self.snapshot[cavern_addr + 544]
            self._place_graphic(cavern_udgs, willy, x, y, 0, bg_attr)
            width, height = 10, 6
            cavern_x = min(max(x - width // 2 + 1, 0), 32 - width)
            cavern_y = min(max(y - height // 2 + 1, 0), 16 - height)
            udg_array = [row[cavern_x:cavern_x + width] for row in cavern_udgs[cavern_y:cavern_y + height]]
            self.write_image(img_path, udg_array, scale=2)
        return self.img_element(cwd, img_path)

    def attribute_crash_img(self, cwd):
        img_path = self.image_path('attribute_crash', 'ScreenshotImagePath')
        if self.need_image(img_path):
            self.push_snapshot()
            self.snapshot[59102] = 2
            self.snapshot[59103] = 72
            self.snapshot[59104] = 17
            cavern = self._get_cavern_udgs(58368)
            self.pop_snapshot()
            cavern[11][17] = cavern[11][18] = Udg(15, cavern[11][15].data)
            udg_array = [row[14:22] for row in cavern[8:13]]
            self.write_image(img_path, udg_array, scale=2)
        return self.img_element(cwd, img_path)

    def _get_cavern_names(self):
        caverns = {}
        for a in range(45056, 65536, 1024):
            caverns[a] = ''.join([chr(b) for b in self.snapshot[a + 512:a + 544]]).strip()
        return caverns

    def _get_teleport_code(self, cavern_num):
        code = ''
        key = 1
        while cavern_num:
            if cavern_num & 1:
                code += str(key)
            cavern_num //= 2
            key += 1
        return code + '6'

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
            if attr in (0, 255):
                break
            sprite_index = self.snapshot[a + 4]
            if cavern_no >= 7 and cavern_no not in (9, 15):
                sprite_index |= 4
            sprite = self._get_graphic(addr + 768 + 32 * sprite_index, attr & 127)
            x, y = self._get_coords(a + 1)
            self._place_graphic(udg_array, sprite, x, y)

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
                y = (self.snapshot[a + 2] & 120) // 8
                y_delta = self.snapshot[a + 2] & 7
                x = self.snapshot[a + 3]
                self._place_graphic(udg_array, sprite, x, y, y_delta)

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
        self._place_graphic(udg_array, willy, x, y)

    def _get_cavern_udgs(self, addr, guardians=1):
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
            udg_array[:8] = self.screenshot(h=8, df_addr=40960, af_addr=64512)

        # Cavern name
        name_udgs = [Udg(48, self.font[b]) for b in self.snapshot[addr + 512:addr + 544]]
        udg_array.append(name_udgs)

        self._place_items(udg_array, addr)
        if guardians:
            self._place_guardians(udg_array, addr)
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

    def _place_graphic(self, udg_array, graphic, x, y, y_delta=0, bg_attr=None):
        if y_delta > 0:
            graphic = self._shift_graphic(graphic, y_delta)
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

class ManicMinerAsmWriter(AsmWriter):
    def expand_gbuf(self, text, index):
        end, addr_from, addr_to = parse_gbuf(text, index)
        output = '#N{}'.format(addr_from)
        if addr_to is not None:
            output += '-#N{}'.format(addr_to)
        return end, output
