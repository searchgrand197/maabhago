# Generated manually for RoleFieldPermission

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("roles_permissions", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="RoleFieldPermission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("module_code", models.CharField(db_index=True, max_length=100)),
                ("field_key", models.CharField(max_length=100)),
                ("can_create", models.BooleanField(default=False)),
                ("can_read", models.BooleanField(default=False)),
                ("can_update", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("role", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="field_permissions", to="roles_permissions.role")),
            ],
        ),
        migrations.AddConstraint(
            model_name="rolefieldpermission",
            constraint=models.UniqueConstraint(fields=("role", "module_code", "field_key"), name="roles_permissions_role_module_field_uniq"),
        ),
        migrations.AddIndex(
            model_name="rolefieldpermission",
            index=models.Index(fields=["role", "module_code"], name="roles_permi_role_id_a66d0f_idx"),
        ),
    ]
