from functools import cached_property

import datasets
import requests
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
    config = models.CharField(
        null=True,
        blank=True,
        max_length=50_000,
    )

    @cached_property
    def hf_object(self):
        return datasets.load_dataset(self.dataset.huggingface_name)

    @property
    @redis_cache()
    def subsets_with_splits(self):
        url = f"https://datasets-server.huggingface.co/splits?dataset={self.huggingface_name}"
        response = requests.get(url)
        splits = response.json()["splits"]
        subsets_with_splits = {}
        for split in splits:
            if split["config"] not in subsets_with_splits:
                subsets_with_splits[split["config"]] = []
            subsets_with_splits[split["config"]].append(split["split"])
        return subsets_with_splits

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
                ).info
            else:
                info = datasets.load_dataset_builder(self.huggingface_name).info

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
    def load_samples(self, split_name="train", subset=None, max_samples=10_000):
        try:
            args = [self.huggingface_name]
            if len(self.subsets_with_splits) > 1:
                if not subset:
                    subset = list(self.subsets_with_splits.keys())[0]
                args.append(subset)
            kwargs = dict(split=f"{split_name}[:{max_samples}]")
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
    name = models.CharField(max_length=1_000)
    answer_choices = models.CharField(max_length=100_000, null=True, blank=True)
    template = models.TextField()
    dataset = models.ForeignKey(
        Dataset,
        null=True,
        related_name="prompts",
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        return f"prompt for dataset {self.dataset}"
