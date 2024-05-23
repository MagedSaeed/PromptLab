from functools import cached_property

import datasets
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
    subsets = models.CharField(
        null=True,
        blank=True,
        max_length=50_000,
    )  # if provided, split by ","

    @cached_property
    def huggingface_info(self):
        try:
            # Load the dataset information without loading the entire dataset
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

    def load_samples(self, split_name, subset="", max_samples=10_000):
        try:
            args = [self.huggingface_name]
            if subset:
                assert subset in self.subsets.split(",")
                args.append(subset)
            kwargs = dict(split=f"{split_name}[:{max_samples}]")
            dataset = datasets.load_dataset(*args, **kwargs)
            return dataset
        except Exception as e:
            return {"error": str(e)}

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
