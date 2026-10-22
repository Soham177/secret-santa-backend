from django.urls import path

from . import views

urlpatterns = [
    path("auth/signup", views.signup),
    path("auth/login", views.login_view),
    path("auth/logout", views.logout_view),
    path("draw/run", views.run_draw),
    path("draw/lock", views.lock_draw),
    path("draw/status", views.draw_status),
    path("participants", views.participants),
    path("participant/<int:user_id>", views.participant_detail),
    path("participant/<int:user_id>/wishlist", views.update_wishlist),
    path("my-giftee", views.my_giftee),
    path("my-wishlist-giver", views.my_wishlist_giver),
]
