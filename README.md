# The `knownlinks` Project

`knownlinks` is a highly responsive, self-hosted bookmark and hierarchy manager designed with the aesthetic and workflow of premium tools like Raindrop.io. It leverages **Django 6** on the backend and **Datastar** on the frontend, establishing a reactive, single-page application (SPA) experience using hypermedia controls and Server-Sent Events (SSE), without the overhead of heavy JavaScript build pipelines.

---

## Architectural Core

The architecture is built on three main pillars:
1. **Django 6 & SQLite**: Serves as the robust, relationally structured backend storage and session controller.
2. **Datastar (Hypermedia & SSE)**: Utilizes `datastar-py` and Server-Sent Events to dynamically patch, merge, or remove HTML elements directly from Django views to the DOM.
3. **Dynamic Responsive Tailwind UI**: Incorporates draggable sidebar layout resizing and full theme preference persistence (Light/Dark/System), loading configuration dynamically on bootstrap.

```
                  ┌────────────────────────────────────────────────────────┐
                  │                        Browser                         │
                  └──────────┬──────────────────────────▲──────────────────┘
                             │                          │
                    HTTP POST (Save Theme)       SSE Patch Elements
                    HTTP GET (Folder Navigate)   (Datastar Streams)
                             │                          │
                             ▼                          │
                  ┌─────────────────────────────────────┴──────────────────┐
                  │                 Django View Controller                 │
                  └──────────┬─────────────────────────────────────────────┘
                             │
                      ORM Operations
                             │
                             ▼
                  ┌────────────────────────────────────────────────────────┐
                  │                   SQLite DB Engine                     │
                  └────────────────────────────────────────────────────────┘
```

---

## Database Schema & Models

The repository uses three core models located in [`bookmarks/models.py`](file:///home/tnotstar/Workspaces/Personal/knownlinks/bookmarks/models.py):

### 1. `Hierarchy`
Represents the bookmark folders arranged in an arbitrary-depth tree structure.
* **Fields**:
  * `name` (`CharField`): Folder name.
  * `parent` (`ForeignKey('self')`): Self-referential nullable link representing the parent node.
  * `created_at` / `updated_at`: Dynamic tracking timestamps.
* **Constraints**:
  * `unique_hierarchy_node`: Ensures a directory cannot contain two subdirectories with the identical name.
  * `unique_hierarchy_root`: Guarantees folder name uniqueness at the root level.

### 2. `Link`
Represents individual bookmarked links residing inside folders.
* **Fields**:
  * `url` (`URLField`): The absolute URL.
  * `title` (`CharField`): Custom bookmark title.
  * `description` (`TextField`): Optional annotations or page summaries.
  * `hierarchy` (`ForeignKey(Hierarchy)`): Reference to the directory it resides in.
* **Constraints**:
  * `unique_folder_link`: Enforces uniqueness of a URL within a specific folder.

### 3. `UserPreference`
Saves display settings and configurations per user.
* **Fields**:
  * `user` (`OneToOneField(User)`): Associated user profile.
  * `sidebar_width` (`IntegerField`): Left navigation panel width represented in viewport percentage (constrained between 15% and 45% on the frontend).
  * `theme` (`CharField`): Selection choice from `dark`, `light`, or `system`.

---

## Ingestion Engine: `import_bookmarks`

The platform includes a high-performance Netscape HTML Bookmark importer command. It implements:
* **Stream Parsing**: Reads standard Netscape HTML files efficiently without loading the entire document into memory.
* **Hierarchy Resolution**: Tracks directories using an execution stack to map parent/child tree nodes accurately in real-time.
* **Transactional Bulk Merging**: Employs `transaction.atomic` and bulk DB operations (`bulk_create` with `update_conflicts=True`) to resolve duplicates without throwing key constraint failures, allowing incremental/delta imports.

```bash
# Ingest and merge bookmarks
uv run python manage.py import_bookmarks <path_to_bookmark_file.html>
```

---

## Setup & Execution

### 1. Installation & Environment Sync
The project dependencies and runtime virtual environment are managed via Astral `uv`. To synchronize the virtual environment:
```bash
uv sync
```

### 2. Run Database Migrations
Initialize your local SQLite database structure:
```bash
uv run python manage.py migrate
```

### 3. Create Superuser (Admin Access)
To log in and populate dynamic settings:
```bash
uv run python manage.py createsuperuser
```

### 4. Seed with Demo Data
To test the ingestion system, you can import the preconfigured mock structure:
```bash
uv run python manage.py import_bookmarks demo.html
```

### 5. Start Development Server
```bash
uv run python manage.py runserver
```
Visit the server at `http://127.0.0.1:8000/`. You will be redirected to `/login/` before entering the editor view.

---

## Theme & Layout Engine
The interface handles styling via dynamic, responsive Tailwind colors injected in [`bookmarks/templates/bookmarks/base.html`](file:///home/tnotstar/Workspaces/Personal/knownlinks/bookmarks/templates/bookmarks/base.html):
* Active user preference (`preference.theme`) determines the HSL palette variables (`bgSidebar`, `bgMain`, `borderColor`, etc.) before booting the layout.
* Custom draggable resize scripts automatically sync panel percentages to the DB on mouse release via reactive Datastar signals.
