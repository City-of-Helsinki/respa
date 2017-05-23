from django.conf import settings
from django.contrib import admin
from .models import Comment


class CommentAdmin(admin.ModelAdmin):
    readonly_fields = ('created_at', 'created_by')

if getattr(settings, 'RESPA_COMMENTS_ENABLED', False):
    admin.site.register(Comment, CommentAdmin)
