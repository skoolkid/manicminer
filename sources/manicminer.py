# Copyright 2012, 2014-2021 Richard Dymond (rjdymond@gmail.com)
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

from skoolkit.graphics import Frame, Udg
from skoolkit.skoolhtml import HtmlWriter
from skoolkit.skoolmacro import parse_ints, parse_brackets

class ManicMinerHtmlWriter(HtmlWriter):
    def init(self):
        self.expand(self.get_section('Expand'))
        self.font = {c: self.snapshot[15360 + 8 * c:15368 + 8 * c] for c in range(32, 122)}
        self.cavern_names = {}
        for a in range(45056, 65536, 1024):
            self.cavern_names[a] = ''.join([chr(b) for b in self.snapshot[a + 512:a + 544]]).strip()
        self.cavern_frames = {}

    def expand_cframe(self, text, index, cwd):
        # #CFRAME(num,force=0)(frame=$num)
        end, num, force = parse_ints(text, index, 0, (0,), ('num', 'force'), self.fields)
        if force:
            end, frame = parse_brackets(text, end)
        else:
            frame = str(num)
        if force or num not in self.cavern_frames:
            udgs = self._get_cavern_udgs(45056 + num * 1024)
            self.handle_image(Frame(udgs, 2, name=frame))
            if not force:
                self.cavern_frames[num] = True
        return end, ''

    def cavern_name(self, cwd, address):
        return self.cavern_names[address]

    def _get_cavern_udgs(self, addr):
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
            udg_array.append([block_graphics.get(attr, bg_udg).copy() for attr in self.snapshot[a:a + 32]])
        if addr == 64512:
            # The Final Barrier (top half)
            udg_array[:8] = self.screenshot(h=8, df_addr=40960, af_addr=64512)

        # Cavern name
        name_udgs = [Udg(48, self.font[b]) for b in self.snapshot[addr + 512:addr + 544]]
        udg_array.append(name_udgs)

        return udg_array
