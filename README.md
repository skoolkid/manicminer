Manic Miner disassembly
=======================

A disassembly of the [Spectrum](https://en.wikipedia.org/wiki/ZX_Spectrum)
version of [Manic Miner](https://en.wikipedia.org/wiki/Manic_Miner), created
using [SkoolKit](https://skoolkit.ca).

Decide which number base you prefer and then click the corresponding link below
to browse the latest release:

* [Manic Miner disassembly](https://skoolkid.github.io/manicminer/) (hexadecimal; mirror [here](https://skoolkid.gitlab.io/manicminer/))
* [Manic Miner disassembly](https://skoolkid.github.io/manicminer/dec/) (decimal; mirror [here](https://skoolkid.gitlab.io/manicminer/dec/))

To build the current development version of the disassembly, first obtain the
development version of [SkoolKit](https://github.com/skoolkid/skoolkit). Then:

    $ skool2html.py sources/mm.skool

To build an assembly language source file that can be fed to an assembler:

    $ skool2asm.py sources/mm.skool > mm.asm
