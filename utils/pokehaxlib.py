import datetime as dt
import logging
import hashlib
import socket
import time
import typing
from base64 import urlsafe_b64encode
from pathlib import Path

from . import gts
from .boxtoparty import makeparty
from .log import log_response
from .rng import encode_rng


logger = logging.getLogger(__name__)


def check_if_bytes(data: typing.Any) -> None:
    if not isinstance(data, bytes):
        raise TypeError(f'Expected bytes but got {type(data)}:\n{data}')


class Request:
    """
    Requests from clients.

    Action and parameter count are parsed from data.

    Format of data:

        b'''
        GET /syachi2ds/web/${EXCHANGEPATH}/${ACTION}.asp?pid=303556658 HTTP/1.1\r\n
        Host: gamestats2.gs.nintendowifi.net\r\n
        User-Agent: GameSpyHTTP/1.0\r\n
        Connection: close\r\n\r\n
        '''

    $EXCHANGEPATH is 'worldexchange' or 'common'
    $ACTION is 'info', 'setProfile', 'post', 'search', 'result', or 'delete'

    parameter_count == 0 when ' HTTP/1.1' and subsequent inputs are replaced with a hash.
    """
    def __init__(self, data: bytes) -> None:
        check_if_bytes(data)
        if not data.startswith(b'GET'):
            raise RuntimeError(f'Expected request to start with \'GET\' but got {data}')
        self.exchangepath, self.action = (
            data.split(b'GET /syachi2ds/web/')[1].split(b'.asp?')[0].decode().split('/')
        )
        self.parameter_count = data.split(b'.asp?')[1].split(b' HTTP/1.1')[0].count(b'&')


class Response:
    """
    Responses from server.

    Current time, length of data, and data are returned when converted to bytes.
    """
    def __init__(self, request: Request, encoded_pkm: bytes) -> None:
        self.is_sent = False
        if request.parameter_count == 0:
            self.data = gts.token
        else:
            if request.action == 'info':
                self.data = b'\x01\x00'
                logging.info('Connection established')
            elif request.action == 'setProfile':
                self.data = b'\x00' * 8
            elif request.action == 'post':
                self.data = b'\x0c\x00'
            elif request.action == 'search':
                self.data = b'\x01\x00'
            elif request.action == 'result':
                self.data = encoded_pkm
            elif request.action == 'delete':
                self.data = b'\x01\x00'
                self.is_sent = True
            else:
                raise RuntimeError(f'Unexpected request action found: {action}')
            m = hashlib.sha1()
            m.update(gts.salt + urlsafe_b64encode(self.data) + gts.salt)
            self.data += m.hexdigest().encode()

    def __bytes__(self) -> bytes:
        now = dt.datetime.now(dt.timezone.utc).strftime(
            'Date: %a, %d %b %Y %H:%M:%S GMT\r\n'
        )
        content_length = f'Content-Length: {len(self.data)}\r\n'
        return (
            b'HTTP/1.1 200 OK\r\n' +
            now.encode() +
            b'Server: Microsoft-IIS/6.0\r\n' +
            b'P3P: CP=\'NOI ADMa OUR STP\'\r\n' +
            b'cluster-server: aphexweb3\r\n' +
            b'X-Server-Name: AW4\r\n' +
            b'X-Powered-By: ASP.NET\r\n' +
            content_length.encode() +
            b'Content-Type: text/html\r\n' +
            b'Set-Cookie: ASPSESSIONIDQCDBDDQS=JFDOAMPAGACBDMLNLFBCCNCI; path=/\r\n' +
            b'Cache-control: private\r\n\r\n' +
            self.data
        )


def encode_pkm(pkm_path: Path) -> tuple[bytes, bytes]:
    with open(pkm_path, 'rb') as f:
        pkm = f.read()
    assert len(pkm) in [136, 220]
    if len(pkm) == 136:
        pkm = makeparty(pkm)
    encoded_pkm = encode_rng(pkm)
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


def encode_response(data: bytes, encoded_pkm: bytes) -> tuple[bytes, bool]:
    request = Request(data)
    response = Response(request, encoded_pkm)
    return bytes(response), response.is_sent


def connect(address: str, port: int) -> tuple[str, int]:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((address, port))
        connection_address, connection_port = s.getsockname()
    return connection_address, connection_port


def spoof_dns(gts_dns_address: str = gts.DNS, gts_dns_port: int = 53) -> None:
    logger.info('Spoofing DNS')
    gts_connection_address, gts_connection_port = connect(gts_dns_address, gts_dns_port)
    logger.info(f'Set DNS on DS to {gts_connection_address}')
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('0.0.0.0', gts_dns_port))
        while True:
            # receive from ds
            ds_response_bytes, ds_response_address = server_socket.recvfrom(512)
            log_response(ds_response_bytes, f'{ds_response_address} (DS)')
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
                # connect to gts
                client_socket.connect((gts_dns_address, gts_dns_port))
                # send to gts
                client_socket.send(ds_response_bytes)
                # receive from gts
                gts_response_bytes, gts_response_address = client_socket.recvfrom(512)
                log_response(gts_response_bytes, f'{gts_response_address} (GTS)')
                if b'gamestats2' in gts_response_bytes:
                    gts_response_bytes = gts_response_bytes[:-4] + b''.join(
                        int(i).to_bytes() for i in gts_connection_address.split('.')
                    )
                # send to ds
                server_socket.sendto(gts_response_bytes, ds_response_address)
