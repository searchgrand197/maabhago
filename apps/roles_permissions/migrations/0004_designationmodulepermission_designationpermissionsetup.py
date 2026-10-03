import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("roles_permissions", "0003_rename_roles_permi_role_id_a66d0f_idx_roles_permi_role_id_e90b38_idx"),
        ("staff", "0004_alter_department_unique_together_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="DesignationModulePermission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True)),
                (
                    "designation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="module_permissions",
                        to="staff.designation",
                    ),
                ),
                (
                    "module",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="designation_permissions",
                        to="roles_permissions.module",
                    ),
                ),
            ],
            options={
                "verbose_name": "Module link",
                "verbose_name_plural": "Module links",
            },
        ),
        migrations.AddConstraint(
            model_name="designationmodulepermission",
            constraint=models.UniqueConstraint(
                fields=("designation", "module"),
                name="roles_permissions_designation_module_uniq",
            ),
        ),
        migrations.CreateModel(
            name="DesignationPermissionSetup",
            fields=[],
            options={
                "verbose_name": "Designation permission",
                "verbose_name_plural": "Designation permissions",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("staff.designation",),
        ),
    ]
