def decode_text(text):
    for enc in ('utf-8', 'iso-8859-15', 'iso-8859-1', 'ascii'):
        try:
            return text.decode(enc)
        except UnicodeDecodeError:
            continue
    # fallback
    return text.decode('utf-8', 'replace')
