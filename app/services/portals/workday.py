from __future__ import annotations
from typing import List, Optional, Set
from bs4 import BeautifulSoup
from app.schemas.discovery import DiscoveredField, FillAction


class WorkdayAdapter:
    name = "workday"

    def matches(self, url: str, html: str) -> bool:
        url_lower = url.lower()
        if "myworkdayjobs.com" in url_lower or "workday" in url_lower:
            return True
        html_lower = html.lower() if isinstance(html, str) else ""
        if "workday" in html_lower and "data-automation-id" in html_lower:
            return True
        return False
    
    def _resolve_html(self, html) -> str:
        if isinstance(html, str):
            return html
        # for cases where html might be a response object
        if hasattr(html, "content"):
            try:
                content = html.content() if callable(html.content) else html.content
                if isinstance(content, (bytes, bytearray)):
                    return content.decode("utf-8", errors="ignore")
                if isinstance(content, str):
                    return content
            except Exception:
                return ""
        return ""

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
                    normalize(field.field_id),
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

        for field in fields:
            key = match_key(field)
            if not key or key not in answers:
                continue

            value = str(answers[key])
            action_type = "type"
            confidence = 0.55
            notes = f"Matched via {key} keyword."

            if field.type == "select":
                action_type = "select"
                if field.options:
                    value = self._pick_option(value, field.options)
                confidence = min(confidence, 0.5)

            elif field.type == "checkbox":
                action_type = "check"
                value = "true" if normalize(value) in {"yes", "true", "1"} else "false"
                confidence = min(confidence, 0.5)

            elif field.type == "radio":
                action_type = "select"
                if field.options:
                    value = self._pick_option(value, field.options)
                confidence = min(confidence, 0.5)

            elif field.type == "file":
                action_type = "upload"
                confidence = min(confidence, 0.4)

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

    def _resolve_html(self, html: str) -> str:
        if isinstance(html, str):
            return html
        if hasattr(html, "content") and callable(getattr(html, "content")):
            try:
                content = html.content()
                if isinstance(content, str):
                    return content
            except Exception:
                return ""
        return ""

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

    def _resolve_html(self, html: str) -> str:
        # html might be None or already a string
        if not html:
            return ""
        if isinstance(html, bytes):
            try:
                return html.decode("utf-8", errors="ignore")
            except Exception:
                return ""
        return str(html)

    def build_fill_actions(self, discovered_fields, proposed_answers):
    # For now just return empty; later we’ll implement actual playwright fills
        return []


    def discover_fields(self, url: str, html: str) -> List[DiscoveredField]:
        html_text = self._resolve_html(html)
        if not html_text:
            return []

        soup = BeautifulSoup(html_text, "html.parser")
        root = soup.find("form") or soup

        fields: List[DiscoveredField] = []
        seen_ids: Set[str] = set()

        def norm(s: Optional[str]) -> str:
            return (s or "").strip()

        def text_of(el) -> str:
            if not el:
                return ""
            return el.get_text(" ", strip=True)
        
        def label_from_describedby(el) -> str:
            ids = (el.get("aria-describedby") or "").split()
            parts = []
            for _id in ids:
                ref = soup.find(id=_id)
                if ref:
                    t = ref.get_text(" ", strip=True)
                    if t:
                        parts.append(t)
                if uxi_type == "selectinput":
                    print("WD selectinput:", field_id, label)

            # Sometimes this is hint text; still better than empty.
            return " ".join(parts).strip()


        def resolve_aria_labelledby(el) -> str:
            ids = (el.get("aria-labelledby") or "").split()
            parts = []
            for _id in ids:
                ref = soup.find(id=_id)
                t = text_of(ref)
                if t:
                    parts.append(t)
            return " ".join(parts).strip()

        def find_label_for_input(input_el) -> str:
            # 1) <label for="id">
            _id = input_el.get("id")
            if _id:
                lab = root.find("label", attrs={"for": _id})
                t = text_of(lab)
                if t:
                    return t

            # 2) aria-labelledby
            t = resolve_aria_labelledby(input_el)
            if t:
                return t

            # 3) aria-describedby (Workday often stores label/hint here)
            t = label_from_describedby(input_el)
            if t:
                return t

            # 4) aria-label / placeholder / name
            for attr in ["aria-label", "placeholder", "name", "id"]:
                t = norm(input_el.get(attr))
                if t:
                    return t


            # 4) climb up: nearest container with a readable "label-like" text
            parent = input_el.parent
            hop = 0
            while parent is not None and hop < 6:
                # Workday containers often have data-automation-id; sometimes label is a sibling span/div
                # Try finding preceding text nodelabel = s in the container
                # Heuristic: look for elements that look like labels
                cand = parent.find(["label", "span", "div"], attrs={"data-automation-id": ["label", "fieldLabel"]})
                if cand:
                    t = text_of(cand)
                    if t:
                        return t

                # fallback: first strong-ish text inside parent (but avoid huge blobs)
                t = text_of(parent)
                if 0 < len(t) <= 80:
                    return t

                parent = parent.parent
                hop += 1

            return ""

        def is_required(input_el, label: str) -> bool:
            return (
                input_el.get("required") is not None
                or input_el.get("aria-required") == "true"
                or "required" in (input_el.get("class") or [])
                or (label.endswith("*"))
            )

        # PASS A: classic inputs/textarea/select (what you already do, but with better label)
        for input_el in root.find_all(["input", "textarea", "select"]):
            tag = input_el.name
            field_type = (input_el.get("type") or "text").lower()
            if tag == "textarea":
                field_type = "textarea"
            if tag == "select":
                field_type = "select"

            field_id = (
                input_el.get("id")
                or input_el.get("name")
                or input_el.get("data-automation-id")
                or input_el.get("data-qa")
                or input_el.get("data-uxi-multiselect-id")
            )
            uxi_type = (input_el.get("data-uxi-widget-type") or "").lower()
            if uxi_type == "selectinput":
                field_type = "select"

            if not field_id:
                continue

            field_id = str(field_id)
            if field_id in seen_ids:
                continue

            label = find_label_for_input(input_el) or field_id
            required = is_required(input_el, label)
            placeholder = input_el.get("placeholder")
            raw_name = input_el.get("name")

            options: List[str] = []
            if tag == "select":
                for opt in input_el.find_all("option"):
                    ot = opt.get_text(strip=True)
                    if ot:
                        options.append(ot)

            fields.append(
                DiscoveredField(
                    field_id=field_id,
                    label=label,
                    type=field_type,
                    required=required,
                    options=options,
                    section=None,
                    placeholder=placeholder,
                    raw_name=raw_name,
                    source_portal=self.name,
                )
            )
            seen_ids.add(field_id)

        # PASS B: Workday "custom dropdown" containers (no <select>)
        # Heuristic: find containers that represent a field with automation id
        # This is intentionally broad and safe; you can tighten once you see DOM samples.
        dropdown_like = root.find_all(attrs={"data-automation-id": True})
        for node in dropdown_like:
            daid = (node.get("data-automation-id") or "").lower()
            if daid not in {"dropdown", "combobox", "multiselect", "select"}:
                continue

            # Make a stable-ish id
            field_id = node.get("id") or node.get("data-automation-id")
            if not field_id:
                continue
            field_id = str(field_id)

            if field_id in seen_ids:
                continue

            # label: try aria-labelledby on container, then nearby text
            label = resolve_aria_labelledby(node) or norm(node.get("aria-label")) or ""
            if not label:
                # try sibling/ancestor label-ish nodes
                parent = node.parent
                hop = 0
                while parent is not None and hop < 5 and not label:
                    # Workday sometimes has label in previous sibling div/span
                    prev = parent.find(["label", "span", "div"])
                    t = text_of(prev)
                    if 0 < len(t) <= 80:
                        label = t
                        break
                    parent = parent.parent
                    hop += 1

            label = label or field_id
            required = (node.get("aria-required") == "true") or label.endswith("*")

            fields.append(
                DiscoveredField(
                    field_id=field_id,
                    label=label,
                    type="select",          # treat as select for your pipeline
                    required=required,
                    options=[],             # options usually not in DOM until opened
                    section=None,
                    placeholder=None,
                    raw_name=None,
                    source_portal=self.name,
                )
            )
            seen_ids.add(field_id)

        # PASS C: radio groups (optional but useful)
        # If Workday uses role="radiogroup", capture the group with options if present in DOM
        for group in root.find_all(attrs={"role": "radiogroup"}):
            field_id = group.get("id") or group.get("data-automation-id") or "radiogroup"
            field_id = str(field_id)

            if field_id in seen_ids:
                continue

            label = resolve_aria_labelledby(group) or norm(group.get("aria-label")) or ""
            if not label:
                # look for a nearby legend/heading
                legend = group.find_previous(["legend", "h1", "h2", "h3", "h4", "label", "span", "div"])
                t = text_of(legend)
                if 0 < len(t) <= 80:
                    label = t

            label = label or field_id

            options: List[str] = []
            # Try to find option labels
            for opt_label in group.find_all("label"):
                t = text_of(opt_label)
                if t and t not in options:
                    options.append(t)

            required = (group.get("aria-required") == "true") or label.endswith("*")

            fields.append(
                DiscoveredField(
                    field_id=field_id,
                    label=label,
                    type="radio",
                    required=required,
                    options=options,
                    section=None,
                    placeholder=None,
                    raw_name=None,
                    source_portal=self.name,
                )
            )
            seen_ids.add(field_id)

        return fields
