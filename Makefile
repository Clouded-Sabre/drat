### Directory definitions ###
SRCDIR=src
OUTDIR=out
INCDIR=include

### Compiler definition ###
CC := gcc

override CFLAGS += \
-std=c99 \
-D _GNU_SOURCE \
-Werror \
-Wall \
-Wextra \
-Wno-incompatible-pointer-types \
-Wno-multichar \
-Wno-unused-variable \
-Wno-unused-parameter \
-Wno-missing-field-initializers \
-Wno-deprecated-non-prototype \
-Wno-unused-but-set-variable \
-I./$(INCDIR)

### Linker definition ###
LD := gcc
override LDFLAGS += # Nothing

### On macOS, include <argp.h> from Homebrew package `argp-standalone`
#ifneq ($(OS),Windows_NT)
#	ifeq ($(shell uname -s),Darwin)
#		override CFLAGS  += -I/usr/local/Cellar/argp-standalone/1.3/include/
#		override LDFLAGS += -L/usr/local/Cellar/argp-standalone/1.3/lib/ -largp
#	endif
#endif
ifneq ($(OS),Windows_NT)
    ifeq ($(shell uname -s),Darwin)
        # Detect Architecture
        ARCH := $(shell uname -m)
        
        ifeq ($(ARCH),arm64)
            # Apple Silicon Paths
            BREW_PREFIX := /opt/homebrew
        else
            # Intel Mac Paths
            BREW_PREFIX := /usr/local
        endif

        # Use wildcard to find the actual version installed so we don't hardcode '1.3'
        ARGP_PATH := $(firstword $(wildcard $(BREW_PREFIX)/Cellar/argp-standalone/*/))
        
        ifneq ($(ARGP_PATH),)
            override CFLAGS  += -I$(ARGP_PATH)include/
            override LDFLAGS += -L$(ARGP_PATH)lib/ -largp
        else
            # Fallback for non-standard or direct brew prefix installs
            override CFLAGS  += -I$(BREW_PREFIX)/include
            override LDFLAGS += -L$(BREW_PREFIX)/lib -largp
        endif
    endif
endif

### Source paths ###
HEADERS		:= $(shell find $(SRCDIR) $(INCDIR) -name '*.h')
SOURCES		:= $(shell find $(SRCDIR) $(INCDIR) -name '*.c')
CMD_SRCS	:= $(wildcard $(SRCDIR)/commands/*.c)
BIN_SRCS	:= $(wildcard $(SRCDIR)/*.c)

### Target paths ###
GCHS		:= $(HEADERS:%.h=$(OUTDIR)/%.gch)
OBJECTS		:= $(SOURCES:%.c=$(OUTDIR)/%.o)
COMMANDS	:= $(CMD_SRCS:$(SRCDIR)/commands/%.c=%)
BINARIES	:= $(BIN_SRCS:$(SRCDIR)/%.c=%)

### Targets ###

.DEFAULT_GOAL := all

$(GCHS): $(OUTDIR)/%.gch: %.h
	@echo "GCHS +++ $< +++ $@"
	@[ -d $(@D) ] || (mkdir -p $(@D) && echo "Created directory \`$(@D)\`.")
	$(CC) $(CFLAGS) -c "$<" -o "$@"
	@echo

$(OBJECTS): $(OUTDIR)/%.o: %.c $(HEADERS)
	@echo "OBJECTS +++ $< +++ $@"
	@[ -d $(@D) ] || (mkdir -p $(@D) && echo "Created directory \`$(@D)\`.")
	$(CC) $(CFLAGS) -c "$<" -o "$@"
	@echo

# Make `<command_name>` an alias of `out/commands/<command_name>.o`
.PHONY: $(COMMANDS)
$(COMMANDS): %: $(OUTDIR)/$(SRCDIR)/commands/%.o

$(BINARIES): %: $(OUTDIR)/$(SRCDIR)/%.o $(OBJECTS)
	@echo "BINARIES +++ $< +++ $@"
	$(LD) $^ $(LDFLAGS) -o $@
	@echo

### Meta-targets ###

.PHONY: headers
headers: $(GCHS)

.PHONY: commands
commands: $(COMMANDS)

.PHONY: binaries
binaries: $(BINARIES)

.PHONY: clean
clean:
	rm -rf $(BINARIES) $(OUTDIR)

.PHONY: all
all: headers commands binaries

##

.PHONY: docs
docs:
	(cd docs && make html)

.PHONY: clean-docs
clean-docs:
	(cd docs && make clean)
