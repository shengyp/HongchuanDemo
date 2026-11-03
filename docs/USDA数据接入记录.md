# USDA FoodData Central 数据接入记录

## 用户提供的文件

文件名：`FoodData_Central_csv.zip`。项目通过 `tools/convert_fdc.py` 读取其中的 `food.csv`、`food_nutrient.csv`、`nutrient.csv`，不改写原始压缩包。导出文件 `data/fdc_foundation_complete.json` 包含源文件 SHA-256，用于确认来源版本。

## 筛选与字段

只取 `food.csv` 中 `data_type=foundation_food` 的主食物记录，避免把样品、子样品、市场采购记录当成独立食材。通过 `fdc_id` 关联 `food_nutrient.csv`，保留蛋白质 1003、脂肪 1004、碳水 1005、膳食纤维 1079、钠 1093，以及能量。能量优先取 2048（Atwater Specific），缺失时取 1008，再缺失时取 2047（Atwater General）。单位按 `nutrient.csv` 核对：能量 kcal，其余分别为 g 或 mg；均为每 100 g 可食部。缺一项就排除该食物，不把空白视为零。

本次文件有 469 条 Foundation Foods 主食物记录；180 条六项指标齐全，已导出为单独的“USDA 食材来源目录”。每条保留 FDC ID、英文名称、发布日期及能量所用的营养素 ID。目录仅用于浏览与后续食材匹配，当前不与内置演示食谱混合。当前压缩包不包含结构化的完整食谱食材用量，因此无法据此生成真实食谱推荐结果。

`templates/fdc_ingredients.csv` 是这 180 条记录转换后的可上传食材表；ID 采用 `fdc_` 加 FDC ID。它与 `templates/recipe_parts.csv` 配合使用。只有食材表而没有正确的食谱组成表时，不应直接替换当前工作台数据。

## 下一步接入食谱

准备 `templates/recipe_parts.csv` 对应的食谱组成表，每行至少要有 `recipe_id,recipe_name,servings,ingredient_id,grams`。食材须先按具体形态（生/熟、部位、加工状态）人工匹配到 FDC ID，不能只按名称近似自动替换。食材表可由所选 FDC 记录按 `templates/ingredients.csv` 导出；再把两张 CSV 一起从“数据管理”页面导入。需要另外核对可食部重量、缺失项和数据使用范围。

USDA 官方资料：[FoodData Central 下载页](https://fdc.nal.usda.gov/download-datasets/)；[Foundation Foods 文档](https://fdc.nal.usda.gov/Foundation_Foods_Documentation/)。
