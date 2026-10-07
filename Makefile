SNAPSHOT = $(shell grep -Po 'SNAPSHOT=\$$MANICMINER_HOME/\K.*' .ddiffsrc)
T2S = manic_miner.t2s

MK = $(SKOOLKIT_HOME)/tools/disassembly.mk
ifeq ($(wildcard $(MK)),)
    $(error $(MK): file not found)
endif
include $(MK)
