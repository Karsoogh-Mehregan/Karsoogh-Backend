import csv
import io
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import City, Province, School, User


ACADEMIC_YEAR_MAP = {
    "هفتم": 7,
    "هشتم": 8,
    "نهم": 9,
}


class Command(BaseCommand):
    help = "Import users from a CSV file with columns: نام, نام خانوادگی, username, password, کد ملی (optional), لیست استان و شهرستان, پایه تحصیلی, موبایل (optional)"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to the CSV file")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate without saving to the database",
        )
        parser.add_argument(
            "--default-password",
            type=str,
            default=None,
            help="Default password for all imported users. If not set, national_code is used.",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_file"]
        dry_run = options["dry_run"]
        default_password = options["default_password"]

        try:
            with open(csv_path, "r", encoding="utf-8-sig") as f:
                content = f.read()
        except FileNotFoundError:
            raise CommandError(f"File not found: {csv_path}")

        reader = csv.DictReader(io.StringIO(content))

        rows = []
        for i, raw_row in enumerate(reader, start=2):  # start=2 because row 1 is header
            # Strip whitespace from header keys to avoid mismatch
            row = {k.strip(): v for k, v in raw_row.items() if k}
            first_name = row.get("first_name", "").strip()
            last_name = row.get("last_name", "").strip()
            username = row.get("username", "").strip()
            password = row.get("password", "").strip()
            national_code = row.get("national_code", "").strip() or None
            location_raw = row.get("location", "").strip()
            academic_year_raw = row.get("academic_year", "").strip()
            phone = row.get("phone", "").strip() or None

            # Skip empty rows
            if not any([first_name, last_name, username]):
                self.stdout.write(
                    self.style.WARNING(f"Row {i}: Skipping empty row")
                )
                continue

            # Validate required fields
            missing = []
            if not first_name:
                missing.append("نام")
            if not last_name:
                missing.append("نام خانوادگی")
            if not username:
                missing.append("username")
            if not password:
                missing.append("password")
            if missing:
                self.stdout.write(
                    self.style.ERROR(
                        f"Row {i}: Missing required fields: {', '.join(missing)} — skipping"
                    )
                )
                continue

            # Parse location: "اداره کل ... استان X, اداره ... ناحیه Y, جنسیت, مدرسه"
            province_name, city_name, school_name = self._parse_location(location_raw)

            # Parse academic year
            academic_year = ACADEMIC_YEAR_MAP.get(academic_year_raw)
            if academic_year is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"Row {i}: Unknown academic year '{academic_year_raw}', defaulting to 7"
                    )
                )
                academic_year = 7

            rows.append(
                {
                    "row_num": i,
                    "first_name": first_name,
                    "last_name": last_name,
                    "username": username,
                    "password": password,
                    "national_code": national_code,
                    "phone": phone,
                    "province_name": province_name,
                    "city_name": city_name,
                    "school_name": school_name,
                    "academic_year": academic_year,
                }
            )

        if not rows:
            self.stdout.write(self.style.WARNING("No valid rows found in CSV."))
            return

        self.stdout.write(f"Found {len(rows)} valid rows to import.")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("[DRY RUN] No changes made."))
            for r in rows:
                self.stdout.write(
                    f"  Row {r['row_num']}: {r['first_name']} {r['last_name']} "
                    f"(user: {r['username']}) — {r['province_name']} / {r['city_name']} / {r['school_name']} "
                    f"— Grade {r['academic_year']} — NC: {r['national_code'] or '-'} — Phone: {r['phone'] or '-'}"
                )
            return

        created_count = 0
        skipped_count = 0
        error_count = 0

        with transaction.atomic():
            for r in rows:
                row_num = r["row_num"]

                # Check for existing user
                if User.objects.filter(username=r["username"]).exists():
                    self.stdout.write(
                        self.style.WARNING(
                            f"Row {row_num}: User with username={r['username']} already exists — skipping"
                        )
                    )
                    skipped_count += 1
                    continue

                if r["national_code"] and User.objects.filter(national_code=r["national_code"]).exists():
                    self.stdout.write(
                        self.style.WARNING(
                            f"Row {row_num}: User with national_code={r['national_code']} already exists — skipping"
                        )
                    )
                    skipped_count += 1
                    continue

                if r["phone"] and User.objects.filter(phone=r["phone"]).exists():
                    self.stdout.write(
                        self.style.WARNING(
                            f"Row {row_num}: User with phone={r['phone']} already exists — skipping"
                        )
                    )
                    skipped_count += 1
                    continue

                # Get or create Province, City, School
                school = None
                if r["province_name"] and r["city_name"] and r["school_name"]:
                    try:
                        province, _ = Province.objects.get_or_create(
                            title=r["province_name"]
                        )
                        city, _ = City.objects.get_or_create(
                            title=r["city_name"], defaults={"province": province}
                        )
                        school, _ = School.objects.get_or_create(
                            title=r["school_name"], defaults={"city": city}
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_num}: Error creating Province/City/School: {e}"
                            )
                        )
                        error_count += 1
                        continue

                password = default_password if default_password else r["password"]

                try:
                    user = User.objects.create_user(
                        username=r["username"],
                        password=password,
                        first_name=r["first_name"],
                        last_name=r["last_name"],
                        national_code=r["national_code"],
                        phone=r["phone"],
                        Academic_Year=r["academic_year"],
                        school=school,
                    )
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Row {row_num}: Created user {user.first_name} {user.last_name} (username: {user.username})"
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Row {row_num}: Error creating user: {e}"
                        )
                    )
                    error_count += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Import complete: {created_count} created, {skipped_count} skipped, {error_count} errors")
        )

    def _parse_location(self, location_raw: str) -> tuple[str, str, str]:
        """
        Parse the location field:
        "اداره کل آموزش و پرورش استان خوزستان, اداره آموزش و پرورش ناحیه اهواز.ناحيه 4, پسر, شهيد بهشتي"

        Returns (province_name, city_name, school_name).
        """
        if not location_raw:
            return ("", "", "")

        parts = [p.strip() for p in location_raw.split(",")]
        if len(parts) < 4:
            return ("", "", "")

        province_part = parts[0]  # "اداره کل آموزش و پرورش استان خوزستان"
        city_part = parts[1]      # "اداره آموزش و پرورش ناحیه اهواز.ناحيه 4"
        # parts[2] is gender (پسر/دختر) — not stored in User model
        school_name = parts[3].strip()  # "شهيد بهشتي"

        # Extract province name after "استان"
        province_name = ""
        province_match = re.search(r"استان\s+(.+)", province_part)
        if province_match:
            province_name = province_match.group(1).strip()

        # Extract city name after "ناحیه" or "ناحيه"
        city_name = ""
        city_match = re.search(r"ناح[یي]ه\s+(.+)", city_part)
        if city_match:
            city_name = city_match.group(1).strip()

        return (province_name, city_name, school_name)
