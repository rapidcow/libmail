/*
 * Copyright (c) 2024 Ethan Meng <ethan@rapidcow.org>
 * All rights reserved.
 * Please only use for purposes of reviewing my coding style.
 *
 * This code is solely my own effort and is not affiliated
 * with UW--Madison or related to the course content of CS300.
 */

package org.rapidcow.internet.mail;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

public final class QuotedPrinter {

    private QuotedPrinter() { };

    private static void die(int status, String message) {
        System.err.println(message);
        System.exit(status);
    }

    public static void main(String[] args) throws IOException {
        InputStream is = System.in;
        OutputStream os = System.out;
        boolean flagEncode = false;
        boolean flagDecode = false;
        boolean positional = false;
        File inFile = null;
        File outFile = null;

        for (int optind = 0; optind < args.length; ++optind) {
            if (!positional) {
                switch (args[optind]) {
                case "-e":
                    flagEncode = true;
                    continue;
                case "-d":
                    flagDecode = true;
                    continue;
                case "-o":
                    if (optind < args.length) {
                        outFile = new File(args[++optind]);
                    } else {
                        die(1, "missing argument to -o");
                    }
                    continue;
                case "--":
                    positional = true;
                    break;
                default:
                    if (args[optind].startsWith("-")) {
                        die(1, "unknown switch: \""
                            + args[optind] + "\"");
                    }
                    positional = true;
                    --optind;
                    break;
                }
            } else {
                if (inFile == null) {
                    inFile = new File(args[optind]);
                } else {
                    die(1, "extraneous argument: \""
                        + args[optind] + "\"");
                }
            }
        }

        if (!flagEncode && !flagDecode) {
            /* if you are expecting this to work like cat -
             * well -- let's just say you are mistaken :) */
            flagEncode = true;
        }

        try {
            if (inFile != null) {
                is = new FileInputStream(inFile);
            }
            if (outFile != null) {
                os = new FileOutputStream(outFile);
            }
            if (flagDecode) {
                is = new QuotedDecoder().decode(is);
            }
            if (flagEncode) {
                os = new QuotedEncoder().encode(os);
            }
            final int BUFSIZ = 16384;
            byte[] buffer = new byte[BUFSIZ];
            int bytesRead;
            while ((bytesRead = is.read(buffer, 0, BUFSIZ)) != -1) {
                os.write(buffer, 0, bytesRead);
            }
        } finally {
            if (is != System.in) {
                is.close();
            }
            if (os != System.out) {
                os.close();
            }
        }
    }

}
