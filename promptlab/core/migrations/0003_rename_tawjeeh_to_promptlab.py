from django.db import migrations


def update_content_type(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")

    old_ct = ContentType.objects.filter(app_label="core", model="tawjeehuser").first()
    new_ct = ContentType.objects.filter(app_label="core", model="promptlabuser").first()

    if old_ct and new_ct:
        # Both exist (Django auto-created the new one via post_migrate).
        # Move permissions from old to new, then delete old.
        for perm in Permission.objects.filter(content_type=old_ct):
            if not Permission.objects.filter(
                content_type=new_ct, codename=perm.codename
            ).exists():
                perm.content_type = new_ct
                perm.save()
            else:
                perm.delete()
        old_ct.delete()
    elif old_ct:
        # Only old exists, just rename it.
        old_ct.model = "promptlabuser"
        old_ct.save()


def reverse_content_type(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ct = ContentType.objects.filter(app_label="core", model="promptlabuser").first()
    if ct:
        ct.model = "tawjeehuser"
        ct.save()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_tawjeehuser_openrouter_api_key"),
        ("prompt", "0015_promptingproject_reviewers"),
    ]

    operations = [
        # 1. Rename the main user table
        migrations.AlterModelTable(
            name="promptlabuser",
            table=None,
        ),
        # 2. Rename FK columns in M2M through tables
        migrations.RunSQL(
            sql='ALTER TABLE "prompt_promptingproject_prompters" RENAME COLUMN "tawjeehuser_id" TO "promptlabuser_id"',
            reverse_sql='ALTER TABLE "prompt_promptingproject_prompters" RENAME COLUMN "promptlabuser_id" TO "tawjeehuser_id"',
        ),
        migrations.RunSQL(
            sql='ALTER TABLE "prompt_promptingproject_reviewers" RENAME COLUMN "tawjeehuser_id" TO "promptlabuser_id"',
            reverse_sql='ALTER TABLE "prompt_promptingproject_reviewers" RENAME COLUMN "promptlabuser_id" TO "tawjeehuser_id"',
        ),
        # 3. Merge content type records (handles case where new CT already exists)
        migrations.RunPython(update_content_type, reverse_content_type),
    ]
