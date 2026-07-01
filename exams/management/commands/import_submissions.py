"""
Management command to bulk-import submissions from a CSV + file folder.

Usage:
    python manage.py import_submissions \
        --exam-id 3 \
        --csv /path/to/submissions.csv \
        --files-dir /path/to/submissions_folder

CSV format (no header row expected, but tolerated if first cell isn't a valid username):
    username, file_for_q1, file_for_q2, ...

    Each file column value is a relative path like: <username>/<filename>
    The columns (after username) map to the exam's questions sorted by ID ascending.

Files directory structure:
    <files-dir>/
        <username1>/
            answer1.pdf
            answer2.pdf
        <username2>/
            ...
"""

import csv
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from exams.models import ExamModel, QuestionModel, Submission


class Command(BaseCommand):
    help = "Import submissions from a CSV file and a folder of user files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--exam-id",
            type=int,
            required=True,
            help="ID of the exam these submissions belong to.",
        )
        parser.add_argument(
            "--csv",
            type=str,
            required=True,
            help="Path to the CSV file (columns: username, file_q1, file_q2, ...).",
        )
        parser.add_argument(
            "--files-dir",
            type=str,
            required=True,
            help="Path to the root folder containing <username>/<file> sub-folders.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate everything without actually creating records or uploading.",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="Skip submissions that already exist instead of raising an error.",
        )

    def handle(self, *args, **options):
        exam_id = options["exam_id"]
        csv_path = Path(options["csv"])
        files_dir = Path(options["files_dir"])
        dry_run = options["dry_run"]
        skip_existing = options["skip_existing"]

        # ── Validate inputs ──────────────────────────────────────────
        if not csv_path.is_file():
            raise CommandError(f"CSV file not found: {csv_path}")
        if not files_dir.is_dir():
            raise CommandError(f"Files directory not found: {files_dir}")

        try:
            exam = ExamModel.objects.get(pk=exam_id)
        except ExamModel.DoesNotExist:
            raise CommandError(f"Exam with ID {exam_id} does not exist.")

        # Questions for this exam, sorted by ID ascending (column order)
        questions = list(
            QuestionModel.objects.filter(exam=exam).order_by("id")
        )
        if not questions:
            raise CommandError(f"Exam '{exam}' has no questions.")

        self.stdout.write(
            f"Exam: {exam} | Questions: {len(questions)} | "
            f"Dry run: {dry_run}"
        )

        # ── Parse CSV ────────────────────────────────────────────────
        rows = self._parse_csv(csv_path)
        self.stdout.write(f"CSV rows to process: {len(rows)}")

        # ── Pre-fetch users ──────────────────────────────────────────
        usernames = {row[0] for row in rows}
        users_qs = User.objects.filter(username__in=usernames)
        users_by_name = {u.username: u for u in users_qs}

        missing_users = usernames - set(users_by_name.keys())
        if missing_users:
            raise CommandError(
                f"Users not found in the database: {', '.join(sorted(missing_users))}"
            )

        # ── Process rows ─────────────────────────────────────────────
        created = 0
        skipped = 0
        errors = []

        for row_num, row in enumerate(rows, start=1):
            username = row[0]
            file_paths = row[1:]

            if len(file_paths) != len(questions):
                errors.append(
                    f"Row {row_num} ({username}): expected {len(questions)} "
                    f"file columns, got {len(file_paths)}"
                )
                continue

            user = users_by_name[username]

            for col_idx, (question, rel_path) in enumerate(
                zip(questions, file_paths), start=1
            ):
                rel_path = rel_path.strip()

                # Allow empty cells → skip that question
                if not rel_path:
                    continue

                file_on_disk = files_dir / username / rel_path
                if not file_on_disk.is_file():
                    errors.append(
                        f"Row {row_num}, col {col_idx} ({username}): "
                        f"file not found: {file_on_disk}"
                    )
                    continue

                # Check for existing submission
                if Submission.objects.filter(
                    user=user, question=question
                ).exists():
                    if skip_existing:
                        skipped += 1
                        continue
                    else:
                        errors.append(
                            f"Row {row_num}, col {col_idx} ({username}): "
                            f"submission already exists for question "
                            f"'{question.sign_name}'"
                        )
                        continue

                if dry_run:
                    created += 1
                    continue

                # Read file and save via Django's storage backend
                file_content = file_on_disk.read_bytes()
                filename = file_on_disk.name

                submission = Submission(user=user, question=question)
                submission.file.save(
                    filename,
                    ContentFile(file_content),
                    save=False,
                )
                submission.save()
                created += 1

        # ── Report ───────────────────────────────────────────────────
        if errors:
            self.stderr.write(self.style.WARNING(f"\n{len(errors)} error(s):"))
            for e in errors:
                self.stderr.write(f"   • {e}")

        verb = "Would create" if dry_run else "Created"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{verb} {created} submission(s), skipped {skipped}."
            )
        )

    # ── helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _parse_csv(csv_path: Path) -> list[list[str]]:
        """Read CSV, skip blank lines and an optional header row."""
        rows = []
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for line_no, row in enumerate(reader, start=1):
                # Skip blank lines
                if not row or all(cell.strip() == "" for cell in row):
                    continue
                # Skip a header row (first cell doesn't look like a username)
                if line_no == 1 and row[0].strip().lower() in (
                    "username",
                    "user",
                    "name",
                    "نام کاربری",
                ):
                    continue
                rows.append([cell.strip() for cell in row])
        return rows
