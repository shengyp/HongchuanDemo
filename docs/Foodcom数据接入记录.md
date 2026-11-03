# Food.com 食谱数据接入记录

## 输入

用户提供的 `archive.zip` 包含 `RAW_recipes.csv`、`RAW_interactions.csv`、`PP_recipes.csv`、`PP_users.csv`、`ingr_map.pkl` 和交互划分文件。本次使用 `RAW_recipes.csv` 的 `id`、`name`、`minutes`、`ingredients` 字段，其他文件保留在原压缩包中，尚未接入。

`tools/convert_foodcom.py` 流式读取压缩包，使用 `ast.literal_eval` 解析食材名称列表，将食谱、食材和食谱食材关系索引到 `data/foodcom.sqlite`。食材名称按原始英文文本去除首尾空格、转小写，同一食谱中重复名称只计一次；不自动合并近义词。数据库 `metadata` 表保存原压缩包 SHA-256。

本次索引 231,637 道食谱、14,942 种食材，无跳过记录。按“食材出现在多少道食谱中”计数，频次的第 25 百分位阈值为 2；频次不超过 2 的 5,217 种食材被标记为长尾。这是统计定义，不等于原始论文 UnKGE-BCKC 模型输出。共现表示两种食材出现在同一道原始食谱中，界面不会将补偿候选当作真实共现。

## 营养计算边界

`RAW_recipes.csv` 的 `ingredients` 是食材**名称列表**，没有每项克数。`nutrition` 列是食谱级营养数组，不能反推每个食材的用量，也不能直接当成每 100 g 食材营养值。本次 Food.com 数据只用于食谱检索、长尾频次和共现，不进入营养验算和克数生成。当前系统的营养计算仍基于演示食谱及单独的 USDA 食材目录。

下一步可抽取一批食谱，人工核对原网页中的食材用量、份数和生熟状态，换算为克后匹配 USDA FDC ID，再生成 `templates/recipe_parts.csv`。匹配不到或量词无法可靠换算的食材应标记待核对，不应臆造克数。

数据集页面：[Food.com Recipes and Interactions](https://www.kaggle.com/datasets/shuyangli94/food-com-recipes-and-user-interactions)。
