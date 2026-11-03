"""Print coverage for an official FoodData Central CSV archive."""

import csv
import io
import sys
import zipfile
from collections import Counter, defaultdict


def main(path):
    with zipfile.ZipFile(path) as archive:
        prefix = next(n.removesuffix("food.csv") for n in archive.namelist() if n.endswith("/food.csv"))

        def rows(name):
            return csv.DictReader(io.TextIOWrapper(archive.open(prefix + name), encoding="utf-8-sig"))

        foods = {x["fdc_id"]: x for x in rows("food.csv") if x["data_type"] == "foundation_food"}
        values = defaultdict(dict)
        wanted = {"1008", "2047", "2048", "1003", "1004", "1005", "1079", "1093"}
        for row in rows("food_nutrient.csv"):
            if row["fdc_id"] in foods and row["nutrient_id"] in wanted:
                values[row["fdc_id"]][row["nutrient_id"]] = row["amount"]
        required = {"1003", "1004", "1005", "1079", "1093"}
        complete = [key for key, v in values.items() if required <= v.keys() and any(k in v for k in ("1008", "2047", "2048"))]
        print("Foundation foods:", len(foods), "complete six nutrients:", len(complete))
        print("Nutrient coverage:", Counter(k for v in values.values() for k in v))
        for key, food in foods.items():
            if any(term in food["description"].lower() for term in ("chicken, broiler", "rice, white", "broccoli", "salmon", "tofu", "quinoa", "spinach", "tomato", "mushroom", "chickpea", "olive oil")):
                print(key, food["description"], values.get(key, {}))


if __name__ == "__main__":
    main(sys.argv[1])
