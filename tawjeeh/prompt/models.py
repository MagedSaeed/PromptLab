import concurrent.futures
from functools import cached_property

import datasets
from core.utils import redis_cache
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Task(models.Model):
    name = models.CharField(max_length=255)

    @property
    def prompts(self):
        return Prompt.objects.filter(dataset__tasks__pk=self.pk)

    def __str__(self):
        return self.name


class Dataset(models.Model):
    name = models.CharField(max_length=255)
    tasks = models.ManyToManyField(Task, related_name="datasets")
    huggingface_name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    huggingface_raw = models.JSONField(null=True, blank=True)

    @cached_property
    def hf_object(self):
        return datasets.load_dataset(self.dataset.huggingface_name)

    @redis_cache()
    def get_columns_names(self):
        try:
            # Assuming the default configuration
            default_config_name = list(self.subsets_with_splits.keys())[0]
            features = datasets.get_dataset_config_info(
                self.huggingface_name,
                config_name=default_config_name,
            ).features

            # Extract and return column names
            columns = list(features.keys())
            return columns
        except Exception as e:
            print(f"Error retrieving dataset columns: {e}")
            raise e

    @property
    @redis_cache()
    def subsets_with_splits(self):
        configs_and_splits = {}
        config_names = datasets.get_dataset_config_names(
            self.huggingface_name,
            trust_remote_code=True,
        )

        # Function to fetch splits for a given config name
        def fetch_splits(config_name):
            config_info = datasets.get_dataset_config_info(
                self.huggingface_name,
                config_name,
                trust_remote_code=True,
            )
            splits = list(config_info.splits.keys())
            return config_name, splits

        # Process configs in parallel if there are more than 10
        if len(config_names) > 10:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_to_config = {
                    executor.submit(fetch_splits, config_name): config_name
                    for config_name in config_names
                }
                for future in concurrent.futures.as_completed(future_to_config):
                    config_name, splits = future.result()
                    configs_and_splits[config_name] = splits
        else:
            # Process configs sequentially if there are 10 or fewer
            for config_name in config_names:
                config_name, splits = fetch_splits(config_name)
                configs_and_splits[config_name] = splits

        return configs_and_splits

    @redis_cache()
    def get_huggingface_info(self, subset=None):
        try:
            # Load the dataset information without loading the entire dataset
            if len(self.subsets_with_splits) > 1:
                if not subset:
                    subset = list(self.subsets_with_splits.keys())[0]
                info = datasets.load_dataset_builder(
                    self.huggingface_name,
                    subset,
                    trust_remote_code=True,
                ).info
            else:
                info = datasets.load_dataset_builder(
                    self.huggingface_name,
                    trust_remote_code=True,
                ).info

            # Create the Hugging Face link
            huggingface_link = (
                f"https://huggingface.co/datasets/{self.huggingface_name}"
            )

            # Format the dataset details
            details = {
                "description": info.description,
                "citation": info.citation,
                "homepage": info.homepage,
                "license": info.license,
                "huggingface_link": huggingface_link,
                "full_info": info,
            }
            return details
        except Exception as e:
            return {"error": str(e)}

    @redis_cache()
    def load_samples(self, split=None, subset=None, max_samples=10_000):
        try:
            args = [self.huggingface_name]
            if len(self.subsets_with_splits) > 1:
                if not subset:
                    subset = list(self.subsets_with_splits.keys())[0]
            args.append(subset)
            if not split:
                if subset:
                    split = list(self.subsets_with_splits[subset])[0]
                else:
                    split = list(self.subsets_with_splits.values())[0][0]
            kwargs = dict(split=f"{split}[:{max_samples}]", trust_remote_code=True)
            dataset = datasets.load_dataset(*args, **kwargs)
            return dataset
        except Exception as e:
            return {"error": str(e)}

    @property
    def huggingface_link(self):
        return f"https://huggingface.co/datasets/{self.huggingface_name}"

    def __str__(self):
        return self.name


class Prompt(models.Model):
    class TextDirectionChoices(models.TextChoices):
        LTR = "ltr", "Left-to-Right"
        RTL = "rtl", "Right-to-Left"

    class PromptStatus(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        RETURNED_FOR_MODIFICATION = (
            "RETURNED_FOR_MODIFICATION",
            "Returned for modification",
        )
        APPROVED = "APPROVED", "Approved"

    name = models.CharField(max_length=1_000)
    answer_choices = models.CharField(max_length=100_000, null=True, blank=True)
    template = models.TextField()
    text_direction = models.CharField(
        max_length=10,
        default="ltr",
        choices=TextDirectionChoices.choices,
    )
    dataset = models.ForeignKey(
        Dataset,
        null=True,
        related_name="prompts",
        on_delete=models.SET_NULL,  # TODO: change to protect
    )
    dataset_subset = models.CharField(max_length=10_000, null=True, blank=True)
    created_by = models.ForeignKey(
        to=User,
        null=True,
        related_name="prompts",
        on_delete=models.SET_NULL,  # TODO: change to protect
    )
    created_on = models.DateTimeField(auto_now_add=True)
    last_updated_on = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=1_000,
        default=PromptStatus.DRAFT,
        choices=PromptStatus.choices,
    )

    def __str__(self):
        return f"prompt for dataset {self.dataset}"

    @property
    def updateable(self):
        return self.status == self.PromptStatus.DRAFT
