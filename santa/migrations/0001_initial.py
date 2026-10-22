import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DrawState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("locked", models.BooleanField(default=False)),
                ("drawn", models.BooleanField(default=False)),
                ("drawn_at", models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Participant",
            fields=[
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ("wishlist", models.TextField(blank=True, default="")),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("giftee", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="santa.participant")),
            ],
        ),
    ]
