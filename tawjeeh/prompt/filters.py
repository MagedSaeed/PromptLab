import django_filters
from prompt.models import Task


class TaskFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = Task
        fields = ["name"]
