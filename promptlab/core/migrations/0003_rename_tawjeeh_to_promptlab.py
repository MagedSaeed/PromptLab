from django.db import migrations


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
        # 3. Update the content type record
        migrations.RunSQL(
            sql="UPDATE django_content_type SET model = 'promptlabuser' WHERE app_label = 'core' AND model = 'tawjeehuser'",
            reverse_sql="UPDATE django_content_type SET model = 'tawjeehuser' WHERE app_label = 'core' AND model = 'promptlabuser'",
        ),
    ]
