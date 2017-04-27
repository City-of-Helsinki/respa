from django.contrib import admin
from .models import Comment


class CommentAdmin(admin.ModelAdmin):
    readonly_fields = ('created_at', 'created_by')


admin.site.register(Comment, CommentAdmin)
