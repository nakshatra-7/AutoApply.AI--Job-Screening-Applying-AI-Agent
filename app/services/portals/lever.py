from __future__ import annotations

from typing import List, Optional

from bs4 import BeautifulSoup

from app.schemas.discovery import DiscoveredField, FillAction


class LeverAdapter:
    name = "lever"

    def matches(self, url: str, html: str) -> bool:
        url_lower = url.lower()
        if "lever.co" in url_lower:
            return True
        if "lever" in html.lower() and "application" in html.lower():
            return True
        return False

    def discover_fields(self, url: str, html: str) -> List[DiscoveredField]:
        soup = BeautifulSoup(html, "html.parser")
        fields: List[DiscoveredField] = []

        def extract_label(element) -> str:
            if element is None:
                return ""
            label = element.get_text(strip=True)
            if label:
                return label
            return element.get("aria-label", "") or element.get("placeholder", "") or ""

        form = soup.find("form")
        if not form:
            form = soup

        for input_el in form.find_all(["input", "textarea", "select"]):
            tag_name = input_el.name
            field_type = input_el.get("type", "text").lower()
            if tag_name == "textarea":
                field_type = "textarea"
            if tag_name == "select":
                field_type = "select"

            field_id = (
                input_el.get("id")
                or input_el.get("name")
                or input_el.get("data-qa")
                or input_el.get("data-qa-id")
            )
            if not field_id:
                continue

            label_el = None
            if input_el.get("id"):
                label_el = form.find("label", attrs={"for": input_el.get("id")})
            label = extract_label(label_el) or input_el.get("aria-label", "") or input_el.get("name", "")

            options: List[str] = []
            if tag_name == "select":
                for opt in input_el.find_all("option"):
                    opt_text = opt.get_text(strip=True)
                    if opt_text:
                        options.append(opt_text)

            required = bool(input_el.get("required")) or "required" in (input_el.get("class") or [])
            placeholder = input_el.get("placeholder")
            raw_name = input_el.get("name")

            fields.append(
                DiscoveredField(
                    field_id=str(field_id),
                    label=label or str(field_id),
                    type=field_type,
                    required=required,
                    options=options,
                    section=None,
                    placeholder=placeholder,
                    raw_name=raw_name,
                    source_portal=self.name,
                )
            )

        return fields

    def build_fill_actions(self, fields: List[DiscoveredField], answers: dict[str, str]) -> List[FillAction]:
        actions: List[FillAction] = []

        def normalize(text: Optional[str]) -> str:
            return (text or "").strip().lower()

        def match_key(field: DiscoveredField) -> Optional[str]:
            haystack = " ".join(
                [
                    normalize(field.label),
                    normalize(field.raw_name),
                    normalize(field.placeholder),
                    normalize(field.type),
                ]
            )
            if "cover letter" in haystack:
                return "cover_letter"
            if "skill" in haystack:
                return "key_skills"
            if "experience" in haystack or "years" in haystack:
                return "years_experience"
            if "work authorization" in haystack or "authorized" in haystack:
                return "work_authorization"
            if "visa" in haystack or "sponsorship" in haystack:
                return "visa_sponsorship"
            if "relocation" in haystack or "relocate" in haystack:
                return "relocation"
            if "notice" in haystack:
                return "notice_period"
            if "salary" in haystack or "compensation" in haystack:
                return "expected_salary"
            if "location" in haystack or "city" in haystack:
                return "location"
            if "linkedin" in haystack:
                return "linkedin"
            if "github" in haystack:
                return "github"
            return None

        application_package = answers.get("application_package")
        if application_package is not None:
            actions.append(
                FillAction(
                    action_type="package",
                    field_id="application_package",
                    value=str(application_package),
                    confidence=0.9,
                    notes="Prepared application package for submission pipeline.",
                )
            )

        for field in fields:
            key = match_key(field)
            if not key:
                continue
            if key not in answers:
                continue

            value = str(answers[key])
            action_type = "type"
            notes = f"Matched via {key} keyword."
            confidence = 0.7

            if field.type == "select":
                action_type = "select"
                if field.options:
                    value = self._pick_option(value, field.options)
                confidence = 0.6
            elif field.type == "checkbox":
                action_type = "check"
                value = "true" if normalize(value) in {"yes", "true", "1"} else "false"
                confidence = 0.6
            elif field.type == "file":
                action_type = "upload"
                confidence = 0.5

            actions.append(
                FillAction(
                    action_type=action_type,
                    field_id=field.field_id,
                    value=value,
                    confidence=confidence,
                    notes=notes,
                )
            )

        return actions

    def _pick_option(self, value: str, options: List[str]) -> str:
        def norm(text: str) -> str:
            return text.strip().lower()

        val = norm(value)
        for option in options:
            if norm(option) == val:
                return option
        yes_set = {"yes", "y", "true", "1"}
        no_set = {"no", "n", "false", "0"}
        if val in yes_set or val in no_set:
            target = yes_set if val in yes_set else no_set
            for option in options:
                if norm(option) in target:
                    return option
        return value
