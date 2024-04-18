import socket
import hashlib
import time
from base64 import urlsafe_b64encode
from pathlib import Path

from . import gts
from .boxtoparty import makeparty
from .pkmlib import encode


class Request:
    def __init__(self, h=None):
        if not h:
            self.action=None
            self.page=None
            self.getvars={}
            return
        elif isinstance(h, bytes):
            h = h.decode()
        if not h.startswith("GET"):
            raise TypeError("Not a DS header!")
        request=h[h.find("/syachi2ds/web/")+15:h.find("HTTP/1.1")-1]
        #request=h.split("/")[3][:h.find("HTTP")-1]
        self.page=request[:request.find("?")]
        self.action=request[request.find("/")+1:request.find(".asp?")]
        vars=dict((i[:i.find("=")], i[i.find("=")+1:]) for i in request[request.find("?")+1:].split("&"))
        self.getvars=vars

    def __str__(self):
        request="%s?%s"%(self.page, '&'.join("%s=%s"%i for i in list(self.getvars.items())))
        return 'GET /syachi2ds/web/%s HTTP/1.1\r\n'%request+ \
            'Host: gamestats2.gs.nintendowifi.net\r\nUser-Agent: GameSpyHTTP/1.0\r\n'+ \
            'Connection: close\r\n\r\n'

    def __repr__(self):
        return "<Request for %s, with %s>"%(self.action, ", ".join(i+"="+j for i, j in list(self.getvars.items())))


class Response:
    def __init__(self, h):
        self.is_pkm_data = False
        if isinstance(h, bytes):
            try:
                h = h.decode()
            except UnicodeDecodeError:
                self.is_pkm_data = True
                self.data = h
                return
        if not h.startswith("HTTP/1.1"):
            self.data=h
            return
        h=h.split("\r\n")
        while True:
            line=h.pop(0)
            if not line:
                break
            elif line.startswith("P3P"):
                self.p3p=line[line.find(": ")+2:] # unknown
            elif line.startswith("cluster-server"):
                self.server=line[line.find(": ")+2:] # unknown
            elif line.startswith("X-Server-"):
                self.sname=line[line.find(": ")+2:] # unknown
            elif line.startswith("Content-Length"):
                self.len=int(line[line.find(": ")+2:]) # necessary
            elif line.startswith("Set-Cookie"):
                self.cookie=line[line.find(": ")+2:] # unnecessary
        self.data="\r\n".join(h)

    def get_bytes(self):
        months=[
            "???", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
            "Nov", "Dec"
        ]
        days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        t=time.gmtime()
        str_repr = (
            "HTTP/1.1 200 OK\r\n" +
            "Date: %s, %02i %s %i %02i:%02i:%02i GMT\r\n"%(
                    days[t[6]], t[2], months[t[1]], t[0], t[3], t[4], t[5]
            ) +
            "Server: Microsoft-IIS/6.0\r\n" +
            "P3P: CP='NOI ADMa OUR STP'\r\n" +
            "cluster-server: aphexweb3\r\n" +
            "X-Server-Name: AW4\r\n" +
            "X-Powered-By: ASP.NET\r\n" +
            "Content-Length: %i\r\n"%len(self.data) +
            "Content-Type: text/html\r\n" +
            "Set-Cookie: ASPSESSIONIDQCDBDDQS=JFDOAMPAGACBDMLNLFBCCNCI; path=/\r\n" +
            "Cache-control: private\r\n\r\n"
        )
        if self.is_pkm_data:
            return str_repr.encode() + self.data
        else:
            return str_repr.encode() + self.data.encode()


def encode_pkm(pkm_path: Path) -> tuple[bytes, bytes]:
    with open(pkm_path, 'rb') as f:
        pkm = f.read()
    assert len(pkm) in [136, 220]
    if len(pkm) == 136:
        pkm = makeparty(pkm)
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


def encode_response(data: bytes, encoded_pkm: bytes) -> tuple[bytes, bool]:
    is_sent = False
    request = Request(data)
    action = request.action
    if len(request.getvars) == 1:
        response = gts.token
    else:
        if action == 'info':
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
            is_sent = True
        m = hashlib.sha1()
        m.update(
            gts.salt.encode() + urlsafe_b64encode(response) + gts.salt.encode()
        )
        response += m.hexdigest().encode()
    response = Response(response).get_bytes()
    return response, is_sent


def connect(address: str, port: int) -> tuple[str, int]:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((address, port))
        connection_address, connection_port = s.getsockname()
    return connection_address, connection_port


def spoof_dns(gts_dns_address: str = gts.DNS, gts_dns_port: int = 53) -> None:
    gts_connection_address, gts_connection_port = connect(gts_dns_address, gts_dns_port)
    print(f'Set DNS on DS to {gts_connection_address}')
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('0.0.0.0', gts_dns_port))
        while True:
            # receive from ds
            ds_response_bytes, ds_response_address = server_socket.recvfrom(512)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
                # connect to gts
                client_socket.connect((gts_dns_address, gts_dns_port))
                # send to gts
                client_socket.send(ds_response_bytes)
                # receive from gts
                gts_response_bytes = client_socket.recv(512)
                if b'gamestats2' in gts_response_bytes:
                    gts_response_bytes = gts_response_bytes[:-4] + b''.join(
                        int(i).to_bytes() for i in gts_connection_address.split('.')
                    )
                # send to ds
                server_socket.sendto(gts_response_bytes, ds_response_address)
