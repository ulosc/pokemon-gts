import struct
from pathlib import Path

from .boxtoparty import makeparty


shift_index = [
    0, 1, 2, 3, 0, 1, 3, 2, 0, 2, 1, 3, 0, 2, 3, 1, 0, 3, 1, 2, 0, 3, 2, 1, 1, 0, 2, 3, 1,
    0, 3, 2, 1, 2, 0, 3, 1, 2, 3, 0, 1, 3, 0, 2, 1, 3, 2, 0, 2, 0, 1, 3, 2, 0, 3, 1, 2, 1,
    0, 3, 2, 1, 3, 0, 2, 3, 0, 1, 2, 3, 1, 0, 3, 0, 1, 2, 3, 0, 2, 1, 3, 1, 0, 2, 3, 1, 2,
    0, 3, 2, 0, 1, 3, 2, 1, 0,
]


class RNG:
    def __init__(self, value: int) -> None:
        self.value = value

    def __call__(self) -> int:
        self.value = 0x41C64E6D * self.value + 0x6073
        self.value &= 0xFFFFFFFF
        return self.value >> 16


def __encode_rng(pkm: bytes) -> bytes:
    s = list(struct.unpack('IHH' + 'H' * (len(pkm) // 2 - 4), pkm))
    shift = ((s[0] >> 0xD & 0x1F) % 24)
    order = shift_index[4*shift : 4*shift+4]
    shifted = s[:3]
    for i in order:
        shifted += s[3+16*i : 19+16*i]
    shifted += s[67:]
    r = RNG(s[2])
    for i in range(3, 67):
        shifted[i] ^= r()
    if len(shifted) > 67:
        r = RNG(shifted[0])
        for i in range(67, len(shifted)):
            shifted[i] ^= r()
    return struct.pack('IHH' + 'H' * (len(pkm) // 2 - 4), *shifted)


def __decode_rng(pkm: bytes) -> bytes:
    shifted = list(struct.unpack('IHH' + 'H' * (len(pkm) // 2 - 4), pkm))
    r = RNG(shifted[2])
    for i in range(3, 67):
        shifted[i] ^= r()
    if len(shifted) > 67:
        r = RNG(shifted[0])
        for i in range(67, len(shifted)):
            shifted[i] ^= r()
    shift = ((shifted[0] >> 0xD & 0x1F) % 24)
    order = shift_index[4*shift : 4*shift+4]
    s = shifted[:3]
    for i in range(4):
        s += shifted[3+16*order.index(i) : 19+16*order.index(i)]
    s += shifted[67:]
    return struct.pack('IHH' + 'H' * (len(pkm) // 2 - 4), *s)


def encode_pkm(pkm_path: Path) -> tuple[bytes, bytes]:
    with open(pkm_path, 'rb') as f:
        pkm = f.read()
    assert len(pkm) in [136, 220]
    if len(pkm) == 136:
        pkm = makeparty(pkm)
    encoded_pkm = __encode_rng(pkm)
    encoded_pkm += b'\x00' * 16
    encoded_pkm += pkm[0x08:0x0a]  # ID
    if pkm[0x40] & 0x04:
        encoded_pkm += b'\x03'  # gender
    else:
        encoded_pkm += (pkm[0x40] & 2 + 1).to_bytes()
    encoded_pkm += pkm[0x8c:0x8c+1]  # level
    # request フシギダネ with either gender at any level
    encoded_pkm += b'\x01\x00\x03\x00\x00\x00\x00\x00'  # request
    encoded_pkm += b'\xdb\x07\x03\x0a\x00\x00\x00\x00'  # date deposited as 3/10/2011
    encoded_pkm += b'\xdb\x07\x03\x16\x01\x30\x00\x00'  # date traded
    encoded_pkm += pkm[0x00:0x04]  # PID
    encoded_pkm += pkm[0x0c:0x0e]  # original trainer ID
    encoded_pkm += pkm[0x0e:0x10]  # original trainer SID
    encoded_pkm += pkm[0x68:0x78]  # original trainer Name
    encoded_pkm += b'\xDB\x02'  # country, city
    encoded_pkm += b'\x46\x01\x15\x02'  # sprite, exchanged, version, language
    encoded_pkm += b'\x01\x00'  # unknown
    return pkm, encoded_pkm
