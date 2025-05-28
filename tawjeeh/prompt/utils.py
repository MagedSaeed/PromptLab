import concurrent.futures
import json
import tempfile

import datasets
import openai
from core.utils import redis_cache
from prompt import constants
from sklearn.model_selection import train_test_split
from templator import TemplateCreator


@redis_cache()
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


@redis_cache()
def collect_dataset_configs_details(dataset_object):
    configs_and_splits = {}
    # Check if we should only download the default subset
    default_subset = getattr(dataset_object, "default_subset", None)
    if default_subset and default_subset.lower().strip() == "nan":
        default_subset = "default"
    if getattr(dataset_object, "download_only_the_default_subset", False):
        if not dataset_object.default_subset:
            raise ValueError(
                "default_subset must be specified when download_only_the_default_subset is True"
            )
        config_names = [default_subset]
    else:
        # Original logic for getting all configs
        if (
            not dataset_object.subsets
            or dataset_object.subsets.lower().strip() == "nan"
        ):
            config_names = datasets.get_dataset_config_names(
                dataset_object.huggingface_name,
                trust_remote_code=True,
            )
        else:
            config_names = dataset_object.subsets.split(",")

        if default_subset:
            if dataset_object.default_subset not in config_names:
                config_names.append(dataset_object.default_subset)

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

    # Since we might only be processing one config now, adjust the parallel processing threshold
    if len(config_names) > 10:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_config = {
                executor.submit(fetch_splits_details, config_name): config_name
                for config_name in config_names
            }
            for future in concurrent.futures.as_completed(future_to_config):
                try:
                    results = future.result()
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
            if config_name.lower().strip() == "nan":
                continue
            fetch_results = fetch_splits_details(config_name)
            if not fetch_results:
                continue
            config_name, splits_details = fetch_results
            configs_and_splits[config_name] = splits_details

    try:
        dataset_object.configs_details = configs_and_splits
        dataset_object.save()
    except Exception as e:
        print(
            f"Error saving configs details for dataset {dataset_object.name}. The error is:",
            e,
        )
        print("trying to save as string...")
        dataset_object.configs_details = json.dumps(
            configs_and_splits,
            indent=4,
            sort_keys=True,
            default=str,
            ensure_ascii=False,
        )
        dataset_object.save()
    return configs_and_splits


def generate_ai_prompts(prompt_dict):
    from prompt.models import Dataset, Prompt

    """
    prompt_dict will come as follows:
        {
            "name": "name",
            "template": "prompt template",
            "task_name": "task name",
            "task_pk": self.task.pk # mostly not needed
            "answer_choices": "[{'value': 'answer choice 1'}, {'value': 'answer choice 2'}, ..., {'value': 'answer choice 5'}]",
            "text_direction": "rtl", # or "ltr"
            "dataset_pk": self.dataset.pk, # primary key to the dataset object, (needed in the return)
            "dataset_name": "huggingface name, for example: arbml/ashaar",
            "dataset_subset": "train" # or "validation", "test",
            "created_by": "zaid", # mostly not needed
        }
    """
    answer_choices = []
    if prompt_dict["answer_choices"]:
        answer_choices = json.loads(prompt_dict["answer_choices"])
        answer_choices = [item["value"] for item in answer_choices]
    templator = TemplateCreator(
        prompt_dict["dataset_name"],
        config=prompt_dict["dataset_subset"],
        answer_choices=answer_choices,
        lang="English",
    )

    templates = templator.prompt_chatgpt(
        prompt_dict["task_name"],
        prompt_dict["template"],
        version="gpt-4-turbo",
        num_templates=5,
    )

    # you can implement the code that generates the prompts here
    # this is just a mocking logic to see how the prompts can be returned as Prompt db objects
    generated_prompts_objects = []
    for t in templates:
        new_prompt = Prompt(
            name=t.name,
            template=t.text,
            dataset=Dataset.objects.get(pk=prompt_dict["dataset_pk"]),
            text_direction="ltr",
            answer_choices=json.dumps(
                [{"value": answer_choice} for answer_choice in t.answer_choices]
            ),  # answer choices need to be in this format
            dataset_subset=prompt_dict["dataset_subset"],
        )
        generated_prompts_objects.append(new_prompt)
    return generated_prompts_objects


def translate_prompt_with_ai(prompt_dict):
    from prompt.models import Dataset, Prompt

    """
    prompt_dict will come as follows:
        {
            "name": "name",
            "template": "prompt template",
            "task_name": "task name",
            "task_pk": self.task.pk # mostly not needed
            "answer_choices": "[{'value': 'answer choice 1'}, {'value': 'answer choice 2'}, ..., {'value': 'answer choice 5'}]",
            "text_direction": "rtl", # or "ltr"
            "dataset_pk": self.dataset.pk, # primary key to the dataset object, (needed in the return)
            "dataset_name": "huggingface name, for example: arbml/ashaar",
            "dataset_subset": "train" # or "validation", "test",
            "created_by": "zaid", # mostly not needed
        }
    """

    # you can implement the code that generates the prompts here
    # this is just a mocking logic to see how the prompts can be returned as Prompt db objects
    new_prompt = Prompt(
        name="AI translated from prompt with title: " + prompt_dict["name"],
        template=f"(AI translated): {prompt_dict['template']}",
        dataset=Dataset.objects.get(pk=prompt_dict["dataset_pk"]),
        text_direction="ltr",
        answer_choices=json.dumps(
            [{"value": f"answer_choice {j + 1}"} for j in range(5)]
        ),  # answer choices need to be in this format
        dataset_subset=prompt_dict["dataset_subset"],
    )
    return new_prompt


# Add this to your existing utils.py file
# Inside prompt/utils.py


def send_to_openrouter(prompt_text, model_id, api_key, max_tokens=1000):
    """
    Send a prompt to OpenRouter API and get the response.

    Args:
        prompt_text (str): The processed prompt template text
        model_id (str): The ID of the model to use
        api_key (str): OpenRouter API key
        max_tokens (int): Maximum tokens to generate

    Returns:
        dict: Response from OpenRouter API
    """
    try:
        # Configure OpenAI client for OpenRouter
        client = openai.OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )

        # Make the API call using extra_headers instead of headers
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt_text}],
            max_tokens=max_tokens,
            extra_headers={
                "HTTP-Referer": "https://tawjeeh.up.railway.app",  # Required by OpenRouter
                "X-Title": "Tawjeeh Prompt Testing",
            },
        )

        # Extract the text from the response
        if response.choices and len(response.choices) > 0:
            result = {
                "content": response.choices[0].message.content,
                "model": model_id,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                "finish_reason": response.choices[0].finish_reason,
            }
            return {"success": True, "result": result}
        else:
            return {"success": False, "error": "No response generated"}

    except Exception as e:
        import traceback

        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
