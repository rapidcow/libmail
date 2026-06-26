/*
 * Copyright (c) 2024 Ethan Meng <ethan@rapidcow.org>
 * All rights reserved.
 */

package org.rapidcow.internet.mail;

import static java.nio.charset.StandardCharsets.US_ASCII;

public enum LineEnding {

    CRLF("\r\n"),
    LF("\n"),
    CR("\r");

    private final String marker;

    private LineEnding(String marker) {
        this.marker = marker;
    }

    public String getMarker() {
        return this.marker;
    }

    public byte[] getSequence() {
        return this.marker.getBytes(US_ASCII);
    }

    public int length() {
        return marker.length();
    }

    public static LineEnding parse(String name) {
        switch (name.toUpperCase()) {
        case "CRLF":
        case "DOS":
        case "\r\n":
            return CRLF;
        case "LF":
        case "UNIX":
        case "\n":
            return LF;
        case "CR":
        case "MAC":
        case "\r":
            return CR;
        }
        throw new IllegalArgumentException(name);
    }

}
