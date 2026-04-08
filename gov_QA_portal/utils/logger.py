import logging
import os
from datetime import datetime
import colorlog

# ── Log folder & file ──────────────────────────────────
LOG_DIR  = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(
    LOG_DIR,
    f"automation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)

# ── Colour map for console ─────────────────────────────
LOG_COLORS = {
    "DEBUG"   : "cyan",
    "INFO"    : "green",
    "WARNING" : "yellow",
    "ERROR"   : "red",
    "CRITICAL": "bold_red",
}


def get_logger(name: str = "form_automation") -> logging.Logger:
    """
    Returns a logger that writes:
      - Coloured output  →  console
      - Plain text       →  logs/automation_YYYYMMDD_HHMMSS.log
    
    Usage:
        from utils.logger import get_logger
        log = get_logger(__name__)
        log.info("Starting row 3")
        log.error("Failed to find tile")
    """

    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # ── Console handler (coloured) ─────────────────────
    console_handler = colorlog.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(
        colorlog.ColoredFormatter(
            fmt=(
                "%(log_color)s%(asctime)s "
                "[%(levelname)-8s] "
                "%(name)s → %(message)s%(reset)s"
            ),
            datefmt="%H:%M:%S",
            log_colors=LOG_COLORS,
        )
    )

    # ── File handler (plain text) ──────────────────────
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)-8s] %(name)s → %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# ── Convenience: module-level default logger ───────────
log = get_logger()