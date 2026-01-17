from django.contrib import admin

from .models import Thread, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_at", "aimag_fk", "org_name")
    search_fields = ("title", "org_name")
    list_filter = ("aimag_fk",)
    filter_horizontal = ("participants",)
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "thread", "sender", "created_at", "is_system")
    search_fields = ("text", "sender__username")
    list_filter = ("is_system",)
