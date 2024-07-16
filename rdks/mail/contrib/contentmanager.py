# XXX: not tested
# ok only tested a TEENY bit.. still nowhere near enough :(
import email.message
import rdks.mail.content.encoders as encoders
import rdks.mail.content.decoders as decoders

__all__ = ['ContentManager']

def get_cte(message):
    return '7bit' if message.policy.cte_type == '7bit' else '8bit'

def get_charset(charset):
    if charset is not None:
        charset = charset.lower()
        charset = email.charset.ALIASES.get(charset, charset)
    return charset

def reset_header(message, header, value):
    if header in message:
        message.replace_header(header, value)
    else:
        message[header] = value

def set_header(message, header, value):
    if header not in message:
        message[header] = value

def is_buffer(obj):
    try:
        memoryview(obj)
    except TypeError:
        return False
    return True

class ContentManager:
    def get_content(self, message, *args, decode=True,
                    decode_content=True, **kwds):
        if message.is_multipart():
            return self.get_multipart_content(
                message, *args, **kwds, decode=decode)
        if decode and decode_content:
            if message.get_param('charset') is not None:
                errors = 'strict' if decode is True else decode
                return self.get_text_content(message,
                    *args, **kwds, errors=errors, decode=decode_content)
        return self.get_raw_content(message,
            *args, **kwds, decode=decode_content)

    def get_multipart_content(self, message, decode=True):
        payload = message.get_payload()
        if not decode:
            return payload
        mimetype = message.get_content_type()
        if mimetype == 'message/rfc822':
            assert len(payload) == 1
            return payload[0]
        if mimetype == 'message/delivery-status':
            # XXX: is EOL translation needed?
            return b''.join(map(bytes, payload)).decode('ascii')
        return payload

    def get_text_content(self, message, *args, errors='strict', **kwds):
        charset = message.get_param('charset')
        assert charset is not None
        return (self.get_raw_content(message, *args, **kwds)
                .decode(charset, errors))

    def get_raw_content(self, message, decode=True):
        payload = message.get_payload()
        if isinstance(payload, bytes):
            bpayload = payload
        elif isinstance(payload, str):
            bpayload = payload.encode('ascii', 'surrogateescape')
        else:
            raise TypeError('expected bytes or str payload, got %s'
                            % (type(payload),))
        if not decode:
            return bpayload
        cte = message.get('Content-Transfer-Encoding', get_cte(message))
        linesep = message.policy.linesep.encode('ascii')
        maxbarelen = message.policy.max_line_length
        maxlinelen = maxbarelen + len(linesep) if maxbarelen else 0
        return self.decode_body(message, bpayload, cte,
            maxlinelen=maxlinelen, linesep=linesep)

    def set_content(self, message, content, *args,
                    description=None, disposition=None,
                    filename=None, creation_date=None,
                    modification_date=None, read_date=None,
                    size=None, cid=None, language=None, **kwds):
        # Beat set_content to be punch - I like MIME-Version
        # declared at the top :)
        if isinstance(message, email.message.EmailMessage):
            if 'MIME-Version' not in message:
                message['MIME-Version'] = '1.0'
        self.set_body_content(message, content, *args, **kwds)
        # The rest is whatever, but it's still here to be
        # somewhat compatible with Python's contentmanager.py
        if disposition is None:
            if filename is not None:
                disposition = 'attachment'
            elif not all(i is None for i in (
                    creation_date, modification_date,
                    read_date, size)):
                disposition = 'inline'
        if disposition is not None:
            reset_header(message, 'Content-Disposition', disposition)
        if filename is not None:
            message.set_param('filename', filename, replace=True,
                              header='Content-Disposition')
        if creation_date is not None:
            message.set_param('creation-date', creation_date,
                              replace=True, header='Content-Disposition')
        if modification_date is not None:
            message.set_param('modification-date', modification_date,
                              replace=True, header='Content-Disposition')
        if read_date is not None:
            message.set_param('read-date', read_date, replace=True,
                              header='Content-Disposition')
        if size is not None:
            message.set_param('size', size, replace=True,
                              header='Content-Disposition')
        if cid is not None:
            reset_header(message, 'Content-ID', cid)
        if description is not None:
            reset_header(message, 'Content-Description', description)
        if language is not None:
            reset_header(message, 'Content-Language', language)

    def set_body_content(self, message, content, mimetype=None,
                         *args, **kwds):
        # str (not really anything else)
        if isinstance(content, str):
            return self.set_text_content(
                message, str(content), mimetype, *args, **kwds,
            )
        # bytes-like object
        if is_buffer(content):
            return self.set_raw_content(
                message, bytes(content), mimetype, *args, **kwds,
            )
        # attached message
        if isinstance(content, email.message.Message):
            if content is self:
                raise ValueError("please don't embed yourself :(")
            mimetype = mimetype or 'message/rfc822'
            return self.set_multipart_content(
                message, [content], mimetype, *args, *kwds)
        # lists
        if isinstance(content, list):
            mimetype = mimetype or 'multipart/mixed'
            return self.set_multipart_content(
                message, list(content), mimetype, *args, *kwds)
        raise ValueError('content should be str-like, byte-like, '
                         'or iterables of parts, not %s'
                         % (type(content).__name__,))

    def set_multipart_content(self, message, parts, mimetype=None,
                              *, boundary=None):
        message.set_payload(parts)
        if mimetype is not None:
            reset_header(message, 'Content-Type', mimetype)
        if boundary is not None:
            message.set_boundary(boundary)

    def set_text_content(self, message, content,
                            mimetype=None, charset='utf-8', *,
                            errors='strict', **kwds):
        charset = get_charset(charset)
        return self.set_raw_content(
            message, content.encode(charset, errors),
            mimetype, charset, **kwds,
        )

    # treol=False fixeol=False - my fav version :,)
    # fixeol=False - the version I pleaded for in #121515
    # (default) - Python's current version (just ass - hmph!)
    def set_raw_content(self, message, content,
                        mimetype=None, charset=None, *,
                        cte=None, treol=None, fixeol=None,
                        linesep=None, **enc_params):
        # XXX XXX: praying that no one uses this in a try-except block....
        eff_cte = (cte if cte is not None else '7bit').lower()
        charset = get_charset(charset)
        if mimetype is None:
            # be a bit brutal if the message was multi-part
            # we don't want to mess up generator logic...
            if message.is_multipart():
                del message['Content-Type']
            if charset is not None:
                set_header(message, 'Content-Type', 'text/plain')
                message.set_param('charset', charset, replace=True)
        else:
            reset_header(message, 'Content-Type', mimetype)
            if charset is not None:
                message.set_param('charset', charset, replace=True)
        # we keep the linesep to ourselves for EOL translation.
        rfc_eol = message.policy.linesep.encode('ascii')
        enc_params['linesep'] = rfc_eol
        maxbarelen = message.policy.max_line_length
        maxlinelen = maxbarelen + len(rfc_eol) if maxbarelen else 0
        if treol is None:
            # disable treol for base64 and anything non-text by default
            treol = eff_cte != 'base64' or \
                message.get_content_maintype() != 'text'
        if fixeol is None:
            fixeol = treol
        if treol:
            # use canonical model... also for translation?
            content = encoders.treol(content, rfc_eol if linesep is None
                                     else linesep, fixeol)
        # We will not reinforce maxuserlen < policy.max_line_length
        # since it can be useful to treat policy's as an advised limit
        # and impose a global max line limit elsewhere (like the
        # smtpline option in compose.py)
        maxuserlen = enc_params.setdefault('maxlinelen', maxlinelen)
        encoded = self.encode_body(message, content, eff_cte, **enc_params)
        message.set_payload(encoded.decode('ascii', 'surrogateescape'))
        if cte is None:
            del message['Content-Transfer-Encoding']
        else:
            reset_header(message, 'Content-Transfer-Encoding', cte)
        # XXX: nothing meaningful i can return :(

    def decode_body(self, message, body, cte, *, maxlinelen, linesep, **kwds):
        decoder_name = 'decode_%s' % (cte.lower().replace('-', '_'),)
        if hasattr(self, decoder_name):
            return getattr(self, decoder_name)(message, body,
                maxlinelen=maxlinelen, linesep=linesep, **kwds)
        raise ValueError('I do not know how to decode %s' % (cte,))

    def encode_body(self, message, body, cte, *, maxlinelen, linesep, **kwds):
        encoder_name = 'encode_%s' % (cte.lower().replace('-', '_'),)
        if hasattr(self, encoder_name):
            return getattr(self, encoder_name)(message, body,
                maxlinelen=maxlinelen, linesep=linesep, **kwds)
        raise ValueError('I do not know how to encode %s' % (cte,))

    def decode_7bit(self, message, body, *, maxlinelen, linesep):
        return decoders.decode_verbatim(body,
            maxlinelen=maxlinelen, linesep=linesep,
            canonical_linesep=b'\n', ascii=True)

    def decode_8bit(self, message, body, *, maxlinelen, linesep):
        return decoders.decode_verbatim(body,
            maxlinelen=maxlinelen, linesep=linesep,
            canonical_linesep=b'\n')

    def decode_quoted_printable(self, message, body, *,
            maxlinelen, linesep):
        return decoders.decode_qp(body,
            maxlinelen=maxlinelen, linesep=linesep,
            canonical_linesep=b'\n')

    def decode_base64(self, message, body, *, maxlinelen, linesep):
        return decoders.decode_base64(body,
            maxlinelen=maxlinelen, linesep=linesep,
            canonical_linesep=b'\n')

    def encode_7bit(self, message, body, *, maxlinelen, linesep):
        return encoders.encode_verbatim(body,
            maxlinelen=maxlinelen, linesep=linesep,
            canonical_linesep=b'\n', ascii=True)

    def encode_8bit(self, message, body, *, maxlinelen, linesep):
        return encoders.encode_verbatim(body,
            maxlinelen=maxlinelen, linesep=linesep,
            canonical_linesep=b'\n')

    def encode_quoted_printable(self, message, body, *,
            maxlinelen, linesep, wrap=None, embed=None, protect=True):
        # this is purely my subjective taste... if you don't like it,
        # change it!  but make sure to respect the user's choices :)
        maintype = message.get_content_maintype()
        if wrap is None:
            # application can sometimes be partially text!
            # i'd give it the benefit of the doubt....
            wrap = maintype in {'text', 'application'}
        if embed is None:
            embed = maintype == 'text'
        return encoders.encode_qp(body,
            maxlinelen=maxlinelen, linesep=linesep,
            canonical_linesep=b'\n', wrap=wrap, embed=embed,
            protect=protect)

    def encode_base64(self, message, body, *,
            maxlinelen, linesep, chomp=False):
        return encoders.encode_base64(body,
            maxlinelen=maxlinelen, linesep=linesep,
            canonical_linesep=b'\n') + (b'' if chomp else linesep)
