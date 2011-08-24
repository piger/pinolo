def decode_text(text):
    result = None

    for encoding in ('utf-8', 'iso-8859-15', 'iso-8859-1'):
        try:
            result = text.decode(encoding)
        except UnicodeDecodeError:
            continue
        else:
            break
    if result is None:
        result = text.decode('utf-8', 'replace')
    return result
