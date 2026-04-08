import logging

def get_logger(name="FORM_ENGINE"):
    
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s — %(levelname)s — %(message)s"
    )

    file_handler = logging.FileHandler("form_engine.log")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger
def log_unknown_field(label):
    with open("unknown_fields.txt", "a") as f:
        f.write(label + "\n")


def log_required_missing(label):
    with open("required_missing.txt", "a") as f:
        f.write(label + "\n")
