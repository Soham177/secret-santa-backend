from django.contrib.auth.models import User
from django.db import models


class Participant(models.Model):
    # the primary key is the user's id, so the id in the urls is just the user id
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    wishlist = models.TextField(blank=True, default="")
    joined_at = models.DateTimeField(auto_now_add=True)
    # who this person gives a gift to. empty until the draw runs.
    # OneToOne so a person can only be somebody's giftee once
    giftee = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.SET_NULL
    )

    def display_name(self):
        return self.user.first_name or self.user.username

    def __str__(self):
        return self.display_name()


class DrawState(models.Model):
    # there is only ever one row of this, fetched with DrawState.get()
    locked = models.BooleanField(default=False)
    drawn = models.BooleanField(default=False)
    drawn_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def get(cls):
        state, _ = cls.objects.get_or_create(pk=1)
        return state
