import django.db.models.deletion
from django.db import migrations, models


def forwards_link_profile(apps, schema_editor):
    Profile = apps.get_model("roles_permissions", "DesignationPermissionProfile")
    Link = apps.get_model("roles_permissions", "DesignationModulePermission")

    designation_ids = set(
        Link.objects.exclude(designation_id__isnull=True).values_list("designation_id", flat=True)
    )
    for did in designation_ids:
        Profile.objects.get_or_create(designation_id=did)

    for link in Link.objects.all():
        if link.designation_id:
            profile = Profile.objects.get(designation_id=link.designation_id)
            link.profile_id = profile.pk
            link.save(update_fields=["profile_id"])


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("roles_permissions", "0005_alter_userrole_options"),
        ("staff", "0004_alter_department_unique_together_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="DesignationPermissionProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "designation",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="module_permission_profile",
                        to="staff.designation",
                    ),
                ),
            ],
            options={
                "verbose_name": "Designation permission",
                "verbose_name_plural": "Designation permissions",
            },
        ),
        migrations.AddField(
            model_name="designationmodulepermission",
            name="profile",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="module_links",
                to="roles_permissions.designationpermissionprofile",
            ),
        ),
        migrations.RunPython(forwards_link_profile, backwards_noop),
        migrations.RemoveConstraint(
            model_name="designationmodulepermission",
            name="roles_permissions_designation_module_uniq",
        ),
        migrations.RemoveField(
            model_name="designationmodulepermission",
            name="designation",
        ),
        migrations.AlterField(
            model_name="designationmodulepermission",
            name="profile",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="module_links",
                to="roles_permissions.designationpermissionprofile",
            ),
        ),
        migrations.AddConstraint(
            model_name="designationmodulepermission",
            constraint=models.UniqueConstraint(
                fields=("profile", "module"),
                name="roles_permissions_profile_module_uniq",
            ),
        ),
        migrations.DeleteModel(
            name="DesignationPermissionSetup",
        ),
    ]
