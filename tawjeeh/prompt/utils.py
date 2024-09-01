import concurrent.futures
import json
import tempfile

import datasets
from prompt import constants
from sklearn.model_selection import train_test_split


def get_split_samples(
    dataset_object,
    split,
    subset,
    cache_dir,
    max_samples=constants.MAX_SAMPLES,
    shuffled=True,
):
    args = [dataset_object.huggingface_name]
    args.append(subset)
    # kwargs = dict(split=f"{split}[:{max_samples}]", trust_remote_code=True)
    kwargs = dict(split=split, trust_remote_code=True)
    kwargs.update(dict(cache_dir=cache_dir))
    dataset = datasets.load_dataset(
        *args,
        **kwargs,
    )

    if shuffled:
        # Shuffle the dataset
        dataset = dataset.shuffle()

    df = dataset.to_pandas()

    try:
        stratified_sample_df, _ = train_test_split(
            df,
            train_size=len(df) - len(set(df[dataset_object.target_column])),
            stratify=df[dataset_object.target_column],
            random_state=42,
        )
        stratified_sample_df = stratified_sample_df[:max_samples]
        dataset = datasets.Dataset.from_pandas(
            stratified_sample_df.reset_index(drop=True)
        )
    except Exception:
        # found an issue in stratifing the dataset, roll back to default shuffling
        dataset = datasets.Dataset.from_pandas(df[:max_samples].reset_index(drop=True))
    return dataset.to_dict()


def collect_dataset_configs_details(dataset_object):
    configs_and_splits = {}
    config_names = datasets.get_dataset_config_names(
        dataset_object.huggingface_name,
        trust_remote_code=True,
    )

    # Function to fetch splits for a given config name
    def fetch_splits_details(config_name):
        try:
            # Create a temporary directory
            splits_details = {}
            with tempfile.TemporaryDirectory() as tmp_cache_dir:
                # Load the dataset and specify the temporary cache directory
                hf_dataset = datasets.load_dataset(
                    dataset_object.huggingface_name,
                    config_name,
                    trust_remote_code=True,
                    cache_dir=tmp_cache_dir,
                )
                splits = list(hf_dataset.keys())
                for split in splits:
                    splits_details[split] = dict()
                    splits_details[split]["all_samples_count"] = hf_dataset[
                        split
                    ].num_rows
                    splits_details[split]["samples"] = get_split_samples(
                        split=split,
                        subset=config_name,
                        cache_dir=tmp_cache_dir,
                        dataset_object=dataset_object,
                    )
            return config_name, splits_details
        except Exception as e:
            print(
                f"Error retrieving {dataset_object.huggingface_name}'s splits with config: {config_name}. The error is: {e}"
            )
            return None

    # Process configs in parallel if there are more than 10
    if len(config_names) > 10:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_config = {
                executor.submit(fetch_splits_details, config_name): config_name
                for config_name in config_names
            }
            for future in concurrent.futures.as_completed(future_to_config):
                try:
                    results = future.result()  # Use the result() method
                    if results is None:
                        continue
                    config_name, splits_details = results
                    configs_and_splits[config_name] = splits_details
                except Exception as e:
                    print(
                        f"Error occurred while processing config_name: {future_to_config[future]}: {e}"
                    )
                    continue
    else:
        # Process configs sequentially if there are 10 or fewer
        for config_name in config_names:
            fetch_results = fetch_splits_details(config_name)
            if not fetch_results:
                continue
            config_name, splits_details = fetch_splits_details(config_name)
            configs_and_splits[config_name] = splits_details
    try:
        dataset_object.configs_details = configs_and_splits
        dataset_object.save()
    except Exception as e:
        print("Error saving configs details: ", e)
        print("trying to save as string...")
        dataset_object.configs_details = json.dumps(
            configs_and_splits,
            indent=4,
            sort_keys=True,
            default=str,
        )
        dataset_object.save()
    return configs_and_splits
