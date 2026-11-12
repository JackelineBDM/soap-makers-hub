"""Load the starter soaps and recipes once, if the shop is empty."""
import json
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from recipes.models import Category, Recipe
from shop.models import Product

SEED_FILE = Path(__file__).resolve().parents[2] / "seed" / "initial_data.json"


def attach_image(obj, name):
    """Upload the local photo for obj (goes to Cloudinary when live)."""
    path = Path(settings.BASE_DIR) / "media" / name
    if name and path.exists():
        with open(path, "rb") as photo:
            obj.image.save(path.name, File(photo), save=True)


class Command(BaseCommand):
    """Create the starter products and recipes if they are missing."""

    help = "Load starter soaps and recipes from shop/seed/initial_data.json"

    def handle(self, *args, **options):
        if not SEED_FILE.exists():
            self.stdout.write("No seed file, nothing to do.")
            return
        rows = json.loads(SEED_FILE.read_text())
        categories = {}
        for row in rows:
            if row["model"] == "recipes.category":
                fields = row["fields"]
                categories[row["pk"]], _ = Category.objects.get_or_create(
                    name=fields["name"],
                    defaults={"friendly_name": fields["friendly_name"]},
                )
        created = 0
        for row in rows:
            fields = dict(row["fields"])
            image = fields.pop("image", None)
            fields.pop("created_at", None)
            fields.pop("created_by", None)
            if row["model"] == "shop.product":
                model, key = Product, "name"
            elif row["model"] == "recipes.recipe":
                model, key = Recipe, "title"
                fields["category"] = categories.get(fields.get("category"))
            else:
                continue
            if model.objects.filter(**{key: fields[key]}).exists():
                continue
            obj = model.objects.create(**fields)
            attach_image(obj, image)
            created += 1
        self.stdout.write(f"Seed finished: {created} new items.")
