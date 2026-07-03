import csv
import io
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth.hashers import make_password

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
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing users instead of skipping them. Users are matched by username.",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_file"]
        dry_run = options["dry_run"]
        default_password = options["default_password"]
        update_mode = options["update"]

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
            if not password and not update_mode:
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

        # Pre-fetch existing unique fields into memory sets for O(1) lookups
        existing_usernames = set(User.objects.values_list('username', flat=True))
        existing_national_codes = set(
            User.objects.exclude(national_code__isnull=True)
            .exclude(national_code="")
            .values_list('national_code', flat=True)
        )
        existing_phones = set(
            User.objects.exclude(phone__isnull=True)
            .exclude(phone="")
            .values_list('phone', flat=True)
        )

        # Pre-fetch users by username for update mode
        users_by_username = {}
        if update_mode:
            usernames_in_csv = {r['username'] for r in rows}
            users_by_username = {
                u.username: u
                for u in User.objects.filter(username__in=usernames_in_csv)
            }

        # Pre-fetch location models into memory to avoid per-row queries
        provinces_cache = {p.title: p for p in Province.objects.all()}
        cities_cache = {(c.title, c.province_id): c for c in City.objects.all()}
        schools_cache = {(s.title, s.city_id): s for s in School.objects.all()}

        users_to_create = []
        users_to_update = []
        skipped_count = 0
        updated_count = 0
        created_count = 0
        error_count = 0

        mode_msg = "UPDATE mode" if update_mode else "INSERT mode"
        self.stdout.write(f"Processing rows in {mode_msg}...")

        with transaction.atomic():
            for r in rows:
                row_num = r["row_num"]

                # 1. Check for existing users in memory
                if r["username"] in existing_usernames:
                    if update_mode:
                        # Update existing user
                        user = users_by_username.get(r["username"])
                        if user:
                            # Update fields that exist in CSV
                            user.first_name = r["first_name"]
                            user.last_name = r["last_name"]
                            user.national_code = r["national_code"]
                            user.phone = r["phone"]
                            user.Academic_Year = r["academic_year"]

                            # Only update password if explicitly provided
                            if r["password"]:
                                user.password = make_password(r["password"])

                            # Update school if provided
                            try:
                                school = self._resolve_school(
                                    r["province_name"],
                                    r["city_name"],
                                    r["school_name"],
                                    provinces_cache,
                                    cities_cache,
                                    schools_cache,
                                )
                            except Exception as e:
                                self.stdout.write(self.style.ERROR(f"Row {row_num}: Error creating Province/City/School: {e}"))
                                error_count += 1
                                continue

                            user.school = school
                            users_to_update.append(user)
                            updated_count += 1
                            self.stdout.write(f"Row {row_num}: Updating user '{r['username']}'")
                            continue
                    else:
                        self.stdout.write(self.style.WARNING(f"Row {row_num}: User with username={r['username']} already exists — skipping"))
                        skipped_count += 1
                        continue

                if r["national_code"] and r["national_code"] in existing_national_codes:
                    self.stdout.write(self.style.WARNING(f"Row {row_num}: User with national_code={r['national_code']} already exists — skipping"))
                    skipped_count += 1
                    continue

                if r["phone"] and r["phone"] in existing_phones:
                    self.stdout.write(self.style.WARNING(f"Row {row_num}: User with phone={r['phone']} already exists — skipping"))
                    skipped_count += 1
                    continue

                # 2. Resolve or create Province, City, School on the fly and update caches
                try:
                    school = self._resolve_school(
                        r["province_name"],
                        r["city_name"],
                        r["school_name"],
                        provinces_cache,
                        cities_cache,
                        schools_cache,
                    )
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Row {row_num}: Error creating Province/City/School: {e}"))
                    error_count += 1
                    continue

                # 3. Prepare User instance
                raw_password = default_password or r["password"] or username
                
                user = User(
                    username=r["username"],
                    password=make_password(raw_password),
                    first_name=r["first_name"],
                    last_name=r["last_name"],
                    national_code=r["national_code"],
                    phone=r["phone"],
                    Academic_Year=r["academic_year"],
                    school=school,
                )
                users_to_create.append(user)
                
                # Add to existing sets so duplicates within the SAME CSV are skipped
                existing_usernames.add(r["username"])
                if r["national_code"]:
                    existing_national_codes.add(r["national_code"])
                if r["phone"]:
                    existing_phones.add(r["phone"])

            # 4. Bulk Create Users
            created_count = len(users_to_create)
            if users_to_create:
                self.stdout.write(f"Bulk inserting {created_count} users into the database...")
                User.objects.bulk_create(users_to_create, batch_size=1000)

            # 5. Bulk Update Users
            if users_to_update:
                self.stdout.write(f"Bulk updating {len(users_to_update)} users in the database...")
                User.objects.bulk_update(
                    users_to_update,
                    ['first_name', 'last_name', 'national_code', 'phone', 'Academic_Year', 'school'],
                    batch_size=1000
                )

        self.stdout.write("")
        result_msg = f"Import complete: {created_count} created"
        if update_mode:
            result_msg += f", {updated_count} updated"
        result_msg += f", {skipped_count} skipped, {error_count} errors"
        self.stdout.write(self.style.SUCCESS(result_msg))

    def _resolve_school(
        self,
        province_name: str,
        city_name: str,
        school_name: str,
        provinces_cache: dict,
        cities_cache: dict,
        schools_cache: dict,
    ):
        """
        Resolve or create Province, City, School on the fly and update caches.
        Returns the School instance or None.
        """
        if not (province_name and city_name and school_name):
            return None

        province = provinces_cache.get(province_name)
        if not province:
            province = Province.objects.create(title=province_name)
            provinces_cache[province_name] = province

        city_key = (city_name, province.id)
        city = cities_cache.get(city_key)
        if not city:
            city = City.objects.create(title=city_name, province=province)
            cities_cache[city_key] = city

        school_key = (school_name, city.id)
        school = schools_cache.get(school_key)
        if not school:
            school = School.objects.create(title=school_name, city=city)
            schools_cache[school_key] = school

        return school

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
