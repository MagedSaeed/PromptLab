import json

from django.contrib.auth import get_user_model
from rest_framework import serializers
from taggit.serializers import TaggitSerializer, TagListSerializerField

from prompt.models import (
    Dataset,
    Prompt,
    PromptingProject,
    PromptReviewAction,
    Task,
)

User = get_user_model()


class UserMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]


class TaskSerializer(serializers.ModelSerializer):
    prompt_count = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ["id", "name", "prompt_count"]

    def get_prompt_count(self, obj):
        return obj.prompts.count() if hasattr(obj, 'prompts') else 0


class DatasetListSerializer(serializers.ModelSerializer):
    primary_task = serializers.SerializerMethodField()
    prompt_count = serializers.SerializerMethodField()
    huggingface_link = serializers.CharField(read_only=True)

    class Meta:
        model = Dataset
        fields = [
            "id", "name", "huggingface_name", "description",
            "primary_task", "prompt_count", "huggingface_link",
            "is_single_classification", "target_column",
        ]

    def get_primary_task(self, obj):
        task = obj.primary_task
        return TaskSerializer(task).data if task else None

    def get_prompt_count(self, obj):
        return obj.prompts.count()


class DatasetDetailSerializer(serializers.ModelSerializer):
    primary_task = serializers.SerializerMethodField()
    tasks = TaskSerializer(many=True, read_only=True)
    prompt_count = serializers.SerializerMethodField()
    huggingface_link = serializers.CharField(read_only=True)
    columns_names = serializers.SerializerMethodField()
    configs_with_splits = serializers.SerializerMethodField()

    class Meta:
        model = Dataset
        fields = [
            "id", "name", "huggingface_name", "description",
            "primary_task", "tasks", "prompt_count", "huggingface_link",
            "is_single_classification", "target_column",
            "configs_details", "features", "columns_names",
            "default_subset", "subsets", "download_only_the_default_subset",
            "configs_with_splits",
        ]

    def get_primary_task(self, obj):
        task = obj.primary_task
        return TaskSerializer(task).data if task else None

    def get_prompt_count(self, obj):
        return obj.prompts.count()

    def get_columns_names(self, obj):
        try:
            return obj.get_columns_names()
        except Exception:
            return []

    def get_configs_with_splits(self, obj):
        try:
            return obj.configs_with_splits_names()
        except Exception:
            return {}


class PromptReviewActionSerializer(serializers.ModelSerializer):
    submitter = UserMinimalSerializer(read_only=True)
    submitter_decision_display = serializers.SerializerMethodField()

    class Meta:
        model = PromptReviewAction
        fields = [
            "id", "submitter", "prompt_status", "submitter_comment",
            "submitter_decision", "submitter_decision_display",
            "prompt_before_submitter_modifications", "taken_on",
        ]

    def get_submitter_decision_display(self, obj):
        return obj.get_submitter_decision_display()


class PromptListSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField(read_only=True)
    created_by = UserMinimalSerializer(read_only=True)
    dataset_name = serializers.CharField(source="dataset.name", read_only=True)
    dataset_huggingface_name = serializers.CharField(source="dataset.huggingface_name", read_only=True)
    status = serializers.SerializerMethodField()
    task_name = serializers.CharField(source="task.name", read_only=True, default=None)
    answer_choices_list = serializers.SerializerMethodField()
    updateable = serializers.BooleanField(read_only=True)
    reviewable = serializers.BooleanField(read_only=True)
    is_approved = serializers.BooleanField(read_only=True)

    class Meta:
        model = Prompt
        fields = [
            "id", "name", "template", "text_direction", "dataset",
            "dataset_name", "dataset_huggingface_name", "dataset_subset",
            "created_by", "created_on", "last_updated_on",
            "tags", "task", "task_name", "status",
            "answer_choices", "answer_choices_list",
            "updateable", "reviewable", "is_approved",
            "base_prompt",
        ]

    def get_status(self, obj):
        return obj.status

    def get_answer_choices_list(self, obj):
        if not obj.answer_choices:
            return []
        try:
            choices = json.loads(obj.answer_choices)
            return [c.get("value", c) for c in choices] if isinstance(choices, list) else []
        except (json.JSONDecodeError, TypeError):
            return []


class PromptDetailSerializer(PromptListSerializer):
    review_actions = serializers.SerializerMethodField()

    class Meta(PromptListSerializer.Meta):
        fields = PromptListSerializer.Meta.fields + ["review_actions"]

    def get_review_actions(self, obj):
        actions = obj.review_actions.order_by("-taken_on")
        return PromptReviewActionSerializer(actions, many=True).data


class PromptCreateUpdateSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField(required=False)

    class Meta:
        model = Prompt
        fields = [
            "id", "name", "template", "text_direction",
            "dataset_subset", "answer_choices", "tags", "task",
        ]

    def validate(self, data):
        # If updating, check that prompt is updateable
        if self.instance and not self.instance.updateable:
            raise serializers.ValidationError("This prompt cannot be modified.")
        return data


class PromptReviewSubmitSerializer(serializers.Serializer):
    """For submitting a prompt for review (changes status to SUBMITTED)"""
    pass  # No fields needed, just triggers the action


class PromptReviewSerializer(serializers.Serializer):
    """For a reviewer to review a prompt"""
    submitter_decision = serializers.ChoiceField(
        choices=PromptReviewAction.DecisionChoices.choices
    )
    submitter_comment = serializers.CharField(required=False, allow_blank=True)
    # Optional prompt modifications by reviewer
    name = serializers.CharField(required=False)
    template = serializers.CharField(required=False)
    text_direction = serializers.CharField(required=False)
    answer_choices = serializers.CharField(required=False, allow_blank=True)
    dataset_subset = serializers.CharField(required=False, allow_blank=True)
    tags = TagListSerializerField(required=False)
    task = serializers.PrimaryKeyRelatedField(queryset=Task.objects.all(), required=False, allow_null=True)

    def validate(self, data):
        decision = data.get("submitter_decision")
        comment = data.get("submitter_comment", "")
        if decision == PromptReviewAction.DecisionChoices.RETURNED_FOR_MODIFICATION and not comment:
            raise serializers.ValidationError(
                {"submitter_comment": "Comment is required when returning for modification."}
            )
        return data


class ProjectListSerializer(serializers.ModelSerializer):
    owner = UserMinimalSerializer(read_only=True)
    datasets_count = serializers.IntegerField(read_only=True, default=0)
    members_count = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()

    class Meta:
        model = PromptingProject
        fields = [
            "id", "name", "description", "owner",
            "datasets_count", "members_count", "user_role",
            "minimum_prompts_per_prompter",
        ]

    def get_members_count(self, obj):
        return obj.members.count()

    def get_user_role(self, obj):
        user = self.context.get("request", {})
        if hasattr(user, "user"):
            user = user.user
        else:
            return None
        if obj.owner == user:
            return "owner"
        if obj.reviewers.filter(pk=user.pk).exists():
            return "reviewer"
        if obj.prompters.filter(pk=user.pk).exists():
            return "prompter"
        return None


class ProjectDetailSerializer(serializers.ModelSerializer):
    owner = UserMinimalSerializer(read_only=True)
    prompters = UserMinimalSerializer(many=True, read_only=True)
    reviewers = UserMinimalSerializer(many=True, read_only=True)
    datasets = DatasetListSerializer(many=True, read_only=True)
    datasets_count = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()

    class Meta:
        model = PromptingProject
        fields = [
            "id", "name", "description", "owner",
            "prompters", "reviewers", "datasets",
            "dataset_assignments", "minimum_prompts_per_prompter",
            "secret_key", "datasets_count", "members_count", "user_role",
        ]

    def get_datasets_count(self, obj):
        return obj.datasets.count()

    def get_members_count(self, obj):
        return obj.members.count()

    def get_user_role(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        user = request.user
        if obj.owner == user:
            return "owner"
        if obj.reviewers.filter(pk=user.pk).exists():
            return "reviewer"
        if obj.prompters.filter(pk=user.pk).exists():
            return "prompter"
        return None


class ProjectCreateUpdateSerializer(serializers.ModelSerializer):
    prompters = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all(), required=False
    )
    reviewers = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all(), required=False
    )

    class Meta:
        model = PromptingProject
        fields = [
            "id", "name", "description",
            "minimum_prompts_per_prompter",
            "prompters", "reviewers",
        ]

    def create(self, validated_data):
        prompters = validated_data.pop("prompters", [])
        reviewers = validated_data.pop("reviewers", [])
        project = PromptingProject.objects.create(**validated_data)
        project.prompters.set(prompters)
        project.reviewers.set(reviewers)
        return project

    def update(self, instance, validated_data):
        prompters = validated_data.pop("prompters", None)
        reviewers = validated_data.pop("reviewers", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if prompters is not None:
            instance.prompters.set(prompters)
        if reviewers is not None:
            instance.reviewers.set(reviewers)
        return instance


class HFDatasetAddSerializer(serializers.Serializer):
    """For adding a HuggingFace dataset to a project"""
    dataset_path = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True, default="")
    tasks = serializers.CharField(required=False, allow_blank=True, default="")
    target_column = serializers.CharField(required=False, allow_blank=True, default="")
    default_subset = serializers.CharField(required=False, allow_blank=True, default="")
    subsets = serializers.CharField(required=False, allow_blank=True, default="")
    is_single_classification = serializers.BooleanField(required=False, default=False)
    download_only_the_default_subset = serializers.BooleanField(required=False, default=False)

    def validate(self, data):
        if data.get("download_only_the_default_subset") and not data.get("default_subset"):
            raise serializers.ValidationError(
                "default_subset is required when download_only_the_default_subset is True"
            )
        return data


class HFDatasetValidationSerializer(serializers.Serializer):
    dataset_path = serializers.CharField()


class HFSyncSerializer(serializers.Serializer):
    sheet_id = serializers.CharField()
    sheet_name = serializers.CharField(default="final-list")
    link_column = serializers.CharField(default="link")
    task_column = serializers.CharField(default="task_name")
    target_column = serializers.CharField(required=False, allow_blank=True, default="")
    is_single_classification_column = serializers.CharField(required=False, allow_blank=True, default="")
    default_subset_column = serializers.CharField(required=False, allow_blank=True, default="")
    subsets_column = serializers.CharField(required=False, allow_blank=True, default="")
    clear_datasets = serializers.BooleanField(default=False)
    target_project = serializers.PrimaryKeyRelatedField(queryset=PromptingProject.objects.all())


class LLMTestSerializer(serializers.Serializer):
    model = serializers.CharField()
    prompt_text = serializers.CharField()
    max_tokens = serializers.IntegerField(required=False, default=1000)


class ApplyTemplateSerializer(serializers.Serializer):
    template = serializers.CharField()
    answer_choices = serializers.CharField(required=False, allow_blank=True, default="")
    sample_index = serializers.IntegerField(required=False, default=0)
    subset = serializers.CharField(required=False, allow_blank=True, default="")
    split = serializers.CharField(required=False, allow_blank=True, default="")
    text_direction = serializers.CharField(required=False, default="ltr")
    test_with_llm = serializers.BooleanField(required=False, default=False)
    llm_model = serializers.CharField(required=False, allow_blank=True, default="")


class MultiplePromptGenerateSerializer(serializers.Serializer):
    base_prompt_id = serializers.IntegerField()


class UserSearchSerializer(serializers.Serializer):
    query = serializers.CharField(required=False, allow_blank=True, default="")
