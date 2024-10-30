/*
 * Copyright (c) 2024 Ethan Meng <ethan@rapidcow.org>
 * All rights reserved.
 */

package org.rapidcow.internet.mail;

public enum MimeQuoting {

    EMBED_ALL,
    EMBED_LINE,
    EMBED_PRINTABLE,
    EMBED_VISIBLE,
    EMBED_NONE;

    public static MimeQuoting parse(String option) {
        switch (option.toUpperCase()) {
        case "ALL":
        case "EMBED_ALL":
        case "QUOTE_TEXT":
            return EMBED_ALL;
        case "LINE":
        case "EMBED_LINE":
        case "QUOTE_BINARY":
            return EMBED_LINE;
        case "PRINTABLE":
        case "EMBED_PRINTABLE":
        case "QUOTE_CONTROL":
            return EMBED_PRINTABLE;
        case "VISIBLE":
        case "EMBED_VISIBLE":
        case "QUOTE_INVISIBLE":
            return EMBED_VISIBLE;
        case "NONE":
        case "EMBED_NONE":
        case "QUOTE_ALL":
            return EMBED_NONE;
        }
        throw new IllegalArgumentException(option);
    }

}
