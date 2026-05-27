import json
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.views import View
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from datastar_py import ServerSentEventGenerator as SSE
from datastar_py.django import DatastarResponse
from .models import Hierarchy, Link, UserPreference


class EditorView(LoginRequiredMixin, TemplateView):
    template_name = "bookmarks/main.html"

    def get(self, request, *args, **kwargs):
        if "active_folder_id" not in request.session:
            request.session["active_folder_id"] = None
            request.session["expanded_folders"] = []
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        active_folder_id = self.request.session.get("active_folder_id")
        expanded_folders = self.request.session.get("expanded_folders", [])

        # Get or create user preference
        preference, _ = UserPreference.objects.get_or_create(user=self.request.user)

        context["hierarchies"] = Hierarchy.objects.filter(
            parent__isnull=True
        ).prefetch_related("children", "links")
        context["active_folder_id"] = active_folder_id
        context["expanded_folders"] = expanded_folders
        context["preference"] = preference

        if active_folder_id is not None:
            try:
                folder = Hierarchy.objects.get(id=active_folder_id)
                folder_ids = self.get_all_hierarchy_ids(folder)
                context["links"] = Link.objects.filter(
                    hierarchy_id__in=folder_ids
                ).select_related("hierarchy")[:100]
            except Hierarchy.DoesNotExist:
                context["links"] = Link.objects.all().select_related("hierarchy")[:100]
        else:
            context["links"] = Link.objects.all().select_related("hierarchy")[:100]

        return context

    def get_all_hierarchy_ids(self, folder):
        ids = [folder.id]
        to_visit = list(folder.children.all())
        while to_visit:
            curr = to_visit.pop()
            ids.append(curr.id)
            to_visit.extend(curr.children.all())
        return ids


class FolderNavigationView(LoginRequiredMixin, View):
    def get(self, request, folder_id=None):
        expanded_folders = request.session.get("expanded_folders", [])
        active_folder_id = request.session.get("active_folder_id")

        # Toggle Expand/Collapse state and set current active node
        if folder_id is not None:
            active_folder_id = folder_id
            if folder_id in expanded_folders:
                expanded_folders.remove(folder_id)
            else:
                expanded_folders.append(folder_id)
        else:
            active_folder_id = None

        request.session["expanded_folders"] = expanded_folders
        request.session["active_folder_id"] = active_folder_id

        hierarchies = Hierarchy.objects.filter(parent__isnull=True).prefetch_related(
            "children", "links"
        )
        preference, _ = UserPreference.objects.get_or_create(user=request.user)

        if active_folder_id is not None:
            try:
                folder = Hierarchy.objects.get(id=active_folder_id)
                folder_ids = self.get_all_hierarchy_ids(folder)
                links = Link.objects.filter(hierarchy_id__in=folder_ids).select_related(
                    "hierarchy"
                )
            except Hierarchy.DoesNotExist:
                links = Link.objects.all().select_related("hierarchy")
        else:
            links = Link.objects.all().select_related("hierarchy")

        links = links[:100]

        context = {
            "hierarchies": hierarchies,
            "links": links,
            "active_folder_id": active_folder_id,
            "expanded_folders": expanded_folders,
            "preference": preference,
        }

        sidebar_html = render_to_string(
            "bookmarks/partials/collections_list.html", context, request=request
        )
        links_html = render_to_string(
            "bookmarks/partials/link_list_container.html", context, request=request
        )

        events = [SSE.patch_elements(sidebar_html), SSE.patch_elements(links_html)]
        return DatastarResponse(events)

    def get_all_hierarchy_ids(self, folder):
        ids = [folder.id]
        to_visit = list(folder.children.all())
        while to_visit:
            curr = to_visit.pop()
            ids.append(curr.id)
            to_visit.extend(curr.children.all())
        return ids


class SavePreferenceView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            pref, _ = UserPreference.objects.get_or_create(user=request.user)

            sidebar_width = data.get("sidebar_width")
            theme = data.get("theme")

            if sidebar_width is not None:
                pref.sidebar_width = int(sidebar_width)
            if theme is not None:
                pref.theme = str(theme)

            pref.save()
        except Exception:
            pass

        return DatastarResponse([])


@login_required
def bookmarks_sse(request):
    hierarchy_id = request.GET.get("hierarchy_id")

    if hierarchy_id:
        links = Link.objects.filter(hierarchy_id=hierarchy_id).select_related(
            "hierarchy"
        )
    else:
        links = Link.objects.all().select_related("hierarchy")[:100]

    html = render_to_string(
        "bookmarks/partials/link_list_container.html", {"links": links}
    )

    return DatastarResponse(SSE.patch_elements(html))
