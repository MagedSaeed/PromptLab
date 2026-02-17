from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_tawjeehuser_openrouter_api_key"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="TawjeehUser",
            new_name="PromptLabUser",
        ),
    ]
