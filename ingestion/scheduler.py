import schedule
import time
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parents[1] / "ingestion"))

from depop_scraper import scrape  # noqa: E402
from embed_items import embed_missing  # noqa: E402


def run():
    schedule.every(3).hours.do(scrape, ["vintage tee", "denim jacket", "streetwear"], 1, 2.0)
    schedule.every(3).hours.do(embed_missing, 100)
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    run()
