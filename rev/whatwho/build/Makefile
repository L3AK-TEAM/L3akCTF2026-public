PYTHON ?= python3
CC ?= cc

OUT := .artifacts
DIST := ../dist

CFLAGS := -std=c17 -O2 -Wall -Wextra -Werror -Wpedantic \
	-fstack-protector-strong -D_FORTIFY_SOURCE=2 -fPIE -Isrc
HARDENED_LDFLAGS := -pie -Wl,-z,relro,-z,now
ifeq ($(shell uname -s),Darwin)
LOCAL_LDFLAGS :=
else
LOCAL_LDFLAGS := $(HARDENED_LDFLAGS)
endif

.PHONY: all cartridge local release dist image run clean

all: local

cartridge: $(OUT)/vault.wwc

$(OUT)/vault.wwc: tools/build_cartridge.py
	@mkdir -p $(OUT)
	$(PYTHON) tools/build_cartridge.py -o $@

local: $(OUT)/whatwho-local $(OUT)/vault.wwc

$(OUT)/whatwho-local: src/main.c src/cartridge.c src/vm.c src/whatwho.h
	@mkdir -p $(OUT)
	$(CC) $(CFLAGS) src/main.c src/cartridge.c src/vm.c \
		$(LOCAL_LDFLAGS) -o $@

# Native Ubuntu x86-64 release.
$(OUT)/whatwho: src/main.c src/cartridge.c src/vm.c src/whatwho.h
	@mkdir -p $(OUT)
	$(CC) $(CFLAGS) -fvisibility=hidden \
		src/main.c src/cartridge.c src/vm.c \
		$(HARDENED_LDFLAGS) -Wl,--build-id=none -o $@
	strip --strip-all $@

release: $(OUT)/whatwho $(OUT)/vault.wwc
	@mkdir -p $(DIST)
	rm -f $(DIST)/what-who.zip $(DIST)/README.txt
	install -m 0755 $(OUT)/whatwho $(DIST)/whatwho
	install -m 0444 $(OUT)/vault.wwc $(DIST)/vault.wwc
	file $(DIST)/whatwho

# Cross-build Linux amd64 artifacts through Docker.
dist: $(OUT)/vault.wwc
	rm -rf $(OUT)/export
	docker buildx build --pull=false --platform linux/amd64 \
		--target artifacts --output type=local,dest=$(OUT)/export .
	@mkdir -p $(DIST)
	rm -f $(DIST)/what-who.zip $(DIST)/README.txt
	install -m 0755 $(OUT)/export/whatwho $(DIST)/whatwho
	install -m 0444 $(OUT)/export/vault.wwc $(DIST)/vault.wwc
	file $(DIST)/whatwho

image:
	docker build --pull=false --platform linux/amd64 \
		-t what-who:latest .

run: image
	docker run --rm --platform linux/amd64 \
		-p 28451:28451 \
		-e 'WHATWHO_FLAG=L3AK{wh4t_4sks_wh0_4nsw3rs}' \
		what-who:latest

clean:
	rm -rf $(OUT)
	rm -f $(DIST)/what-who.zip $(DIST)/README.txt
	rm -f $(DIST)/whatwho $(DIST)/vault.wwc
