import struct


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


def encode_rng(pkm: bytes) -> bytes:
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


def decode_rng(pkm: bytes) -> bytes:
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
