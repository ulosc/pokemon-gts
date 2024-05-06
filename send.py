import argparse
import logging
import socket
import threading
import time
from pathlib import Path

from utils.log import set_root_logger, log_response
from utils.pokehaxlib import encode_pkm, encode_response, spoof_dns


set_root_logger()
logger = logging.getLogger(__name__)


def send_pkm(pkm_path: Path) -> None:
    pkm, encoded_pkm = encode_pkm(pkm_path)
    # daemonize thread to exit when main thread exits
    t = threading.Thread(target=spoof_dns, args=(), daemon=True)
    t.start()
    time.sleep(1)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', 80))
        s.listen()
        logger.info('Enter GTS')
        while True:
            # accept connection from ds
            connection_socket, connection_address = s.accept()
            with connection_socket:
                # receive from ds
                ds_response_bytes = connection_socket.recv(512)
                log_response(ds_response_bytes, f'{connection_address} (DS)')
                # create response for ds
                encoded_response_bytes, is_sent = encode_response(
                    data=ds_response_bytes,
                    encoded_pkm=encoded_pkm,
                )
                # send to ds
                connection_socket.send(encoded_response_bytes)
            if is_sent:
                break


def main(pkm_file: str) -> None:
    pkm_path = Path(pkm_file)
    assert pkm_path.suffix == '.pkm'
    assert pkm_path.exists()
    send_pkm(pkm_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Send .pkm file to games via the GTS')
    parser.add_argument('pkm_file', metavar='pkm-file', type=str)
    args = parser.parse_args()

    main(args.pkm_file)
