/*
 * Copyright (c) 2024 Ethan Meng <ethan@rapidcow.org>
 * All rights reserved.
 */

package org.rapidcow.internet.mail;

import static java.nio.charset.StandardCharsets.ISO_8859_1;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.Charset;
import java.util.Objects;

public class QuotedDecoder {

    private boolean ignoreBadEscape = false;
    private boolean ignoreEighthBit = false;
    private LineEnding newline = LineEnding.CRLF;
    private LineEnding linesep = null;

    public QuotedDecoder() { }

    public String decodeText(String text) {
        return decodeText(text, ISO_8859_1);
    }

    public String decodeText(String text, Charset charset) {
        byte[] data = text.getBytes(ISO_8859_1);
        data = decode(data);
        return new String(data, charset);
    }

    public byte[] decode(byte[] data) {
        ByteArrayInputStream file = new ByteArrayInputStream(data);
        try (InputStream wrapper = decode(file)) {
            return wrapper.readAllBytes();
        } catch (IOException exc) {
            /* should never happen */
            throw new IllegalStateException(
                "ByteArrayInputStream threw IOException", exc
            );
        }
    }

    public InputStream decode(InputStream file) {
        return new DecodingStream(file);
    }

    private static class DecodingStream extends InputStream {
        private InputStream file;
        private byte[] current = new byte[3];
        private int currentCount = 0;

        private static final byte ESCAPE = '='; // escape char itself

        private DecodingStream(InputStream file) {
            this.file = file;
        }

        private void rotateBuffer(int n) {
            for (int i = n; i < currentCount; ++i) {
                current[i - n] = current[i];
            }
            currentCount -= n;
        }

        @Override
        public int read() throws IOException {
            byte[] buffer = new byte[1];
            return read(buffer, 0, 1) == -1 ? -1 : buffer[0];
        }

        @Override
        public int read(byte[] buffer, int offset, int length) throws IOException {
            Objects.checkFromIndexSize(offset, length, buffer.length);
            int left = length;
            boolean eof = false;
            while (left > 0) {
                int bytesRead = file.read(current, currentCount, 3 - currentCount);
                if (bytesRead < 0) {
                    eof = true;
                    break;
                }
                currentCount += bytesRead;
                for (int i = 0; i < currentCount && left > 0; ++i) {
                    buffer[offset++] = current[i];
                    --left;
                }
                rotateBuffer(currentCount);
            }
            return length == left && eof ? -1 : length - left;
        }

    }

}
