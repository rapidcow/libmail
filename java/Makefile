.PHONY: help lib clean
SRCDIR = lib/src/main/java/org/rapidcow/internet/mail
OUTDIR = lib/bin/main/java/org/rapidcow/internet/mail
DSTDIR = lib/bin/main/java
# Library
LSRC = $(patsubst %,$(SRCDIR)/%.java,LineEnding MimeQuoting QuotedDecoder QuotedEncoder)
LBIN = $(patsubst $(SRCDIR)/%.java,$(OUTDIR)/%.class,$(LSRC))
# Command-line Interface
ISRC = $(patsubst %,$(SRCDIR)/%.java,QuotedPrinter)
IBIN = $(patsubst $(SRCDIR)/%.java,$(OUTDIR)/%.class,$(ISRC))

JAVAC = /usr/bin/env javac
JAVADOC = /usr/bin/env javadoc
JAR = /usr/bin/env jar
JFLAGS = -Xlint:all

help:
	@echo "java port of libmail"
	@echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
	@echo "make lib     compile most things"
	@echo "make exe     compile just the printer"

doc:
	$(JAVADOC) -d public $(SRC)

lib: $(LBIN)
exe: $(IBIN)
## Enums
BIN_ENUMS = $(OUTDIR)/LineEnding.class $(OUTDIR)/MimeQuoting.class
$(OUTDIR)/LineEnding.class: $(SRCDIR)/LineEnding.java
	@-mkdir -p $(dir $@)
	$(JAVAC) $(JFLAGS) -d $(DSTDIR) $<
$(OUTDIR)/MimeQuoting.class: $(SRCDIR)/MimeQuoting.java
	@-mkdir -p $(dir $@)
	$(JAVAC) $(JFLAGS) -d $(DSTDIR) $<

## Encoder/Decoder (use enums)
BIN_QPCD = $(OUTDIR)/QuotedDecoder.class $(OUTDIR)/QuotedEncoder.class
$(OUTDIR)/QuotedEncoder.class: $(SRCDIR)/QuotedEncoder.java $(BIN_ENUMS)
	$(JAVAC) $(JFLAGS) -cp $(DSTDIR) -d $(DSTDIR) $<

$(OUTDIR)/QuotedDecoder.class: $(SRCDIR)/QuotedDecoder.java $(BIN_ENUMS)
	$(JAVAC) $(JFLAGS) -cp $(DSTDIR) -d $(DSTDIR) $<

## Entry point (uses all)
$(OUTDIR)/QuotedPrinter.class: $(SRCDIR)/QuotedPrinter.java $(BIN_QPCD)
	$(JAVAC) $(JFLAGS) -cp $(DSTDIR) -d $(DSTDIR) $<
