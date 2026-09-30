sheet_id = "1kIDS-fwO5l6sH2ZBDCepOJeNyOh2j7Wb-w3W0JChi2k"
sheet_name = "final-list"
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

import pandas as pd

df = pd.read_csv(url, usecols=range(13))


def get_dataset_info(id=-1, name=None):
    if id >= 0:
        row = df.iloc[id]
    elif name:
        id = df.query(f'dataset_name == "{name}"').index
        row = df.iloc[id]
    else:
        raise ("error")

    dataset_name = row["link"].split("datasets/")[-1]
    task_name = row["task_name"]
    example_template = row["example_template"]
    subset = (
        row["dataset_subsets_to_download"]
        if str(row["dataset_subsets_to_download"]) != "nan"
        else None
    )
    answer_choices = (
        eval(row["answer_choices"]) if str(row["answer_choices"]) != "nan" else []
    )

    return dataset_name, subset, task_name, example_template, answer_choices
