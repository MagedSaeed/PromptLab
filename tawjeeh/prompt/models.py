from django.db import models

# Create your models here.


class Task(models.Model):
    name = models.CharField(max_length=255)

    @property
    def prompts(self):
        return Prompt.objects.filter(dataset__task__pk=self.pk)


class Dataset(models.Model):
    name = models.CharField(max_length=255)
    task = models.ForeignKey(
        Task,
        null=True,
        blank=True,
        related_name="datasets",
        on_delete=models.CASCADE,
    )
    huggingface_name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    huggingface_raw = models.JSONField(null=True, blank=True)


class Prompt(models.Model):
    content = models.CharField(max_length=50_000)
    dataset = models.ForeignKey(
        Dataset,
        related_name="prompts",
        on_delete=models.CASCADE,
    )
