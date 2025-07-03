/*
 * Copyright (c) 2024 Ethan Meng <ethan@rapidcow.org>
 * All rights reserved.
 * Please only use for purposes of reviewing my coding style.
 *
 * This code is solely my own effort and is not affiliated
 * with UW--Madison or related to the course content of CS300.
 */

package org.rapidcow.internet.mail;

import static java.nio.charset.StandardCharsets.ISO_8859_1;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.Charset;
import java.util.Objects;

/**
 * Encoder that implements RFC 2045 QP transfer encoding.
 * Java port of my encoder originally written for Python.
 *
 * @author Ethan Meng
 */
public class QuotedEncoder {

    private int maxLineLength = 80;
    private LineEnding newline = LineEnding.CRLF;
    private LineEnding linesep = null;
    private MimeQuoting quoting = MimeQuoting.EMBED_LINE;
    private boolean protect = true;

    public QuotedEncoder() { }

    private int checkLength(int length) {
        if (length < 0) {
            throw new IllegalArgumentException("negative length");
        }
        return length;
    }

    public QuotedEncoder setNewline(String marker) {
        return setNewline(LineEnding.parse(marker));
    }

    public QuotedEncoder setNewline(LineEnding marker) {
        newline = marker;
        if (linesep == null) linesep = marker;
        return this;
    }

    public QuotedEncoder setCanonicalNewline(String marker) {
        return setCanonicalNewline(LineEnding.parse(marker));
    }

    public QuotedEncoder setCanonicalNewline(LineEnding marker) {
        linesep = marker;
        return this;
    }

    public QuotedEncoder setLineLength(int length) {
        maxLineLength = checkLength(length);
        return this;
    }

    public QuotedEncoder setQuoting(String style) {
        return setQuoting(MimeQuoting.parse(style));
    }

    public QuotedEncoder setQuoting(MimeQuoting style) {
        quoting = style;
        return this;
    }

    public QuotedEncoder ensureNewline(boolean safe) {
        protect = safe;
        return this;
    }

    public LineEnding getNewline() {
        return newline;
    }

    public LineEnding getCanonicalNewline() {
        return linesep == null ? newline : linesep;
    }

    public boolean ensuresNewline() {
        return protect;
    }

    public int getLineLength() {
        return maxLineLength;
    }

    public MimeQuoting getQuoting() {
        return quoting;
    }

    public String encodeText(String text) {
        return encodeText(text, ISO_8859_1);
    }

    public String encodeText(String text, Charset charset) {
        byte[] data = text.getBytes(charset);
        /* QP-encoding is 8-bit clean.  Decoding with ASCII should suffice;
         * though using latin-1 is just being extra cautious here. */
        return new String(encode(data), ISO_8859_1);
    }

    public byte[] encode(byte[] data) {
        ByteArrayOutputStream file = new ByteArrayOutputStream();
        try (OutputStream wrapper = encode(file)) {
            wrapper.write(data);
        } catch (IOException exc) {
            throw new IllegalStateException(
                "ByteArrayOutputStream threw IOException", exc
            );
        }
        return file.toByteArray();
    }

    public OutputStream encode(OutputStream file) {
        byte[] newline = this.newline.getSequence();
        byte[] linesep = newline;
        if (this.linesep != null) {
            linesep = this.linesep.getSequence();
        }
        return new EncodingStream(file, newline, linesep, maxLineLength, quoting, protect);
    }

    private static class EncodingStream extends OutputStream {
        private final OutputStream file;
        private final byte[]       newline;
        private final byte[]       linesep;
        private final int          linelen;
        private final MimeQuoting  quoting;
        private final boolean      protect;

        private byte[] current = new byte[2];
        private int columnOffset = 0;
        private int currentCount = 0;
        private boolean safe = false;
        private boolean closed = false;

        private static final byte SPACE = ' '; // whitespace
        private static final byte HTAB = '\t';
        private static final byte TILDE = '~'; // the last printable ASCII
        private static final byte ESCAPE = '='; // escape char itself

        private static final byte[] SOFTSEP = new byte[] {'='};

        private EncodingStream(
            OutputStream file, byte[] newline, byte[] linesep,
            int maxColumnLen, MimeQuoting quoting, boolean protect
        ) {
            this.file = file;
            this.newline = newline;
            this.linesep = linesep;
            this.linelen = maxColumnLen;
            this.quoting = quoting;
            this.protect = protect;
        }

        private void rotateBuffer(int n) {
            for (int i = n; i < currentCount; ++i) {
                current[i - n] = current[i];
            }
            currentCount -= n;
        }

        private void pushToBuffer(byte octet) {
            current[currentCount++] = octet;
        }

        private boolean isNewline() {
            for (int i = 0; i < this.newline.length; ++i) {
                if (current[i] != this.newline[i]) {
                    return false;
                }
            }
            return true;
        }

        @Override
        public void write(int octet) throws IOException {
            write(new byte[] {(byte) octet}, 0, 1);
        }

        @Override
        public void write(byte[] buffer, int offset, int length) throws IOException {
            Objects.checkFromIndexSize(length, offset, buffer.length);
            byte[] quote;
            boolean inLine;
            while (offset < length) {
                pushToBuffer(buffer[offset++]);
                if (currentCount == current.length) {
                    if (current[0] == '\r' || current[0] == '\n') {
                        if (isNewline()) {
                            /* Only embed the newline itself if not EMBED_LINE
                             * or higher (i.e. EMBED_NONE only) */
                            if (this.quoting == MimeQuoting.EMBED_NONE) {
                                for (byte octet : this.linesep) {
                                    file.write(encodeByte(octet, false));
                                }
                                file.write(SOFTSEP);
                            }
                            file.write(this.linesep);
                            rotateBuffer(this.newline.length);
                            safe = true;
                        } else {
                            file.write(encodeByte(current[0], false));
                            file.write(SOFTSEP);
                            file.write(this.linesep);
                            rotateBuffer(1);
                            safe = false;
                        }
                        columnOffset = 0;
                        continue;
                    }
                    inLine = current[1] == '\r' || current[1] == '\n';
                    quote = encodeByte(current[0], inLine);
                    /* Always flush pre-emptively -- if we flush when it is too late,
                     * it's probably not preventable anyways (i.e. mime max length
                     * essentially equal to length of line sep) */
                    if (columnOffset + quote.length + (inLine ? 1 : 0) >= linelen) {
                        file.write(SOFTSEP);
                        file.write(this.linesep);
                        columnOffset = 0;
                    }
                    file.write(quote);
                    rotateBuffer(1);
                    safe = false;
                    /* Now that we know this line won't end any time soon, if
                     * there is not enough space for a soft wrap, flush too */
                    columnOffset += quote.length;
                }
            }
        }

        @Override
        public void flush() throws IOException {
            file.flush();
        }

        @Override
        public void close() throws IOException {
            if (!closed) {
                try {
                    if (currentCount >= this.newline.length && isNewline()) {
                        file.write(this.linesep);
                        rotateBuffer(this.newline.length);
                        safe = true;
                    }
                    for (int i = 0; i < currentCount; ++i) {
                        file.write(encodeByte(current[i], i + 1 < currentCount));
                    }
                    if (!safe && this.protect) {
                        file.write(SOFTSEP);
                        file.write(this.linesep);
                    }
                } finally {
                    file.close();
                    closed = true;
                }
            }
        }

        private byte[] encodeByte(byte octet, boolean inLine) {
            if (embed(octet, inLine)) {
                return new byte[] {octet};
            }
            byte[] output = new byte[3];
            output[0] = '=';
            for (int i = 0; i < 2; ++i) {
                int digit = octet & 0xf;
                int hexDigit = digit < 10 ? '0' + digit : 'A' + (digit - 10);
                output[2 - i] = (byte) hexDigit;
                octet >>= 4;
            }
            return output;
        }

        private boolean embed(byte octet, boolean inLine) {
            if (octet < SPACE || octet == ESCAPE || TILDE < octet) {
                /* control characters & escape char are always encoded.
                 * (that includes CRLF; if they were to be
                 * embedded they wouldn't be passed here.) */
                if (octet != HTAB) {
                    return false;
                }
                /* tabs are encoded if disallowed by EMBED_PRINTABLE
                 * OR we are the last character (RFC 2045 6.7 Rule 3) */
                return inLine && quoting != MimeQuoting.EMBED_PRINTABLE;
            }
            /* spaces are encoded if disallowed by EMBED_VISIBLE
             * OR we are the last character (RFC 2045 6.7 Rule 3) */
            if (octet == SPACE) {
                return inLine && quoting != MimeQuoting.EMBED_VISIBLE;
            }
            /* the survivors are now embedded unless
             * disallowed by EMBED_NONE */
            return quoting != MimeQuoting.EMBED_NONE;
        }
    }

}
