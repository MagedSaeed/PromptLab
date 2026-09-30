sheet_id = "1kIDS-fwO5l6sH2ZBDCepOJeNyOh2j7Wb-w3W0JChi2k"
sheet_name = "final-list"
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

import pandas as pd
from datasets import load_dataset

df = pd.read_csv(url, usecols=range(7))


def get_answer_choices(dataset, split):
    schema = {}
    features = dataset[split].features
    for feature_name in features:
        feature = features[feature_name]
        if type(feature) == list:
            schema[feature_name] = feature[0].dtype
        elif type(feature) == dict:
            first_feature_key = list(feature.keys())[0]
            schema[feature_name] = feature[first_feature_key]
        else:
            try:
                return feature.names
            except:
                schema[feature_name] = feature.dtype
    return []


ds = []
all_choices = []
for _id in range(len(df)):
    row = df.iloc[_id]
    dataset_name = row["link"].split("datasets/")[-1]
    task_name = row["task_name"]
    example_template = row["example_template"]
    subset = row["subset"] if str(row["subset"]) != "nan" else None
    has_answer_choices = True if row["has_answer_choices"] == "yes" else False
    answer_choices = []
    if has_answer_choices:
        if "belebele" in dataset_name:
            split = subset

        dataset = load_dataset(dataset_name, subset, trust_remote_code=True)

        if "belebele" not in dataset_name:
            split = "train"
        if "train" in dataset:
            split = "train"
        elif "validation" in dataset:
            split = "validation"
        else:
            split = "test"

        answer_choices = get_answer_choices(dataset, split)
    ds.append(dataset_name)
    all_choices.append(answer_choices)


pd.DataFrame({"data": ds, "answer_choices": all_choices}).to_csv("out.csv")
