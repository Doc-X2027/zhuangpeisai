import json
import sys
from pathlib import Path

BASE_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
WORKFLOW_PATH = BASE_DIR / "workflow.json"


def read_json(file_name=WORKFLOW_PATH):
    with open(file_name, 'r', encoding='utf-8') as f:
        task = json.load(f)

    ret = ""
    for item in task["assembly_sequence"]:
        color = item["object_color"]
        obj = {
            "red": "1", "orange": "2", "yellow": "3",
            "green": "4", "blue": "5", "purple": "6",
            "pink": "7", "cyan": "8", "brown": "9",
        }[color]
        opr = item["operation"]
        act = {"pick": "1", "place": "2"}[opr]
        ret = ret + str(obj) + ";"
    return ret

if __name__ == "__main__":
    ret = read_json()
    print(ret)
