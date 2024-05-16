from django.db import models

# Create your models here.


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

    def __str__(self):
        return self.name


class Prompt(models.Model):
    content = models.CharField(max_length=50_000)
    dataset = models.ForeignKey(
        Dataset,
        related_name="prompts",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return f"prompt for dataset{self.dataset}"
