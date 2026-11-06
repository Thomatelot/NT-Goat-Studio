"""Same-size patching of Nintendo BLZ ("backwards LZ") compressed binaries.

Only the tokens around the modified bytes are re-encoded (optimal parse); the
rest of the original token stream is kept, and the stream is padded back to its
original length, so nothing else in the ROM has to move.
"""
import struct

MAX_DISP = 0x1002   # (0xFFF + 3)
MIN_DISP = 3
MAX_LEN = 18
MIN_LEN = 3


def _header(comp):
    enc_hdr, inc_len = struct.unpack_from('<II', comp, len(comp) - 8)
    return enc_hdr >> 24, enc_hdr & 0xFFFFFF, inc_len


def decompress(comp):
    from_tokens, plain = tokens(comp)
    return plain


def tokens(comp):
    """Return (token list, plain). Token = (pos, length, kind, value):
    produces plain[pos:pos+length]; kind 0 = literal (value=byte),
    kind 1 = match (value = disp, source = plain[pos+disp : pos+disp+length])."""
    hdr_len, enc_len, inc_len = _header(comp)
    n = len(comp)
    out = bytearray(n + inc_len)
    out[:n] = comp
    start = n - enc_len
    src, dst = n - hdr_len, n + inc_len
    toks = []
    while src > start:
        src -= 1
        flags = comp[src]
        for _ in range(8):
            if src <= start:
                break
            if flags & 0x80:
                src -= 2
                v = comp[src] | (comp[src + 1] << 8)
                ln, disp = (v >> 12) + 3, (v & 0xFFF) + 3
                for _ in range(ln):
                    dst -= 1
                    out[dst] = out[dst + disp]
                toks.append((dst, ln, 1, disp))
            else:
                src -= 1
                dst -= 1
                out[dst] = comp[src]
                toks.append((dst, 1, 0, comp[src]))
            flags = (flags << 1) & 0xFF
    return toks, bytes(out)


def encode(toks):
    """Encode tokens (in decode order) into the backward stream (memory order)."""
    rev = bytearray()
    for g in range(0, len(toks), 8):
        group = toks[g:g + 8]
        flags = 0
        body = bytearray()
        for i, (pos, ln, kind, val) in enumerate(group):
            if kind:
                flags |= 0x80 >> i
                v = ((ln - 3) << 12) | (val - 3)
                body += bytes([v >> 8, v & 0xFF])
            else:
                body.append(val)
        rev.append(flags)
        rev += body
    return bytes(reversed(rev))


def _best_tokens(plain, lo, hi):
    """Optimal (min bits) tokenisation of plain[lo:hi] in decode order (high→low).
    Matches may copy from anywhere above their position (already decoded)."""
    n = hi - lo
    # longest match for a token ending at position e (covering [e-L, e))
    idx = {}
    for q in range(lo + 3, min(len(plain), hi + MAX_DISP + MAX_LEN) + 1):
        idx.setdefault(plain[q - 3:q], []).append(q)
    INF = 1 << 60
    best = [INF] * (n + 1)   # best[k] = cost to encode plain[lo:lo+k]
    choice = [None] * (n + 1)
    best[0] = 0
    for k in range(1, n + 1):
        e = lo + k
        c = best[k - 1] + 9
        ch = (1, 0, plain[e - 1])
        if k >= MIN_LEN:
            key = plain[e - 3:e]
            for q in idx.get(key, ()):
                disp = q - e
                if disp < MIN_DISP or disp > MAX_DISP:
                    continue
                L = 0
                while L < MAX_LEN and L < k and plain[e - 1 - L] == plain[q - 1 - L]:
                    L += 1
                if L >= MIN_LEN:
                    # any length MIN_LEN..L is possible with this disp
                    for l in range(MIN_LEN, L + 1):
                        cc = best[k - l] + 17
                        if cc < c:
                            c, ch = cc, (l, 1, disp)
        best[k], choice[k] = c, ch
    out = []
    k = n
    while k > 0:
        l, kind, val = choice[k]
        out.append((lo + k - l, l, kind, val))
        k -= l
    return out   # already in decode order (high → low)


def patch(comp, changes, margin=MAX_DISP + MAX_LEN + 2):
    """changes: {offset_in_plain: new_byte}. Returns new compressed bytes of the
    SAME length, or raises ValueError if it cannot fit."""
    hdr_len, enc_len, inc_len = _header(comp)
    toks, plain = tokens(comp)
    new = bytearray(plain)
    for o, b in changes.items():
        new[o] = b
    start = len(comp) - enc_len
    if min(changes) < start:
        raise ValueError("change inside the uncompressed prefix (handle separately)")
    # regions to re-encode: [lo - margin, hi) merged
    offs = sorted(changes)
    regions = []
    for o in offs:
        lo, hi = o - margin, o + 1
        if regions and lo <= regions[-1][1]:
            regions[-1][1] = max(regions[-1][1], hi)
        else:
            regions.append([lo, hi])
    # snap to original token boundaries
    starts = sorted(t[0] for t in toks)
    import bisect
    snapped = []
    for lo, hi in regions:
        lo = max(start, lo)
        i = bisect.bisect_right(starts, lo) - 1
        lo2 = starts[max(i, 0)]
        j = bisect.bisect_left(starts, hi)
        hi2 = starts[j] if j < len(starts) else len(plain)
        snapped.append((lo2, hi2))
    out_toks = []
    ti = 0
    for lo, hi in sorted(snapped, key=lambda r: -r[0]):
        while ti < len(toks) and toks[ti][0] >= hi:
            out_toks.append(toks[ti]); ti += 1
        out_toks.extend(_best_tokens(bytes(new), lo, hi))
        while ti < len(toks) and toks[ti][0] >= lo:
            ti += 1
    out_toks.extend(toks[ti:])
    stream = encode(out_toks)
    old_stream_len = len(comp) - start - hdr_len
    pad = len(comp) - start - len(stream) - 8
    if pad < 0 or pad > 0xFF - 8:
        raise ValueError("re-encoded stream does not fit (%d bytes over)" % (len(stream) - old_stream_len))
    result = bytearray(comp[:start]) + stream + b'\xFF' * pad
    result += struct.pack('<II', ((8 + pad) << 24) | (len(comp) - start), inc_len)
    assert len(result) == len(comp)
    # verify: decodes to the new plain, and in-place decoding is safe
    _, check = tokens(bytes(result))
    if check != bytes(new):
        raise ValueError("verification failed")
    _check_safety(bytes(result))
    return bytes(result)


def _check_safety(comp):
    """In-place decompression must never overwrite unread compressed bytes."""
    hdr_len, enc_len, inc_len = _header(comp)
    n = len(comp)
    start = n - enc_len
    src, dst = n - hdr_len, n + inc_len
    while src > start:
        src -= 1
        flags = comp[src]
        for _ in range(8):
            if src <= start:
                break
            if flags & 0x80:
                src -= 2
                v = comp[src] | (comp[src + 1] << 8)
                dst -= (v >> 12) + 3
            else:
                src -= 1
                dst -= 1
            if dst < src:
                raise ValueError("unsafe in-place decompression")
            flags = (flags << 1) & 0xFF
