from django.db import migrations

noop = migrations.RunPython.noop


def fill_is_general_admin(apps, schema_editor):
    user_model = apps.get_model('users', 'User')
    user_model.objects.filter(is_staff=True).update(is_general_admin=True)


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0009_user_is_general_admin'),
    ]

    operations = [
        migrations.RunPython(fill_is_general_admin, noop),
    ]
