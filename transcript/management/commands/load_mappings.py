import csv
from django.core.management.base import BaseCommand
from transcript.models import GraduateAttribute, CharacterStrength, AttributeStrengthMap

class Command(BaseCommand):
    help = 'Load Graduate Attribute → Character Strength mappings from a CSV file'

    def handle(self, *args, **kwargs):
        path = 'transcript/mapping.csv'

        try:
            with open(path, newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                self.stdout.write("Reading CSV and importing mappings...")

                for row in reader:
                    attribute_name = row['Column 1'].strip()
                    if not attribute_name:
                        continue  # skip blank rows

                    attribute, _ = GraduateAttribute.objects.get_or_create(name=attribute_name)

                    for strength_name, val in row.items():
                        if strength_name == 'Column 1':
                            continue

                        try:
                            weight = float(val.strip())
                        except (ValueError, AttributeError):
                            continue  # skip blanks or invalid numbers

                        if weight > 0:
                            strength, _ = CharacterStrength.objects.get_or_create(name=strength_name.strip())
                            AttributeStrengthMap.objects.update_or_create(
                                graduate_attribute=attribute,
                                character_strength=strength,
                                defaults={'weight': weight}
                            )

                self.stdout.write(self.style.SUCCESS("Mapping data imported successfully."))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"File not found: {path}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error occurred: {str(e)}"))
