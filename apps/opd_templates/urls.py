from django.urls import path
from . import views

urlpatterns = [
    # Template CRUD — matches Node.js server.js routes exactly
    path("api/templates", views.list_templates, name="opd-templates-list"),
    path("api/templates/update-layout", views.update_layout, name="opd-templates-update-layout"),
    path("admin/templates/upload", views.upload_template, name="opd-templates-upload"),

    # Print slip (replicates GET/POST /api/print from Node.js)
    path("api/print", views.print_slip, name="opd-print"),

    # Background image serving (replicates GET /template/:name from Node.js)
    path("template/<str:name>", views.template_bg_image, name="opd-template-bg"),

    # Health check
    path("api/health", views.health, name="opd-health"),
]
