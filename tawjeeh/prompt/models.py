import json
import random
import secrets
from functools import cached_property

import datasets
from core.utils import redis_cache  # noqa: F401
from django.contrib.auth import get_user_model
from django.core.cache import cache  # noqa: F401
from django.db import models, transaction
from prompt.utils import collect_dataset_configs_details
from taggit.managers import TaggableManager

User = get_user_model()


class PromptingProject(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    prompters = models.ManyToManyField(User, related_name="prompting_projects")
    datasets = models.ManyToManyField("Dataset", related_name="prompting_projects")
    dataset_assignments = models.JSONField(default=dict, null=True, blank=True)
    minimum_prompts_per_prompter = models.PositiveIntegerField(
        default=5,
        null=True,
        blank=True,
    )
    secret_key = models.CharField(max_length=64, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.secret_key:
            self.secret_key = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def distribute_datasets(self, save=True):
        with transaction.atomic():
            prompters = list(self.prompters.all())
            tasks = self.datasets.values_list("tasks__name", flat=True).distinct()
            assignments = {}
            for task_name in tasks:
                task_datasets = list(
                    self.datasets.filter(tasks__name=task_name).values(
                        "name",
                        # "huggingface_name",
                    )
                )
                random.shuffle(task_datasets)

                for i, prompter in enumerate(prompters):
                    dataset = task_datasets[i % len(task_datasets)]

                    if prompter.username not in assignments:
                        assignments[prompter.username] = {}

                    assignments[prompter.username][task_name] = {
                        "dataset_name": dataset["name"],
                        # "huggingface_name": dataset["huggingface_name"],
                    }

            dataset_assignments = assignments
            if save:
                self.dataset_assignments = dataset_assignments
                self.save()
                return f"Distributed datasets for {len(tasks)} tasks among {len(prompters)} prompters for project {self.name}"
            return dataset_assignments

    def __str__(self):
        return self.name


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
    is_single_classification = models.BooleanField(default=False)
    # determins the target label column name in the dataset
    # for a sentiment anslysis with text column and label column, the value of this field should be label
    target_column = models.CharField(
        max_length=10_000,
        null=True,
        blank=True,
    )
    configs_details = models.JSONField(null=True, blank=True)
    features = models.JSONField(null=True, blank=True)
    columns_names = models.JSONField(null=True, blank=True)
    default_subset = models.CharField(
        max_length=10_000,
        null=True,
        blank=True,
        help_text="Subset to show by default when accessing the dataset from the left bar. If empty, the first subset will be chosen. Useful when the dataset has many subsets.",
    )
    subsets = models.CharField(
        max_length=10_000,
        null=True,
        blank=True,
        help_text='Subsets to download, empty for all. Split subsets by comma",".',
    )

    @property
    def primary_task(self):
        if self.tasks.exists():
            return self.tasks.first()

    @cached_property
    def default_config(self):
        # Assuming the default configuration
        if self.default_subset:
            default_config_name = self.default_subset
        else:
            default_config_name = list(self.get_configs_details().keys())[0]
        default_config = datasets.get_dataset_config_info(
            self.huggingface_name,
            trust_remote_code=True,
            config_name=default_config_name,
        )
        return default_config

    def get_features(self):
        """
        Get the features of a given dataset and cache if needed
        """
        if self.features:
            return self.features
        try:
            features = self.default_config.features
            self.features = features.to_dict()
            self.save()
            return features
        except Exception as e:
            print(f"Error retrieving dataset features: {e}")
            raise e

    def get_columns_names(self):
        if self.columns_names:
            return self.columns_names
        try:
            # Assuming the default configuration
            features = self.get_features()
            # Extract and return column names
            columns = list(features.keys())
            self.columns_names = columns
            self.save()
            return columns
        except Exception as e:
            print(f"Error retrieving dataset ({self.name}) columns: {e}")
            raise e

    def configs_with_splits_names(self):
        names = {}
        if (
            not self.subsets or self.subsets == "nan"
        ):  # "nan" is coming from the empty string in excel pandas
            for config in self.get_configs_details():
                names[config] = list(self.get_configs_details()[config].keys())
        else:
            for config in self.subsets.split(","):
                names[config] = list(self.get_configs_details()[config].keys())
        return names

    def get_configs_details(self):
        if not self.configs_details:
            collect_dataset_configs_details(dataset_object=self)
        if isinstance(self.configs_details, str):
            return json.loads(self.configs_details)
        return self.configs_details

    @property
    def huggingface_link(self):
        return f"https://huggingface.co/datasets/{self.huggingface_name}"

    def __str__(self):
        return self.name

    def create_example_prompt(
        self,
        prompt_template,
        created_by,
        subset=None,
        answer_choices=None,
        text_direction="ltr",
        name="Example Prompt",
    ):
        example_template_tag = "Example Prompt"
        # check first if the dataset has already an example prompt
        if Prompt.objects.filter(
            dataset=self,
            tags__name__icontains=example_template_tag,
        ).exists():
            "example prompt already exists"
            return None
        if not subset:
            subset = list(self.get_configs_details().keys())[0]
        if User.objects.filter(username__iexact=created_by).exists():
            created_by_user = User.objects.get(username__iexact=created_by)
        else:
            created_by_user = User.objects.create(username=created_by)
        if answer_choices:
            assert isinstance(answer_choices, list), "answer_choices must be a list"
            answer_choices = list(map(lambda choice: {"value": choice}, answer_choices))
            answer_choices = json.dumps(answer_choices)
        else:
            answer_choices = None
        prompt = Prompt(
            template=prompt_template,
            dataset=self,
            dataset_subset=subset,
            created_by=created_by_user,
            text_direction=text_direction,
            answer_choices=answer_choices,
            name=name,
        )
        prompt.save()
        # add example prompt tag
        prompt.tags.add(example_template_tag)
        prompt.save()
        # create an action for submitting the prompt by the creator
        submission_action = PromptReviewAction(
            prompt=prompt,
            submitter=created_by_user,
            prompt_status=PromptReviewAction.PromptStatus.SUBMITTED,
        )
        submission_action.save()
        # create an acceptance action
        # approval_action = PromptReviewAction(
        #     prompt=prompt,
        #     submitter=created_by_user,
        #     submitter_decision=PromptReviewAction.DecisionChoices.APPROVED,
        #     prompt_status=PromptReviewAction.PromptStatus.SUBMITTED,
        # )
        # approval_action.save()
        return prompt

    def reset_cache(self):
        self.columns_names = None
        self.features = None
        self.configs_details = None
        self.save()
        return True

    @property
    def default_answer_choices(self):
        for prompt in self.prompts.all():
            if prompt.answer_choices:
                return prompt.answer_choices
        return None


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

    tags = TaggableManager(blank=True)

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
    def reviewable(self):
        if not self.review_actions.exists():
            return False

        return (
            self.status == PromptReviewAction.PromptStatus.SUBMITTED
            and self.review_actions.last().submitter_decision
            != PromptReviewAction.DecisionChoices.APPROVED
        )

    @property
    def approved(self):
        return not self.updateable and not self.reviewable

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

    def get_submitter_decision_display(self):
        if self.submitter_decision:
            return self.DecisionChoices(self.submitter_decision).label
        return "Submitted"  # or any default value you prefer

    def __str__(self):
        return f"Review made by {self.submitter} on {self.prompt}."


# it was part of the dataset class
# def get_huggingface_info(self, subset=None):
#     cache_key = f"{self.huggingface_name}_huggingface_info"
#     details = cache.get(cache_key)
#     if details:
#         return details
#     try:
#         # Load the dataset information without loading the entire dataset
#         if len(self.subsets_with_splits) > 1:
#             if not subset:
#                 subset = list(self.subsets_with_splits.keys())[0]
#             info = datasets.load_dataset_builder(
#                 self.huggingface_name,
#                 subset,
#                 trust_remote_code=True,
#             ).info
#         else:
#             info = datasets.load_dataset_builder(
#                 self.huggingface_name,
#                 trust_remote_code=True,
#             ).info

#         # Create the Hugging Face link
#         huggingface_link = (
#             f"https://huggingface.co/datasets/{self.huggingface_name}"
#         )

#         # Format the dataset details
#         details = {
#             "description": info.description,
#             "citation": info.citation,
#             "homepage": info.homepage,
#             "license": info.license,
#             "huggingface_link": huggingface_link,
#             "full_info": info,
#         }
#         cache.set(cache_key, details, timeout=constants.DEFAULT_TIMEOUT)
#         return details
#     except Exception as e:
#         return {"error": str(e)}
