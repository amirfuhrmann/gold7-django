from django.urls import path

from . import views
from .invitation_views import accept_invitation_view

app_name = "account"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("invite/<uuid:token>/", accept_invitation_view, name="accept-invitation"),
]
