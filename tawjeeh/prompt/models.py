from functools import cached_property

import datasets
from core.utils import redis_cache
from django.db import models


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

    @property
    @redis_cache()
    def subsets_with_splits(self):
        configs_and_splits = {}
        config_names = datasets.get_dataset_config_names(
            self.huggingface_name,
            trust_remote_code=True,
        )
        # Iterate through available configs and get their splits
        for config_name in config_names:
            config_info = datasets.get_dataset_config_info(
                self.huggingface_name,
                config_name,
                trust_remote_code=True,
            )
            splits = list(config_info.splits.keys())
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
    def load_samples(self, split="train", subset=None, max_samples=10_000):
        try:
            args = [self.huggingface_name]
            if len(self.subsets_with_splits) > 1:
                if not subset:
                    subset = list(self.subsets_with_splits.keys())[0]
                args.append(subset)
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
        on_delete=models.SET_NULL,
    )
    dataset_subset = models.CharField(max_length=10_000, null=True, blank=True)

    def __str__(self):
        return f"prompt for dataset {self.dataset}"
