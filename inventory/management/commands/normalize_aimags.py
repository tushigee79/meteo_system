from __future__ import annotations

import re
from typing import Dict, Iterable, List, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Model
from django.apps import apps


# ============================================================
# 1) Каноник стандарт нэрс (21 аймаг + УБ)
# ============================================================
CANONICAL: List[str] = [
    "Архангай",
    "Баян-Өлгий",
    "Баянхонгор",
    "Булган",
    "Говь-Алтай",
    "Говьсүмбэр",
    "Дархан-Уул",
    "Дорноговь",
    "Дорнод",
    "Дундговь",
    "Завхан",
    "Орхон",
    "Өвөрхангай",
    "Өмнөговь",
    "Сүхбаатар",
    "Сэлэнгэ",
    "Төв",
    "Увс",
    "Ховд",
    "Хөвсгөл",
    "Хэнтий",
    "Улаанбаатар",
]

# Зарим түгээмэл хэлбэрүүдийг урьдчилан зураглах (optional нэмэлт)
ALIASES: Dict[str, str] = {
    # “УБ” гэх мэт бичиглэлүүд тааруулах
    "уб": "Улаанбаатар",
    "улаанбаатар хот": "Улаанбаатар",
    "улаанбаатар": "Улаанбаатар",
    # Заримдаа “Говьсүмбэр” дээр “Говь-Сүмбэр” гэж бичсэн байдаг
    "говь-сүмбэр": "Говьсүмбэр",
    "говь—сүмбэр": "Говьсүмбэр",
    "говь–сүмбэр": "Говьсүмбэр",
    # “Дархан Уул” гэх мэт
    "дархан уул": "Дархан-Уул",
}

# Хайлт/тааруулалтын үед “-” төрлүүдийг нэг болгох
DASHES = r"[\u2010\u2011\u2012\u2013\u2014\u2212-]"  # ‐ - ‒ – — − -


def normalize_text(s: str) -> str:
    """Нэрийг тааруулахад ашиглах нормал хэлбэр (lower + dash unify + spaces)."""
    s = (s or "").strip()
    if not s:
        return ""
    # бүх төрлийн дашийг '-' болгох
    s = re.sub(DASHES, "-", s)
    # олон зайг нэг болгох
    s = re.sub(r"\s+", " ", s)
    return s.lower().strip()


def to_title_mn(s: str) -> str:
    """
    Монгол үсэгтэй Title-case хийх "хөнгөн" хувилбар.
    Python-ийн .title() нь 'Өвөрхангай' зэрэгт ихэнхдээ OK.
    """
    s = (s or "").strip()
    s = re.sub(DASHES, "-", s)
    s = re.sub(r"\s+", " ", s)
    return s.title()


def build_canonical_lookup() -> Dict[str, str]:
    """normalize_text(canonical) -> canonical"""
    d: Dict[str, str] = {}
    for c in CANONICAL:
        d[normalize_text(c)] = c
    # aliases-г бас normalize хийгээд нэмнэ
    for k, v in ALIASES.items():
        d[normalize_text(k)] = v
    return d


def guess_canonical(name: str, canon_map: Dict[str, str]) -> str:
    """
    Оруулсан нэрийг canonical руу тааруулж өгнө.
    1) alias/canonical exact normalized match
    2) нэрийг title болгоод canonical-аас хайх
    3) олдохгүй бол title хувилбарыг буцаана
    """
    n = normalize_text(name)
    if not n:
        return ""
    if n in canon_map:
        return canon_map[n]

    # title-case болгосон хэлбэр canonical-д байвал түүнийг авна
    t = to_title_mn(name)
    tn = normalize_text(t)
    if tn in canon_map:
        return canon_map[tn]

    # тусгай жижиг “-” байрлалын алдаа (жиш: “Баян Өлгий” -> “Баян-Өлгий”)
    # canonical жагсаалт дотор ойролцоо хэлбэрүүд байвал dash-г авч үзнэ
    ndashless = n.replace("-", " ")
    for key, val in canon_map.items():
        if key.replace("-", " ") == ndashless:
            return val

    # олдохгүй бол title-г өөрийг нь canonical гэж үзээд үлдээнэ
    return t


def get_fk_fields_pointing_to(model: Model) -> List[Tuple[Model, str]]:
    """
    Aimag model-руу FK холбогдсон бүх model.field-үүдийг динамикаар олно.
    Жиш: Location.aimag_ref, Organization.aimag, UserProfile.aimag гэх мэт.
    """
    target = model.__class__
    aimag_model = apps.get_model("inventory", "Aimag")
    target = aimag_model  # explicit

    refs: List[Tuple[Model, str]] = []
    for m in apps.get_models():
        for f in m._meta.get_fields():
            # ManyToOneRel бол reverse relation учир field биш; FK тал нь ManyToOneRel биш байна
            if getattr(f, "is_relation", False) and getattr(f, "many_to_one", False) and getattr(f, "remote_field", None):
                if f.remote_field.model == aimag_model:
                    refs.append((m, f.name))
    return refs


class Command(BaseCommand):
    help = "Normalize and merge duplicate Aimag rows into canonical 21 aimags + UB."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Print actions but do not write to DB.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        Aimag = apps.get_model("inventory", "Aimag")

        canon_map = build_canonical_lookup()

        # FK references list (dynamic)
        fk_refs = get_fk_fields_pointing_to(Aimag)

        self.stdout.write(self.style.MIGRATE_HEADING("=== Aimag normalization/merge ==="))
        self.stdout.write(f"Dry-run: {dry_run}")
        self.stdout.write(f"FK refs found: {len(fk_refs)}")

        aimags = list(Aimag.objects.all().order_by("id"))
        if not aimags:
            self.stdout.write(self.style.WARNING("No Aimag rows found. Nothing to do."))
            return

        # 1) name -> canonical_name mapping
        id_to_newname: Dict[int, str] = {}
        for a in aimags:
            new_name = guess_canonical(getattr(a, "name", ""), canon_map)
            id_to_newname[a.id] = new_name

        # 2) Group by canonical name (normalized)
        groups: Dict[str, List[int]] = {}
        for a in aimags:
            cname = id_to_newname[a.id] or getattr(a, "name", "") or ""
            key = normalize_text(cname)
            groups.setdefault(key, []).append(a.id)

        # 3) Ensure canonical rows exist for all CANONICAL names (create if missing)
        existing_by_key: Dict[str, int] = {}
        for a in aimags:
            existing_by_key[normalize_text(a.name)] = a.id

        created_ids: List[int] = []
        for c in CANONICAL:
            ck = normalize_text(c)
            if ck not in existing_by_key:
                self.stdout.write(self.style.WARNING(f"Missing canonical '{c}' -> will CREATE"))
                if not dry_run:
                    obj = Aimag.objects.create(name=c)
                    created_ids.append(obj.id)
                    existing_by_key[ck] = obj.id

        if created_ids:
            self.stdout.write(self.style.SUCCESS(f"Created canonical rows: {created_ids}"))

        # refresh aimags after creates
        if not dry_run and created_ids:
            aimags = list(Aimag.objects.all().order_by("id"))

        # rebuild groups after potential creates
        # (created canonical rows already clean)
        id_to_obj = {a.id: a for a in aimags}
        groups = {}
        for a in aimags:
            new_name = guess_canonical(a.name, canon_map)
            key = normalize_text(new_name or a.name)
            groups.setdefault(key, []).append(a.id)

        # 4) Merge each group: keep a canonical "winner", move FKs, delete losers
        total_merged = 0
        total_renamed = 0

        for gkey, ids in sorted(groups.items(), key=lambda x: x[0]):
            if not gkey:
                continue

            # Determine canonical name for this key
            canonical_name = canon_map.get(gkey)
            if not canonical_name:
                # if key corresponds to some title normalized, still set canonical_name as title of first
                canonical_name = guess_canonical(id_to_obj[ids[0]].name, canon_map)

            # Pick winner:
            # Prefer exact canonical name match; else smallest id.
            winner_id = None
            for i in ids:
                if normalize_text(id_to_obj[i].name) == normalize_text(canonical_name):
                    winner_id = i
                    break
            if winner_id is None:
                winner_id = min(ids)

            loser_ids = [i for i in ids if i != winner_id]

            # rename winner if needed to canonical_name
            winner = id_to_obj[winner_id]
            if canonical_name and winner.name != canonical_name:
                self.stdout.write(f"RENAME winner id={winner_id}: '{winner.name}' -> '{canonical_name}'")
                total_renamed += 1
                if not dry_run:
                    winner.name = canonical_name
                    winner.save(update_fields=["name"])

            if not loser_ids:
                continue

            self.stdout.write(self.style.NOTICE(f"MERGE group '{canonical_name}' keep={winner_id} losers={loser_ids}"))

            # Move all FK references from losers -> winner
            for model_cls, field_name in fk_refs:
                qs = model_cls.objects.filter(**{f"{field_name}__in": loser_ids})
                cnt = qs.count()
                if cnt:
                    self.stdout.write(f"  - UPDATE {model_cls._meta.label}.{field_name}: {cnt} rows")
                    if not dry_run:
                        qs.update(**{field_name: winner_id})

            # Finally delete losers
            total_merged += len(loser_ids)
            if not dry_run:
                Aimag.objects.filter(id__in=loser_ids).delete()

        self.stdout.write(self.style.SUCCESS("=== Done ==="))
        self.stdout.write(f"Renamed winners: {total_renamed}")
        self.stdout.write(f"Deleted merged duplicates: {total_merged}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run mode: no DB changes were made."))
