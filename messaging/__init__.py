from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class Thread(models.Model):
    """Ð”Ð¾Ñ‚Ð¾Ð¾Ð´ Ñ‡Ð°Ñ‚: Ð½ÑÐ³ thread Ð½ÑŒ 1:1 ÑÑÐ²ÑÐ» Ð¶Ð¸Ð¶Ð¸Ð³ Ð±Ð°Ð³Ð¸Ð¹Ð½ thread Ð±Ð°Ð¹Ð¶ Ð±Ð¾Ð»Ð½Ð¾."""

    title = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ð“Ð°Ñ€Ñ‡Ð¸Ð³")
    created_at = models.DateTimeField(auto_now_add=True)

    # optional scoping (Ð°Ð¹Ð¼Ð°Ð³/Ð±Ð°Ð¹Ð³ÑƒÑƒÐ»Ð»Ð°Ð³Ð° Ñ‚Ò¯Ð²ÑˆÐ½Ð¸Ð¹ thread Ñ…Ð¸Ð¹Ñ… Ð±Ð¾Ð»Ð¾Ð¼Ð¶)
    aimag_fk = models.ForeignKey("inventory.Aimag", on_delete=models.SET_NULL, blank=True, null=True, verbose_name="ÐÐ¹Ð¼Ð°Ð³/ÐÐ¸Ð¹ÑÐ»ÑÐ»")
    org_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ð‘Ð°Ð¹Ð³ÑƒÑƒÐ»Ð»Ð°Ð³Ð° (Ñ‚ÐµÐºÑÑ‚)")

    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="chat_threads", verbose_name="ÐžÑ€Ð¾Ð»Ñ†Ð¾Ð³Ñ‡Ð¸Ð´")

    class Meta:
        verbose_name = "Ð§Ð°Ñ‚ thread"
        verbose_name_plural = "12. Ð”Ð¾Ñ‚Ð¾Ð¾Ð´ Ñ‡Ð°Ñ‚ (threads)"
        ordering = ("-created_at",)

    def __str__(self):
        return self.title or f"Thread #{self.id}"


class Message(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_messages")
    created_at = models.DateTimeField(default=timezone.now)
    text = models.TextField()
    is_system = models.BooleanField(default=False)

    class Meta:
        verbose_name = "ÐœÐµÑÑÐµÐ¶"
        verbose_name_plural = "12. Ð”Ð¾Ñ‚Ð¾Ð¾Ð´ Ñ‡Ð°Ñ‚ (messages)"
        ordering = ("created_at",)

    def __str__(self):
        return f"{self.sender} @ {self.created_at}"

