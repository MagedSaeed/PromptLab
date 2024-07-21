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

    @property
    def primary_task(self):
        if self.tasks.exists():
            return self.tasks.first()

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
            try:
                dataset = datasets.load_dataset(
                    self.huggingface_name,
                    config_name,
                    trust_remote_code=True,
                )
                splits = list(dataset.keys())
                return config_name, splits
            except Exception as e:
                print(
                    f"Error retrieving {self.huggingface_name}'s splits with config: {config_name}. The error is: {e}"
                )
                return None

        # Process configs in parallel if there are more than 10
        if len(config_names) > 10:
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                future_to_config = {
                    executor.submit(fetch_splits, config_name): config_name
                    for config_name in config_names
                }
                for future in concurrent.futures.as_completed(future_to_config):
                    if not hasattr(future, "results"):
                        continue
                    results = future.results()
                    if results is None:
                        continue
                    config_name, splits = results
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

    def __str__(self):
        return f"prompt for dataset {self.dataset}"

    @property
    def updateable(self):
        # catch the case when the prompt is not yet created
        # it should be updateable in this case
        if not self.pk:
            return True
        return self.status in (
            PromptReviewAction.PromptStatus.DRAFT,
            PromptReviewAction.DecisionChoices.RETURNED_FOR_MODIFICATION,
        )

    @property
    def status(self):
        status = PromptReviewAction.PromptStatus.DRAFT
        if self.review_actions.exists():
            last_review_action = self.review_actions.last()
            status = last_review_action.prompt_status
            if last_review_action.submitter_decision:
                status = last_review_action.submitter_decision
        return status


class PromptReviewAction(models.Model):
    class DecisionChoices(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        RETURNED_FOR_MODIFICATION = (
            "RETURNED_FOR_MODIFICATION",
            "Returned for modification",
        )

    class PromptStatus(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"

    submitter = models.ForeignKey(User, on_delete=models.RESTRICT)
    prompt = models.ForeignKey(
        Prompt,
        on_delete=models.CASCADE,
        null=True,
        related_name="review_actions",
    )
    prompt_status = models.CharField(
        max_length=256,
        default=PromptStatus.DRAFT,
        choices=PromptStatus.choices,
    )
    submitter_comment = models.CharField(
        max_length=10_000,
        null=True,
        blank=True,
    )
    submitter_decision = models.CharField(
        null=True,
        blank=True,
        max_length=256,
        choices=DecisionChoices.choices,
    )
    # this field is a json field that will
    # save the old prompt fields before reviewer modification.
    # only changed fields will be kept
    prompt_before_submitter_modifications = models.JSONField(null=True, blank=True)
    taken_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review made by {self.submitter} on {self.prompt}."
