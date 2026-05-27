import re
import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from bookmarks.models import Hierarchy, Link

class Command(BaseCommand):
    help = 'Import and merge bookmarks from a Netscape HTML Bookmark file'

    def add_arguments(self, parser):
        parser.add_argument('filepath', type=str, help='Path to the Netscape HTML bookmark file')

    def handle(self, *args, **options):
        filepath = options['filepath']

        # Pre-compile Regexes
        folder_re = re.compile(r'<H3(?:\s+[^>]*)?>(.*?)</H3>', re.IGNORECASE)
        link_re = re.compile(r'<A\s+HREF="([^"]+)"(?:\s+[^>]*)?>(.*?)</A>', re.IGNORECASE)
        date_re = re.compile(r'ADD_DATE="(\d+)"', re.IGNORECASE)
        dd_re = re.compile(r'^\s*<DD>(.*)', re.IGNORECASE)
        dl_open_re = re.compile(r'<DL>', re.IGNORECASE)
        dl_close_re = re.compile(r'</DL>', re.IGNORECASE)

        # Parse & DB Upsert state
        stack = []
        current_hierarchy = None
        last_created_hierarchy = None
        
        links_to_create = []
        links_map = {}
        
        folder_count = 0

        try:
            with transaction.atomic():
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line_stripped = line.strip()

                        # 1. Check for Description (<DD>)
                        dd_match = dd_re.match(line_stripped)
                        if dd_match and links_to_create:
                            description_text = dd_match.group(1).strip()
                            description_text = re.sub(r'<[^>]+>', '', description_text) # strip HTML tag residue
                            links_to_create[-1].description = description_text
                            continue

                        # 2. Check for DL Open (Enter Folder)
                        if dl_open_re.search(line_stripped):
                            stack.append(current_hierarchy)
                            if last_created_hierarchy:
                                current_hierarchy = last_created_hierarchy
                                last_created_hierarchy = None
                            continue

                        # 3. Check for DL Close (Exit Folder)
                        if dl_close_re.search(line_stripped):
                            if stack:
                                current_hierarchy = stack.pop()
                            continue

                        # 4. Check for Folder Definition (<H3>)
                        folder_match = folder_re.search(line_stripped)
                        if folder_match:
                            name = folder_match.group(1).strip()
                            name = re.sub(r'<[^>]+>', '', name) # Strip nested tag fragments
                            
                            # Parse optional ADD_DATE
                            date_match = date_re.search(line_stripped)
                            created_at = timezone.now()
                            if date_match:
                                try:
                                    created_at = timezone.make_aware(
                                        datetime.datetime.fromtimestamp(int(date_match.group(1)), tz=datetime.timezone.utc)
                                    )
                                except Exception:
                                    pass

                            # Immediate DB upsert to obtain correct parent node context
                            hierarchy, created = Hierarchy.objects.update_or_create(
                                name=name,
                                parent=current_hierarchy,
                                defaults={'updated_at': timezone.now()}
                            )
                            
                            if created:
                                Hierarchy.objects.filter(pk=hierarchy.pk).update(created_at=created_at)
                                folder_count += 1
                                
                            last_created_hierarchy = hierarchy
                            continue

                        # 5. Check for Bookmark Link (<A>)
                        link_match = link_re.search(line_stripped)
                        if link_match:
                            # Fallback if link is encountered at the root structure without folders
                            if current_hierarchy is None:
                                current_hierarchy, _ = Hierarchy.objects.get_or_create(
                                    name='Unsorted',
                                    parent=None
                                )

                            url = link_match.group(1).strip()
                            title = link_match.group(2).strip()
                            title = re.sub(r'<[^>]+>', '', title)

                            # Parse optional ADD_DATE
                            date_match = date_re.search(line_stripped)
                            created_at = timezone.now()
                            if date_match:
                                try:
                                    created_at = timezone.make_aware(
                                        datetime.datetime.fromtimestamp(int(date_match.group(1)), tz=datetime.timezone.utc)
                                    )
                                except Exception:
                                    pass

                            link_key = (url, current_hierarchy.id)
                            link_obj = Link(
                                url=url,
                                title=title,
                                hierarchy=current_hierarchy,
                                created_at=created_at,
                                updated_at=timezone.now()
                            )

                            # Ensure unique links in the list to prevent batch-level conflict issues
                            if link_key in links_map:
                                idx = links_map[link_key]
                                links_to_create[idx] = link_obj
                            else:
                                links_map[link_key] = len(links_to_create)
                                links_to_create.append(link_obj)
                            continue

                # Batch Upsert accumulated links
                if links_to_create:
                    Link.objects.bulk_create(
                        links_to_create,
                        batch_size=1000,
                        update_conflicts=True,
                        unique_fields=['url', 'hierarchy'],
                        update_fields=['title', 'description', 'updated_at']
                    )

        except FileNotFoundError:
            raise CommandError(f"Bookmark file not found: {filepath}")
        except Exception as e:
            raise CommandError(f"Error parsing and merging bookmarks: {e}")

        self.stdout.write(self.style.SUCCESS(
            f"Successfully processed {folder_count} folders and merged/inserted {len(links_to_create)} links."
        ))
