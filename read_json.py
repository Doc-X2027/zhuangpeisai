import json

def read_json(file_name):
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
    file_name = "workflow_20260530_160807.json"
    ret = read_json(file_name)
    print(ret)
