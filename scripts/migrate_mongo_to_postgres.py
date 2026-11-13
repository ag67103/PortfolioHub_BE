"""
One-off copy of the old MongoDB data into PostgreSQL.

    pip install pymongo
    export DATABASE_URL=postgresql://user:pass@host/dbname      # target (schema must exist: alembic upgrade head)
    python scripts/migrate_mongo_to_postgres.py --mongo-url mongodb://localhost:27017 --mongo-db portfolio [--dry-run]

- ObjectIds become UUIDs derived from the ObjectId (uuid5), so the script can be re-run safely: rows that already
  exist are skipped, never duplicated.
- Access tokens are NOT copied (everybody signs in again). Collections `about` and `token_blacklist` were unused.
- Rows that point at a missing user are skipped and reported, as are users whose username/email already exist.
"""
import argparse
import asyncio
import os
import sys
import uuid
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pymongo import MongoClient  # noqa: E402
from sqlalchemy.dialects.postgresql import insert  # noqa: E402

from app.db.database import SessionLocal  # noqa: E402
from app.models import Award, Certification, Education, Experience, Message, Project, Skill, User  # noqa: E402

NAMESPACE = uuid.UUID("6f1c2d34-8a5b-4c7e-9d10-0a1b2c3d4e5f")


def to_uuid(oid) -> uuid.UUID | None:
    return None if oid is None else uuid.uuid5(NAMESPACE, str(oid))


def to_date(v):
    if v is None:
        return None
    return v.date() if isinstance(v, datetime) else v


def to_dt(v):
    if v is None:
        return None
    if isinstance(v, datetime) and v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    return v


def enum_str(v):
    return getattr(v, "value", v)


USER_FIELDS = ["username", "email", "hashed_password", "first_name", "middle_name", "last_name", "title", "gender", "phone",
               "address", "profile_image_url", "portfolio_title", "portfolio_description", "portfolio_education",
               "portfolio_certifications", "portfolio_awards", "github_url", "twitter_url", "instagram_url",
               "linkedin_url", "leetcode_url", "website_url"]


def user_row(d):
    row = {k: d.get(k) for k in USER_FIELDS}
    row.update(id=to_uuid(d["_id"]), is_active=enum_str(d.get("is_active", "active")), role=enum_str(d.get("role", "viewer")),
               visitor_count=d.get("visitor_count") or 0, created_at=to_dt(d.get("created_at")) or datetime.now(timezone.utc),
               updated_at=to_dt(d.get("updated_at")) or datetime.now(timezone.utc))
    return row


def item_rows(model, docs, fields, date_fields=()):
    rows = []
    for d in docs:
        row = {f: d.get(f) for f in fields}
        for f in date_fields:
            row[f] = to_date(d.get(f))
        row.update(id=to_uuid(d["_id"]), user_id=to_uuid(d.get("user_id")),
                   created_at=to_dt(d.get("created_at")) or datetime.now(timezone.utc),
                   updated_at=to_dt(d.get("updated_at")) or datetime.now(timezone.utc))
        if "technologies" in fields:
            row["technologies"] = row["technologies"] or []
        rows.append(row)
    return rows


def message_rows(docs):
    rows = []
    for d in docs:
        rows.append(dict(
            id=to_uuid(d["_id"]), conversationId=to_uuid(d.get("conversationId")) or uuid.uuid4(),
            senderName=d.get("senderName"), senderEmail=d.get("senderEmail"), senderUserId=to_uuid(d.get("senderUserId")),
            recipientUserId=to_uuid(d.get("recipientUserId")), recipientEmail=d.get("recipientEmail"),
            recipientName=d.get("recipientName"), messageSubject=d.get("messageSubject"), messageContent=d.get("messageContent") or "",
            created_at=to_dt(d.get("created_at")) or datetime.now(timezone.utc),
            updated_at=to_dt(d.get("updated_at")) or datetime.now(timezone.utc),
            isDeletedForSender=bool(d.get("isDeletedForSender")), isDeletedForRecipient=bool(d.get("isDeletedForRecipient")),
            isRead=bool(d.get("isRead"))))
    return rows


async def insert_rows(db, model, rows, label, dry_run):
    inserted = 0
    for row in rows:
        if dry_run:
            inserted += 1
            continue
        # ORM attribute names -> column keys via the mapper (Message uses camelCase attributes)
        values = {model.__mapper__.get_property(k).columns[0].name: v for k, v in row.items()}
        res = await db.execute(insert(model.__table__).values(**values).on_conflict_do_nothing())
        inserted += res.rowcount or 0
    print(f"{label:15} read {len(rows):5}  inserted {inserted:5}  skipped {len(rows) - inserted}")


async def main(args):
    mongo = MongoClient(args.mongo_url)[args.mongo_db]

    users = list(mongo["users"].find())
    user_ids = {to_uuid(u["_id"]) for u in users}

    seen_names, seen_emails, user_rows = set(), set(), []
    for u in users:
        key_n, key_e = (u.get("username") or "").lower(), (u.get("email") or "").lower()
        if key_n in seen_names or key_e in seen_emails:
            print(f"! skipping duplicate user {u.get('username')} <{u.get('email')}> ({u['_id']})")
            user_ids.discard(to_uuid(u["_id"]))
            continue
        seen_names.add(key_n); seen_emails.add(key_e)
        user_rows.append(user_row(u))

    async with SessionLocal() as db:
        await insert_rows(db, User, user_rows, "users", args.dry_run)

        specs = [
            (Project, "projects", ["title", "description", "technologies", "live_url", "code_url", "image_url"], ["start_date", "end_date"]),
            (Experience, "experiences", ["title", "company", "description", "technologies"], ["start_date", "end_date"]),
            (Education, "educations", ["institution", "degree", "description"], ["start_date", "end_date"]),
            (Certification, "certifications", ["name", "issuer", "description", "credential_id", "credential_url"], ["issue_date"]),
            (Award, "awards", ["name", "issuer", "description", "category"], ["issue_date"]),
            (Skill, "skills", ["name", "category", "proficiency"], []),
        ]
        for model, coll, fields, dates in specs:
            docs = list(mongo[coll].find())
            rows = item_rows(model, docs, fields, dates)
            kept = [r for r in rows if r["user_id"] in user_ids]
            if len(kept) != len(rows):
                print(f"! {coll}: skipped {len(rows) - len(kept)} rows whose user does not exist")
            await insert_rows(db, model, kept, coll, args.dry_run)

        msgs = message_rows(list(mongo["message"].find()))
        kept = [m for m in msgs if m["recipientUserId"] in user_ids]
        for m in kept:
            if m["senderUserId"] not in user_ids:
                m["senderUserId"] = None
        if len(kept) != len(msgs):
            print(f"! message: skipped {len(msgs) - len(kept)} rows whose recipient does not exist")
        await insert_rows(db, Message, kept, "messages", args.dry_run)

        if args.dry_run:
            await db.rollback()
            print("Dry run: nothing written.")
        else:
            await db.commit()
            print("Done.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mongo-url", default="mongodb://localhost:27017")
    ap.add_argument("--mongo-db", default="portfolio")
    ap.add_argument("--dry-run", action="store_true")
    asyncio.run(main(ap.parse_args()))
