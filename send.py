import argparse
import hashlib
import os
import time
from base64 import urlsafe_b64encode
from pathlib import Path

from utils.pokehaxlib import initServ, getReq, sendResp
from utils.boxtoparty import makeparty
from utils.pkmlib import encode
from utils import gtsvar


def encode_pkm(pkm_path: Path) -> tuple[bytes, bytes]:
    with open(pkm_path, 'rb') as f:
        pkm = f.read()
    assert len(pkm) in [136, 220]
    if len(pkm) == 136:
        print('Adding bytes for party')
        pkm = makeparty(pkm)
    print('Adding bytes for GTS')
    encoded_pkm = encode(pkm)
    encoded_pkm += b'\x00' * 16
    encoded_pkm += pkm[0x08:0x0a]  # ID
    if pkm[0x40] & 0x04:
        encoded_pkm += b'\x03'  # gender
    else:
        encoded_pkm += (pkm[0x40] & 2 + 1).to_bytes()
    encoded_pkm += pkm[0x8c:0x8c+1]  # level
    # request フシギダネ with either gender at any level
    encoded_pkm += b'\x01\x00\x03\x00\x00\x00\x00\x00'
    encoded_pkm += b'\xdb\x07\x03\x0a\x00\x00\x00\x00'  # date deposited as 3/10/2011
    encoded_pkm += b'\xdb\x07\x03\x16\x01\x30\x00\x00'  # date traded
    encoded_pkm += pkm[0x00:0x04]  # PID
    encoded_pkm += pkm[0x0c:0x0e]  # original trainer ID
    encoded_pkm += pkm[0x0e:0x10]  # original trainer SID
    encoded_pkm += pkm[0x68:0x78]  # original trainer Name
    encoded_pkm += b'\xDB\x02'  # country, city
    encoded_pkm += b'\x46\x01\x15\x02'  # sprite, exchanged, version, language
    encoded_pkm += b'\x01\x00'
    return pkm, encoded_pkm


def send_pkm(pkm_path: Path) -> None:
    sent = False
    response = ''
    pkm, encoded_pkm = encode_pkm(pkm_path)
    print('Enter GTS')
    while not sent:
        sock, request = getReq()
        action = request.action
        if len(request.getvars) == 1:
            sendResp(sock, gtsvar.token)
            continue
        elif action == 'info':
            response = b'\x01\x00'
            print('Connection established')
        elif action == 'setProfile':
            response = b'\x00' * 8
        elif action == 'post':
            response = b'\x0c\x00'
        elif action == 'search':
            response = b'\x01\x00'
        elif action == 'result':
            response = encoded_pkm
        elif action == 'delete':
            response = b'\x01\x00'
            sent = True
        m = hashlib.sha1()
        m.update(
            gtsvar.salt.encode() + urlsafe_b64encode(response) + gtsvar.salt.encode()
        )
        response += m.hexdigest().encode()
        sendResp(sock, response)


def main(pkm_file: str) -> None:
    pkm_path = Path(pkm_file)
    assert pkm_path.suffix == '.pkm'
    assert pkm_path.exists()
    initServ()
    time.sleep(1)
    send_pkm(pkm_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Send .pkm file to games via the GTS')
    parser.add_argument('pkm_file', metavar='pkm-file', type=str)
    args = parser.parse_args()

    main(args.pkm_file)
