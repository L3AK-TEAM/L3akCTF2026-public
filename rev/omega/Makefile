# Omega - PRX challenge build.
#
# src/ is split by execution domain:
#   src/host/   native code (CC):  the PRISM VM core (host/vm) plus two
#               front-ends -- prismvm (standalone) and executor (production).
#   src/guest/  emulated code (JOBCC): jobs, the in-VM verifier, the SHA-256
#               unit, and abi/ (the linker script + syscall header every guest
#               links against).
#   src/tools/  build-time codegen (python): obfuscate, prism, elf2prx, etc.

# --- Host VM toolchain -----------------------------------------------------
CC      ?= cc
CFLAGS  ?= -O2 -Wall -Wextra -std=c11
STRIP   ?= strip

# --- Layout ----------------------------------------------------------------
HOST_DIR  = src/host
BUILD_DIR = build
VM_DIR    = $(HOST_DIR)/vm
GUEST_DIR = src/guest
ABI_DIR   = $(GUEST_DIR)/abi
JOBS_DIR  = $(GUEST_DIR)/jobs
TOOLS     = src/tools
OUT       = out

CFLAGS  += -I$(HOST_DIR) -I$(VM_DIR)

CFLAGS  += -Werror=mismatched-dealloc -Werror=use-after-free

# --- MIPS cross-toolchain for PRX job binaries -----------------------------
CROSS   ?= mips-linux-gnu-
JOBCC    = $(CROSS)gcc

# --- Host VM core (src/host/vm) --------------------------------------------
# cpu / memory / loader / syscalls -- the reusable emulator, no front-end.
VM_SRCS = $(wildcard $(VM_DIR)/*.c)
VM_OBJS = $(patsubst $(VM_DIR)/%.c,$(OUT)/%.o,$(VM_SRCS))

# Host support object (src/host/xalloc.c).
SUPPORT_OBJS = $(OUT)/xalloc.o

# Host binaries: two front-ends over the same VM core.
PRISMVM_BIN  = $(OUT)/prismvm    # standalone driver
EXECUTOR_BIN = $(OUT)/executor   # production verify-then-run

# Deploy-only: the per-connection jail entrypoint (build/run.c).
RUN_BIN      = $(OUT)/run

# -EL drives little-endian output (prism.ld omits OUTPUT_FORMAT on purpose);
# -mfp32 is required to pair with -march=mips1 on this toolchain.
JOBCFLAGS  = -static -nostdlib -nostartfiles -ffreestanding -fno-builtin \
             -march=mips1 -mfp32 -mabi=32 -EL -mno-abicalls -fno-pic -G0 \
             -fno-stack-protector -fomit-frame-pointer -O1 \
             -I$(ABI_DIR)
JOBLDFLAGS = -Wl,-T,$(ABI_DIR)/prism.ld \
             -Wl,-z,max-page-size=0x1000 -Wl,-z,noseparate-code \
             -Wl,--build-id=none -Wl,--no-dynamic-linker

ELF2PRX = python3 $(TOOLS)/elf2prx.py
BIN2C   = python3 $(TOOLS)/bin2c.py

# --- Targets ---------------------------------------------------------------
all: $(PRISMVM_BIN) hello echo verifier executor run

prismvm: $(PRISMVM_BIN)

# Standalone VM driver.
$(PRISMVM_BIN): $(VM_OBJS) $(OUT)/prismvm.o $(SUPPORT_OBJS)
	$(CC) $(CFLAGS) -o $@ $^

# VM core objects.
$(OUT)/%.o: $(VM_DIR)/%.c $(VM_DIR)/prismvm.h $(VM_DIR)/prism.h | $(OUT)
	$(CC) $(CFLAGS) -c -o $@ $<

# Host support + front-end objects (explicit rules: their sources live in
# src/host, not src/host/vm, so they don't match the VM core pattern above).
$(OUT)/xalloc.o: $(HOST_DIR)/xalloc.c $(HOST_DIR)/xalloc.h $(HOST_DIR)/compiler.h | $(OUT)
	$(CC) $(CFLAGS) -c -o $@ $<

$(OUT)/prismvm.o: $(HOST_DIR)/prismvm.c $(VM_DIR)/prismvm.h | $(OUT)
	$(CC) $(CFLAGS) -c -o $@ $<

# Jobs: C -> ELF -> PRX (MAC left zeroed; e_flags = 0).
hello: $(OUT)/hello_world.prx
echo:  $(OUT)/echo.prx

$(OUT)/hello_world.elf: $(JOBS_DIR)/hello_world/main.c $(ABI_DIR)/prism.ld | $(OUT)
	$(JOBCC) $(JOBCFLAGS) $(JOBLDFLAGS) -o $@ $<

$(OUT)/echo.elf: $(JOBS_DIR)/echo/main.c $(ABI_DIR)/prism.ld | $(OUT)
	$(JOBCC) $(JOBCFLAGS) $(JOBLDFLAGS) -o $@ $<

verifier: $(OUT)/verifier.prx

$(OUT)/verifier.elf: $(GUEST_DIR)/verifier.c $(GUEST_DIR)/sha256.c $(GUEST_DIR)/sha256.h \
                     $(ABI_DIR)/prism.ld | $(OUT)
	$(JOBCC) $(JOBCFLAGS) -I$(GUEST_DIR) $(JOBLDFLAGS) -o $@ \
	    $(GUEST_DIR)/verifier.c $(GUEST_DIR)/sha256.c

# ELF -> PRX. Re-encodes .text to PRISM leaves e_mac/e_flags zeroed by default.
$(OUT)/%.prx: $(OUT)/%.elf $(TOOLS)/elf2prx.py $(TOOLS)/prx_mac.py $(TOOLS)/prism.py
	$(ELF2PRX) $< -o $@

executor: $(EXECUTOR_BIN)

# Embed the verifier PRX bytes into a C header for the executor to load in-process.
$(OUT)/verifier_prx.h: $(OUT)/verifier.prx $(TOOLS)/bin2c.py | $(OUT)
	$(BIN2C) $(OUT)/verifier.prx -o $@ --symbol verifier_prx

$(OUT)/executor.o: $(HOST_DIR)/executor.c $(OUT)/verifier_prx.h $(VM_DIR)/prismvm.h | $(OUT)
	$(CC) $(CFLAGS) -I$(OUT) -c -o $@ $<

$(EXECUTOR_BIN): $(VM_OBJS) $(OUT)/executor.o $(SUPPORT_OBJS)
	$(CC) $(CFLAGS) -o $@ $^

run: $(RUN_BIN)

$(RUN_BIN): $(BUILD_DIR)/run.c | $(OUT)
	$(CC) $(CFLAGS) -D_GNU_SOURCE -o $@ $<

# Sign a job's PRX with the deploy secret from build/.env.
$(OUT)/%.signed.prx: $(OUT)/%.elf $(TOOLS)/elf2prx.py $(TOOLS)/prx_mac.py $(TOOLS)/prism.py build/.env
	@SECRET=$$(sed -n 's/^SECRET=//p' build/.env); \
	$(ELF2PRX) $< -o $@ --sign-secret 0x$$SECRET

sign: $(OUT)/hello_world.signed.prx $(OUT)/echo.signed.prx

# --- Distribution handout ---------------------------------
# The player handout is 4 files: the executor binary, the echo job signed two
# ways, and the hand-maintained README. echo.remote.prx is signed with the REAL
# deploy key (build/.env) so it runs on the server; echo.local.prx is signed
# with the throwaway key the README documents for `SECRET=... ./executor`.
DIST            = dist
DIST_SECRET     = 00112233445566778899aabbccddeeff

dist: $(DIST)/executor $(DIST)/echo.remote.prx $(DIST)/echo.local.prx

# Strip symbols off the handout executor -- it's a rev target, don't leak names.
$(DIST)/executor: $(EXECUTOR_BIN)
	@mkdir -p $(@D)
	cp $< $@
	$(STRIP) $@

# Remote job: signed with the real deploy key from build/.env.
$(DIST)/echo.remote.prx: $(OUT)/echo.elf $(TOOLS)/elf2prx.py $(TOOLS)/prx_mac.py $(TOOLS)/prism.py build/.env
	@mkdir -p $(@D)
	@SECRET=$$(sed -n 's/^SECRET=//p' build/.env); \
	$(ELF2PRX) $< -o $@ --sign-secret 0x$$SECRET

# Local job: signed with the throwaway key documented in dist/README.md.
$(DIST)/echo.local.prx: $(OUT)/echo.elf $(TOOLS)/elf2prx.py $(TOOLS)/prx_mac.py $(TOOLS)/prism.py
	@mkdir -p $(@D)
	$(ELF2PRX) $< -o $@ --sign-secret 0x$(DIST_SECRET)

# Smoke test: verification happens inside the VM, so only validly-signed jobs
# run. Exercises both jobs plus the rejection path. The executor has no env file
# in the repo root (its fallback is ./.env), so feed it the key via $SECRET --
# the same path the handout README documents.
check: export SECRET := $(shell sed -n 's/^SECRET=//p' build/.env)
check: sign verifier executor
	@echo '[check] signed hello:'; \
	./$(EXECUTOR_BIN) $(OUT)/hello_world.signed.prx
	@echo '[check] signed echo:'; \
	printf 'ping\n/quit\n' | ./$(EXECUTOR_BIN) $(OUT)/echo.signed.prx 2>/dev/null | grep -q goodbye \
	    && echo '  [+] echo verified and ran' || { echo '  [-] echo FAILED'; exit 1; }
	@echo '[check] unsigned hello (must be refused):'; \
	if ./$(EXECUTOR_BIN) $(OUT)/hello_world.prx >/dev/null 2>&1; then \
	    echo '  [-] unsigned job was ACCEPTED'; exit 1; \
	else echo '  [+] correctly refused'; fi

$(OUT):
	mkdir -p $(OUT)

clean:
	rm -rf $(OUT)

.PHONY: all prismvm hello echo verifier executor run sign dist check clean
