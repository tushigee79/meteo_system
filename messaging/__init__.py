from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class Thread(models.Model):
    """�"о�,оод �?а�,: нэг thread н�O 1:1 эсвэл жижиг багийн thread байж болно."""

    title = models.CharField(max_length=255, blank=True, null=True, verbose_name="�"а�?�?иг")
    created_at = models.DateTimeField(auto_now_add=True)

    # optional scoping (аймаг/байг�f�fллага �,үв�^ний thread �.ий�. боломж)
    aimag_fk = models.ForeignKey("inventory.Aimag", on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Аймаг/Нийслэл")
    org_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="�'айг�f�fллага (�,екс�,)")

    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="chat_threads", verbose_name="�z�?ол�?ог�?ид")

    class Meta:
        verbose_name = "Ча�, thread"
        verbose_name_plural = "12. �"о�,оод �?а�, (threads)"
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
        verbose_name = "�oессеж"
        verbose_name_plural = "12. �"о�,оод �?а�, (messages)"
        ordering = ("created_at",)

    def __str__(self):
        return f"{self.sender} @ {self.created_at}"


