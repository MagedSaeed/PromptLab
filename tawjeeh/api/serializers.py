from django.contrib.auth import get_user_model
from prompt.models import Dataset, Prompt, PromptingProject
from rest_framework import serializers
from taggit.serializers import TaggitSerializer, TagListSerializerField

User = get_user_model()


class PromptSerializer(TaggitSerializer, serializers.ModelSerializer):
    project_secret_key = serializers.CharField(write_only=True)
    dataset_huggingface_name = serializers.CharField(write_only=True)
    created_by = serializers.CharField(write_only=True)
    tags = TagListSerializerField(required=False)

    class Meta:
        model = Prompt
        fields = [
            "tags",
            "name",
            "template",
            "created_by",
            "dataset_subset",
            "answer_choices",
            "text_direction",
            "project_secret_key",
            "dataset_huggingface_name",
        ]

    def validate(self, data):
        project_secret_key = data.pop("project_secret_key", None)
        dataset_huggingface_name = data.pop("dataset_huggingface_name", None)
        if not project_secret_key:
            raise serializers.ValidationError("Project secret key is required")
        if not dataset_huggingface_name:
            raise serializers.ValidationError("Dataset Hugging Face name is required")

        try:
            created_by = User.objects.get(username=data.pop("created_by", ""))
            project = PromptingProject.objects.get(secret_key=project_secret_key)
            dataset = Dataset.objects.get(
                huggingface_name=dataset_huggingface_name,
                prompting_projects=project,
            )
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid user")
        except PromptingProject.DoesNotExist:
            raise serializers.ValidationError("Invalid project secret key")
        except Dataset.DoesNotExist:
            raise serializers.ValidationError("Dataset does not belong to the project")

        data["dataset"] = dataset
        data["created_by"] = created_by
        return data

    def create(self, validated_data):
        tags = validated_data.pop("tags", [])
        instance = Prompt.objects.create(**validated_data)
        instance.tags.add(*map(str, tags))
        return instance
