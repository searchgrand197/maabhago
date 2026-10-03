from django.db import models


def template_image_upload_path(instance, filename):
    import os
    ext = os.path.splitext(filename)[1].lower() or ".png"
    safe_key = str(instance.key).lower().replace(" ", "-")
    return f"opd_templates/{safe_key}-bg{ext}"


class OPDTemplate(models.Model):
    """
    Stores an OPD print template (previously managed by the Node.js server.js).
    Each template has a unique key (e.g. 'single', 'holi'), a human-readable name,
    a JSON layout (fields, notes, printOffsetX, printOffsetY, backgroundDataUrl, etc.),
    and an optional background image file.
    """

    key = models.SlugField(unique=True, max_length=120)
    name = models.CharField(max_length=255)
    layout = models.JSONField(default=dict, blank=True)
    background_image = models.ImageField(
        upload_to=template_image_upload_path,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]
        verbose_name = "OPD Template"
        verbose_name_plural = "OPD Templates"

    def __str__(self):
        return f"{self.name} ({self.key})"
