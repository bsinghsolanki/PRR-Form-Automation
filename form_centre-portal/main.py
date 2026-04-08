from driver.browser import get_driver
from data.google_sheet import load_rows
from engine.field_detector import build_form_map
from engine.form_filler import fill_form
from core.bot import FormBot
from utils.constants import FIELD_MAP


FIELD_MAP = {
    "name of individual requesting information": "Name",
    "email address": "Email",
}

if __name__ == "__main__":
    bot = FormBot(
        credentials="credentials.json",
        sheet_id="1rrAXd03CgCVEASDaovhJLDOeGXfJ-eYQaNdxwd4Q8rM",
        worksheet="Sheet1"
    )

    bot.run()
