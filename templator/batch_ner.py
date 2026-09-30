from datasets import Dataset, load_dataset

data = [
    {
        "ner_col": "ner_tag",
        "word_col": "token",
        "data_name": "community-datasets/caner",
    },
    {"ner_col": "label", "word_col": "Word", "data_name": "arbml/AQMAR"},
    {
        "ner_col": "label",
        "word_col": "Word",
        "data_name": "arbml/Zero_Shot_Cross_Lingual_NER_ar",
    },
    {"ner_col": "label", "word_col": "Word", "data_name": "arbml/Disease_NER"},
]


for item in data:
    ner_col = item["ner_col"]
    word_col = item["word_col"]
    data_name = item["data_name"]
    data = load_dataset(data_name)
    batched_data = []
    lst_ner = []
    lst_word = []
    final_dataset = {"words": [], "tags": []}
    for i, ex in enumerate(data["train"]):
        lst_ner.append(ex[ner_col])
        lst_word.append(ex[word_col])

        if i % 16 == 0 and i != 0:
            final_dataset["words"].append(lst_word)
            final_dataset["tags"].append(lst_ner)
            lst_ner = []
            lst_word = []

    print(data_name)
    print(data["train"].features[ner_col].names)
    data = Dataset.from_dict(final_dataset)
    data_name = data_name.split("/")[-1]
    data.push_to_hub(f"arbml/{data_name}_batched")
    print(data[0])
