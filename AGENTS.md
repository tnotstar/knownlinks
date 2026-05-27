# AGENTS.md

Welcome, Agent. This document contains precise technical context, architecture blueprints, guidelines, and execution strategies for modifying or extending the `knownlinks` repository. Refer to this document before making any changes.

---

## 🎯 Repository Specs & Architecture

* **Primary Stack**: Python `3.13+` | Django `6.0.5` | SQLite | Datastar `1.0.1` (SSE Hypermedia Protocol).
* **Environment & Package Manager**: Managed strictly via **Astral `uv`**. Always verify [`uv.lock`](file:///home/tnotstar/Workspaces/Personal/knownlinks/uv.lock) and [`pyproject.toml`](file:///home/tnotstar/Workspaces/Personal/knownlinks/pyproject.toml) before suggesting or executing environment setups.
* **Arch Style**: standard Django MVT with Datastar hypermedia reactivity.
* **Design Philosophy Constraints**:
  * Adhere to **SOLID principles** and Clean Code discipline.
  * Minimize third-party micro-dependencies.
  * Use **static type annotations** on all new Python methods and variables.
  * Standard logging: Never use `print()` or `sys.stdout` directly in controller code. Use Python standard `logging` or structured logs if possible.
  * Commit Message Convention: [Conventional Commits v1.0](https://www.conventionalcommits.org/en/v1.0.0/) (`type(scope): description`).

---

## 🛠️ Folder Tree & Structural Blueprint

```
knownlinks/
├── bookmarks/                  # Core application directory
│   ├── management/             # CLI Custom management commands
│   │   └── commands/           # import_bookmarks.py parser & merger
│   ├── migrations/             # Auto-generated SQLite schema migrations
│   ├── templates/bookmarks/    # Django dynamic HTML layouts
│   │   ├── partials/           # Granular sub-components loaded via SSE
│   │   ├── base.html           # Main HTML header, scripts, and Tailwind init
│   │   ├── login.html          # Authentication gate
│   │   └── main.html           # Desktop panel workspace layout
│   ├── admin.py                # Admin site registrations
│   ├── apps.py                 # Application metadata definition
│   ├── models.py               # ORM Database specifications
│   ├── urls.py                 # App specific URL routes
│   └── views.py                # Backend SSE controllers & UI views
├── config/                     # Settings and root configuration urls
├── pyproject.toml              # UV Project dependency constraints
└── uv.lock                     # UV Lock file
```

---

## ⚡ Datastar Reactive Flow Pattern

Reactivity in this application is handled purely by returning Server-Sent Events (SSE) from Django view actions. The client listens to the events, replacing or updating matching DOM nodes reactively.

### Flow Rules for UI Updates

1. **State Store (`data-store`)**:
   Bound in [`bookmarks/templates/bookmarks/main.html`](file:///home/tnotstar/Workspaces/Personal/knownlinks/bookmarks/main.html) using a JSON data store format:
   ```html
   <div data-store="{ active_folder_id: {{ active_folder_id|default:'null' }}, sidebar_width: {{ preference.sidebar_width }}, theme: '{{ preference.theme }}' }">
   ```
2. **Reactivity Triggers**:
   Elements trigger backend endpoints using custom Datastar attributes:
   * `@get('/endpoint')` or `@post('/endpoint')`
   * To bind user input to store signals, use `data-bind="signal_name"`.
3. **SSE Patch Responses**:
   The controller MUST return a `DatastarResponse` containing compiled list of events.
   ```python
   from datastar_py import ServerSentEventGenerator as SSE
   from datastar_py.django import DatastarResponse

   def my_view(request):
       # 1. Render sub-components to strings
       html_content = render_to_string("bookmarks/partials/my_component.html", context, request=request)
       
       # 2. Return SSE patch events
       events = [SSE.patch_elements(html_content)]
       return DatastarResponse(events)
   ```
4. **DOM IDs matching**:
   Ensure the root HTML elements in partials have identical `id` attributes to what needs to be replaced. For example, rendering `collections_list.html` will patch `<ul id="collections-list">`.

---

## 🗄️ Database Integrity & Constraints

Keep DB operations safe by utilizing Django ORM constraints:
* **Self-Referential Hierarchies**: `Hierarchy` uses unique constraints to guard against duplicate folders inside the same directory level:
  ```python
  models.UniqueConstraint(
      fields=["name", "parent"],
      name="unique_hierarchy_node",
      condition=models.Q(parent__isnull=False),
  )
  models.UniqueConstraint(
      fields=["name"],
      name="unique_hierarchy_root",
      condition=models.Q(parent__isnull=True),
  )
  ```
* **Bulk Operations safety**: When merging or batch inserting large collections, use `transaction.atomic()` context block and `bulk_create` with conflict resolution parameters:
  ```python
  Link.objects.bulk_create(
      links_to_create,
      batch_size=1000,
      update_conflicts=True,
      unique_fields=['url', 'hierarchy'],
      update_fields=['title', 'description', 'updated_at']
  )
  ```

---

## ⚙️ How to add standard features

### 1. Adding a New Partial View
1. Define the endpoint URL in [`bookmarks/urls.py`](file:///home/tnotstar/Workspaces/Personal/knownlinks/bookmarks/urls.py).
2. Create a specific sub-component file inside `bookmarks/templates/bookmarks/partials/` containing a root tag with a unique `id`.
3. Create a view class extending `LoginRequiredMixin` and `View` in [`bookmarks/views.py`](file:///home/tnotstar/Workspaces/Personal/knownlinks/bookmarks/views.py).
4. Fetch dynamic data, render the sub-component template, and return `DatastarResponse(SSE.patch_elements(rendered_string))`.

### 2. Modifying Database Models
1. Add/modify fields in [`bookmarks/models.py`](file:///home/tnotstar/Workspaces/Personal/knownlinks/bookmarks/models.py). Ensure constraints are added to `Meta.constraints` instead of using complex database triggers.
2. Run database migrations generation:
   ```bash
   uv run python manage.py makemigrations
   ```
3. Apply changes locally:
   ```bash
   uv run python manage.py migrate
   ```

---

## ⚠️ Gotchas & Pitfalls to Avoid

* **Tailwind Dynamic Class Names**: Since Tailwind is initialized as a client CDN stylesheet in [`base.html`](file:///home/tnotstar/Workspaces/Personal/knownlinks/bookmarks/base.html) with custom JavaScript configurations, avoid referencing color utility names that have not been registered inside the dynamic `tailwind.config` block.
* **Session Mutability in SSE**: Django views reading/writing state in sessions (`request.session`) might conflict if multiple SSE events fire concurrently. Ensure requests modifying active state parameters are serialized properly by the browser.
* **Bulk Create Return Values**: Note that `bulk_create` with SQLite does not populated Primary Keys (`id`) on returned instances if the rows were updated rather than inserted. Rely on unique constraints (`unique_fields=['url', 'hierarchy']`) for matching lookups.
