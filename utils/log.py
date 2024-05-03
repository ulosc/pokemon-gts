import logging


def set_root_logger(log_file: str = './gts.log') -> None:
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # stream handling
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    logger.addHandler(stream_handler)
    # file handling
    formatter = logging.Formatter('%(asctime)s %(message)s', '%Y-%m-%d %H:%M:%S')
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
