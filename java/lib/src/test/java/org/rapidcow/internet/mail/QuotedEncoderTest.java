package org.rapidcow.internet.mail;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class QuotedEncoderTest {
    @Test void hello() {
        String coder = new QuotedEncoder()
                .setNewline("\r\n")
                .setCanonicalNewline("\n")
                .setLineLength(100)
                .setQuoting(MimeQuoting.EMBED_PRINTABLE)
                .ensureNewline(true)
                .encodeText("Hello\r\nworld\r\n\n\n\r\n");
        assertEquals(coder, "Hello\nworld\n=0A=\n=0A=\n\n");
    }
}
