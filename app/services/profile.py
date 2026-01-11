import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.db_models import Resume, User, UserFact
from app.models.store import Profile, ResumeRecord, store


class ProfileService:
    def get_profile(self, user_id: str, db: Optional[Session] = None) -> Profile:
        if db is None:
            if user_id not in store.users:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            # Seed an empty profile if one does not exist yet.
            if user_id not in store.profiles:
                store.profiles[user_id] = Profile(user_id=user_id)
            return store.profiles[user_id]

        user_uuid = self._as_uuid(user_id)
        if user_uuid is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id")
        user = self._ensure_db_user(db, user_uuid)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        facts = (
            db.query(UserFact)
            .filter(UserFact.user_id == user_uuid)
            .all()
        )
        fact_map = {fact.key: fact.value for fact in facts}
        skills_value = fact_map.get("skills")
        skills = skills_value if isinstance(skills_value, list) else []
        profile = Profile(
            user_id=user_id,
            first_name=fact_map.get("first_name"),
            last_name=fact_map.get("last_name"),
            address_line1=fact_map.get("address_line1"),
            city=fact_map.get("city"),
            postal_code=fact_map.get("postal_code"),
            phone=fact_map.get("phone"),
            country=fact_map.get("country"),
            headline=fact_map.get("headline"),
            summary=fact_map.get("summary"),
            skills=skills,
            location=fact_map.get("location"),
        )
        return profile

    def update_profile(
        self,
        user_id: str,
        db: Optional[Session],
        first_name: Optional[str],
        last_name: Optional[str],
        address_line1: Optional[str],
        city: Optional[str],
        postal_code: Optional[str],
        phone: Optional[str],
        country: Optional[str],
        headline: Optional[str],
        summary: Optional[str],
        skills: Optional[list[str]],
        location: Optional[str],
    ) -> Profile:
        if db is not None:
            user_uuid = self._as_uuid(user_id)
            if user_uuid is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id")
            user = self._ensure_db_user(db, user_uuid)
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            if first_name is not None:
                self._upsert_fact(db, user_uuid, "first_name", first_name)
            if last_name is not None:
                self._upsert_fact(db, user_uuid, "last_name", last_name)
            if address_line1 is not None:
                self._upsert_fact(db, user_uuid, "address_line1", address_line1)
            if city is not None:
                self._upsert_fact(db, user_uuid, "city", city)
            if postal_code is not None:
                self._upsert_fact(db, user_uuid, "postal_code", postal_code)
            if phone is not None:
                self._upsert_fact(db, user_uuid, "phone", phone)
            if country is not None:
                self._upsert_fact(db, user_uuid, "country", country)
            if headline is not None:
                self._upsert_fact(db, user_uuid, "headline", headline)
            if summary is not None:
                self._upsert_fact(db, user_uuid, "summary", summary)
            if skills is not None:
                self._upsert_fact(db, user_uuid, "skills", skills)
            if location is not None:
                self._upsert_fact(db, user_uuid, "location", location)
            db.commit()
            return self.get_profile(user_id, db=db)

        profile = self.get_profile(user_id)
        if first_name is not None:
            profile.first_name = first_name
        if last_name is not None:
            profile.last_name = last_name
        if address_line1 is not None:
            profile.address_line1 = address_line1
        if city is not None:
            profile.city = city
        if postal_code is not None:
            profile.postal_code = postal_code
        if phone is not None:
            profile.phone = phone
        if country is not None:
            profile.country = country
        if headline is not None:
            profile.headline = headline
        if summary is not None:
            profile.summary = summary
        if skills is not None:
            profile.skills = skills
        if location is not None:
            profile.location = location
        store.add_profile(profile)
        return profile

    def upload_resume(self, user_id: str, file: UploadFile, db: Optional[Session] = None) -> ResumeRecord:
        contents = file.file.read()
        parsed = self._parse_resume(contents)
        if db is not None:
            user_uuid = self._as_uuid(user_id)
            if user_uuid is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id")
            user = self._ensure_db_user(db, user_uuid)
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            resume = Resume(
                id=uuid.uuid4(),
                user_id=user_uuid,
                resume_type=None,
                filename=file.filename or "resume",
                parsed_json=parsed,
            )
            db.add(resume)
            self._seed_profile_facts(db, user_uuid, parsed)
            db.commit()
            resume_record = ResumeRecord(
                id=str(resume.id),
                user_id=user_id,
                filename=resume.filename,
                content_type=file.content_type or "application/octet-stream",
                size_bytes=len(contents),
                parsed_json=parsed,
            )
            return resume_record

        if user_id not in store.users:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        resume_record = ResumeRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            size_bytes=len(contents),
            parsed_json=parsed,
        )
        store.add_resume(resume_record)
        self._seed_profile_from_resume(user_id, parsed)
        return resume_record

    def _parse_resume(self, contents: bytes) -> dict[str, str]:
        try:
            text = contents.decode("utf-8", errors="ignore")
        except Exception:
            return {}
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        email = next((line for line in lines if "@" in line and "." in line), "")
        phone = ""
        for line in lines:
            if "linearized" in line.lower() or line.strip().startswith("<<"):
                continue
            digits = "".join(ch for ch in line if ch.isdigit())
            if 7 <= len(digits) <= 15:
                phone = digits
                break
        name = ""
        for line in lines[:5]:
            if any(ch.isdigit() for ch in line):
                continue
            if len(line.split()) in {2, 3, 4}:
                name = line
                break
        return {
            "email": email,
            "phone": phone,
            "full_name": name,
        }

    def _seed_profile_from_resume(self, user_id: str, parsed: dict[str, str]) -> None:
        if not parsed:
            return
        profile = self.get_profile(user_id)
        if parsed.get("full_name") and not (profile.first_name or profile.last_name):
            parts = parsed["full_name"].split()
            profile.first_name = parts[0]
            profile.last_name = " ".join(parts[1:]) if len(parts) > 1 else profile.last_name
        if parsed.get("phone") and not profile.phone:
            profile.phone = parsed["phone"]
        if parsed.get("email") and not profile.summary:
            profile.summary = parsed["email"]
        store.add_profile(profile)

    def _seed_profile_facts(self, db: Session, user_id: uuid.UUID, parsed: dict[str, str]) -> None:
        if not parsed:
            return
        full_name = parsed.get("full_name")
        if full_name:
            parts = full_name.split()
            if parts:
                self._upsert_fact(db, user_id, "first_name", parts[0])
            if len(parts) > 1:
                self._upsert_fact(db, user_id, "last_name", " ".join(parts[1:]))
        phone = parsed.get("phone")
        if phone:
            self._upsert_fact(db, user_id, "phone", phone)
        email = parsed.get("email")
        if email:
            self._upsert_fact(db, user_id, "email", email)

    def _upsert_fact(self, db: Session, user_id: uuid.UUID, key: str, value: object) -> None:
        existing = (
            db.query(UserFact)
            .filter(UserFact.user_id == user_id, UserFact.key == key)
            .one_or_none()
        )
        if existing:
            existing.value = value
            existing.last_confirmed_at = datetime.utcnow()
            existing.updated_at = datetime.utcnow()
            return
        db.add(
            UserFact(
                id=uuid.uuid4(),
                user_id=user_id,
                key=key,
                value=value,
                last_confirmed_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

    def _as_uuid(self, user_id: str) -> Optional[uuid.UUID]:
        try:
            return uuid.UUID(user_id)
        except (TypeError, ValueError):
            return None

    def _ensure_db_user(self, db: Session, user_id: uuid.UUID) -> Optional[User]:
        user = db.get(User, user_id)
        if user:
            return user
        store_user = store.users.get(str(user_id))
        if not store_user:
            return None
        name = store_user.full_name or store_user.email.split("@")[0]
        user = User(
            id=user_id,
            name=name,
            email=store_user.email,
            hashed_password=store_user.password_hash,
            created_at=store_user.created_at,
        )
        db.add(user)
        db.commit()
        return user


profile_service = ProfileService()
