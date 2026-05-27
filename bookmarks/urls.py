from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "bookmarks"

urlpatterns = [
    path(
        "",
        views.EditorView.as_view(),
        name="editor",
    ),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="bookmarks/login.html"),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path(
        "sse/",
        views.bookmarks_sse,
        name="bookmarks_sse",
    ),
    path(
        "navigate/<int:folder_id>/",
        views.FolderNavigationView.as_view(),
        name="navigate",
    ),
    path(
        "navigate/all/",
        views.FolderNavigationView.as_view(),
        name="navigate_all",
    ),
    path(
        "preference/save/",
        views.SavePreferenceView.as_view(),
        name="save_preference",
    ),
]
