from django.db import models
from django.contrib.auth.models import User


class Hierarchy(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hierarchy"
        verbose_name_plural = "Hierarchies"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "parent"],
                name="unique_hierarchy_node",
                condition=models.Q(parent__isnull=False),
            ),
            models.UniqueConstraint(
                fields=["name"],
                name="unique_hierarchy_root",
                condition=models.Q(parent__isnull=True),
            ),
        ]

    def __str__(self):
        return self.name


class Link(models.Model):
    url = models.URLField(max_length=2000)
    title = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)
    hierarchy = models.ForeignKey(
        Hierarchy, on_delete=models.CASCADE, related_name="links"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "link"
        constraints = [
            models.UniqueConstraint(
                fields=["url", "hierarchy"], name="unique_folder_link"
            )
        ]

    def __str__(self):
        return self.title


class UserPreference(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="preference"
    )
    sidebar_width = models.IntegerField(default=20)  # expressed as width percentage
    theme = models.CharField(
        max_length=10,
        choices=[("dark", "Dark"), ("light", "Light"), ("system", "System")],
        default="dark",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_preference"

    def __str__(self):
        return f"{self.user.username}'s preference"
