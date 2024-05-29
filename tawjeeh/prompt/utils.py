import datasets


def get_hf_dataset_config_choices(dataset_name):
    return [
        (config_name, config_name)
        for config_name in datasets.get_dataset_config_names(dataset_name)
    ]
