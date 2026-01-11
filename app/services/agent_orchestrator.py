from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.store import Profile, store
from app.schemas.agent import AgentStep
from app.schemas.discovery import DiscoveredField
from app.services.portals.registry import pick_adapter


@dataclass
class AgentState:
    user_id: str
    goal: str
    constraints: Dict[str, Any]
    profile: Optional[Profile]
    context: Dict[str, Any]
    proposed_answers: Dict[str, str] = field(default_factory=dict)
    last_error: Optional[str] = None
    observations: List[Dict[str, Any]] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    retries: Dict[str, int] = field(default_factory=dict)
    plan: List[Dict[str, Any]] = field(default_factory=list)
    plan_index: int = 0
    job_analysis: Dict[str, Any] = field(default_factory=dict)
    fit_score: Optional[float] = None
    apply_decision: Optional[str] = None  # apply | skip | blocked
    selected_resume_id: Optional[str] = None
    missing_fields: List[str] = field(default_factory=list)
    user_answers: Dict[str, Any] = field(default_factory=dict)
    portal: Optional[str] = None
    discovered_fields: List[Dict[str, Any]] = field(default_factory=list)
    fill_actions: List[Dict[str, Any]] = field(default_factory=list)
    canonical_field_map: Dict[str, str] = field(default_factory=dict)
    step: int = 0
    completed: bool = False
    status: str = "planning"


class AgentOrchestrator:
    """Think-Act-Observe-Decide loop driving application filling."""

    def __init__(self) -> None:
        self.tools = {
            "fetch_profile": self._tool_fetch_profile,
            "map_fields": self._tool_map_fields,
            "draft_answers": self._tool_draft_answers,
            "request_user_input": self._tool_request_user_input,
            "analyze_job": self._tool_analyze_job,
            "score_fit": self._tool_score_fit,
            "decide_apply_strategy": self._tool_decide_apply_strategy,
            "select_resume": self._tool_select_resume,
            "identify_missing_fields": self._tool_identify_missing_fields,
            "build_application_package": self._tool_build_application_package,
            "detect_portal": self._tool_detect_portal,
            "discover_fields": self._tool_discover_fields,
            "map_to_canonical": self._tool_map_to_canonical,
            "build_fill_actions": self._tool_build_fill_actions,
        }

    def decide_next_tool(self, state: AgentState) -> Optional[str]:
        if state.profile is None or not getattr(state.profile, "skills", []):
            return "fetch_profile"

        if not state.job_analysis:
            return "analyze_job"

        if state.fit_score is None:
            return "score_fit"

        # Resume selection: only if DB available, otherwise skip once
        if state.selected_resume_id is None and not state.context.get("resume_selection_skipped"):
            if state.constraints.get("db_available", False):
                return "select_resume"
            state.context["resume_selection_skipped"] = True

        if state.apply_decision is None:
            return "decide_apply_strategy"
        if state.apply_decision == "skip":
            return None

        if "fields" not in state.context:
            return "map_fields"

        if not state.proposed_answers:
            return "draft_answers"

        if "portal" not in state.context:
            return "detect_portal"

        if "discovered_fields" not in state.context:
            return "discover_fields"

        if "canonical_field_map" not in state.context:
            return "map_to_canonical"

        if "fill_actions" not in state.context:
            return "build_fill_actions"

        if not state.context.get("missing_fields_checked"):
            return "identify_missing_fields"

        if not state.context.get("application_package"):
            return "build_application_package"

        return None

    def run(
        self,
        user_id: str,
        goal: str,
        job_context: Dict[str, Any],
        user_profile: Optional[Profile],
        constraints: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None,
        return_meta: bool = False,
        user_inputs: Optional[Dict[str, Any]] = None,
    ):
        constraints = constraints or {}
        max_steps = constraints.get("max_steps", 6)
        state = AgentState(
            user_id=user_id,
            goal=goal,
            constraints=constraints,
            profile=user_profile or store.profiles.get(user_id),
            context=job_context or {},
        )
        if db is not None:
            facts = self._load_user_facts(db, user_id)
            if facts:
                state.context.setdefault("user_facts", {})
                state.context["user_facts"].update(facts)
                state.context.update(facts)
        if user_inputs is not None:
            state.context.setdefault("user_inputs", {})
            state.context["user_inputs"].update(user_inputs)
            state.context.update(user_inputs)
            state.context["missing_fields_checked"] = False
            if db is not None:
                self._persist_user_facts(db, user_id, user_inputs)

        if constraints and isinstance(constraints.get("user_inputs"), dict):
            state.context.setdefault("user_inputs", {})
            state.context["user_inputs"].update(constraints["user_inputs"])

        state.constraints["db_available"] = db is not None
        run_db_obj = None
        if db is not None:
            from app.models.db_models import AgentRun  # local import to avoid cycle
            run_db_obj = AgentRun(
                user_id=user_id,
                goal=goal,
                status="planning",
                fit_score=None,
                selected_resume_id=None,
            )
            db.add(run_db_obj)
            db.commit()
            db.refresh(run_db_obj)
            state.context["run_id"] = str(run_db_obj.id)

        steps: List[AgentStep] = []

        while state.step < max_steps and not state.completed:
            current_step = state.step + 1
            tool = self.decide_next_tool(state)

            if tool is None:
                state.completed = True
                state.status = "completed"
                break

            plan_details = {
                "chosen_tool": tool,
                "reason": self._reason_for_tool(tool, state),
                "success_criteria": self._success_for_tool(tool),
                "step": state.step,
                "next_step": state.step + 1,
                "current_step": state.step,
                "tool": tool,
            }
            plan_step = AgentStep(name="plan", status="thinking", details=plan_details, tool=tool)
            steps.append(plan_step)
            self._log_step(db, run_db_obj, current_step, plan_step)

            current_step = state.step + 1
            try:
                result = self.tools[tool](state, db=db)
            except Exception as exc:  # noqa: BLE001
                state.step = current_step
                retries = state.retries.get(tool, 0) + 1
                state.retries[tool] = retries
                state.last_error = str(exc)
                failed_step = AgentStep(
                    name=tool,
                    status="failed",
                    details={"error": state.last_error, "retry": retries},
                    tool=tool,
                )
                steps.append(failed_step)
                self._log_step(db, run_db_obj, current_step, failed_step)
                if retries > 1:
                    state.status = "blocked"
                    state.completed = True
                continue

            state.step = current_step

            # Observe
            state.observations.append(
                {"step": current_step, "tool": tool, "result": result, "timestamp": datetime.utcnow().isoformat()}
            )
            state.actions.append(
                {"step": current_step, "tool": tool, "inputs": self._inputs_for_tool(tool, state)}
            )

            # Update state
            if "profile" in result:
                state.profile = result["profile"]
            if "context" in result:
                state.context.update(result["context"])
            if "answers" in result:
                state.proposed_answers.update(result["answers"])
            if "portal" in result:
                state.portal = result["portal"]
                state.context["portal"] = result["portal"]
            if "discovered_fields" in result:
                state.discovered_fields = result["discovered_fields"]
                state.context["discovered_fields"] = result["discovered_fields"]
            if "canonical_field_map" in result:
                state.canonical_field_map = result["canonical_field_map"]
                state.context["canonical_field_map"] = result["canonical_field_map"]
            if "fill_actions" in result:
                state.fill_actions = result["fill_actions"]
                state.context["fill_actions"] = result["fill_actions"]
            if "missing_fields" in result:
                state.missing_fields = result["missing_fields"]
                state.context["missing_fields_checked"] = True
            if "application_package" in result:
                state.context["application_package"] = result["application_package"]
            if "selected_resume_id" in result and result.get("selected_resume_id"):
                state.selected_resume_id = result["selected_resume_id"]

            # Validation after map_fields
            if tool == "map_fields":
                job_desc = state.context.get("job_description", "")
                if not job_desc or len(job_desc.strip()) < 20:
                    state.last_error = "Job description missing or too short; need user input."
                    state.status = "blocked"
                    state.completed = True
                    user_prompt = self._tool_request_user_input(state)
                    steps.append(
                        AgentStep(
                            name="request_user_input",
                            status="acted",
                            details={
                                "result": user_prompt.get("note", ""),
                                "question": "Please paste the job description or key requirements.",
                            },
                            tool="request_user_input",
                        )
                    )
                    break

            if tool == "identify_missing_fields":
                missing = state.context.get("missing_fields", [])
                identify_step = AgentStep(
                    name="identify_missing_fields",
                    status="acted",
                    details={"missing_fields": missing, "missing_count": len(missing)},
                    tool="identify_missing_fields",
                )
                steps.append(identify_step)
                self._log_step(db, run_db_obj, current_step, identify_step)
                if missing:
                    state.last_error = "Missing required fields; need user input."
                    state.status = "blocked"
                    state.completed = True
                    next_questions = state.context.get("next_questions", [])
                    user_step = AgentStep(
                        name="request_user_input",
                        status="acted",
                        details={"result": "User input required to proceed.", "questions": next_questions},
                        tool="request_user_input",
                    )
                    steps.append(user_step)
                    self._log_step(db, run_db_obj, current_step, user_step)
                    break
            else:
                note = "done"
                if isinstance(result, dict):
                    note = result.get("note") or result.get("result") or "done"

                acted_step = AgentStep(
                    name=tool,
                    status="acted",
                    details={"result": note},
                    tool=tool,
                )
                steps.append(acted_step)
                self._log_step(db, run_db_obj, current_step, acted_step)


        if not state.completed:
            state.status = "completed"
            state.completed = True

        finish_step = AgentStep(
            name="finish",
            status=state.status if state.status in {"completed", "blocked", "failed"} else "completed",
            details={"summary": "Agent loop finished", "last_error": state.last_error},
        )
        steps.append(finish_step)
        self._log_step(db, run_db_obj, state.step + 1, finish_step)

        if db is not None and run_db_obj is not None:
            run_db_obj.status = state.status
            run_db_obj.fit_score = state.fit_score
            run_db_obj.selected_resume_id = state.selected_resume_id
            db.add(run_db_obj)
            db.commit()

        meta = {
            "missing_fields": state.context.get("missing_fields", []),
            "next_questions": state.context.get("next_questions", []),
        }
        if return_meta:
            return steps, state.proposed_answers, meta
        return steps, state.proposed_answers

    def _reason_for_tool(self, tool: str, state: AgentState) -> str:
        if tool == "fetch_profile":
            return "Profile missing or lacks skills."
        if tool == "analyze_job":
            return "Need to parse job description for requirements."
        if tool == "score_fit":
            return "Need to compute fit against profile."
        if tool == "decide_apply_strategy":
            return "Need decision to apply or skip."
        if tool == "map_fields":
            return "Form fields not mapped yet."
        if tool == "draft_answers":
            return "Need answers for mapped fields."
        if tool == "request_user_input":
            return "Need user input to continue."
        if tool == "identify_missing_fields":
            return "Ensure required fields are present."
        if tool == "build_application_package":
            return "Package application payload for submission."
        if tool == "detect_portal":
            return "Detect which job portal is in use."
        if tool == "discover_fields":
            return "Discover form fields on the portal."
        if tool == "map_to_canonical":
            return "Map portal fields to canonical keys."
        if tool == "build_fill_actions":
            return "Generate fill actions for the portal."
        return "Progress towards goal."

    def _success_for_tool(self, tool: str) -> str:
        if tool == "fetch_profile":
            return "Profile loaded with skills."
        if tool == "analyze_job":
            return "Job description parsed with requirements."
        if tool == "score_fit":
            return "Fit score computed."
        if tool == "decide_apply_strategy":
            return "Decision made to apply or skip."
        if tool == "map_fields":
            return "Fields mapped in context."
        if tool == "draft_answers":
            return "Proposed answers generated."
        if tool == "request_user_input":
            return "User provides missing information."
        if tool == "identify_missing_fields":
            return "Missing fields identified or confirmed complete."
        if tool == "build_application_package":
            return "Application package prepared."
        if tool == "detect_portal":
            return "Portal detected or defaulted."
        if tool == "discover_fields":
            return "Form fields extracted."
        if tool == "map_to_canonical":
            return "Fields mapped to canonical keys."
        if tool == "build_fill_actions":
            return "Fill actions generated."
        return "Tool executed."

    def _inputs_for_tool(self, tool: str, state: AgentState) -> Dict[str, Any]:
        if tool == "fetch_profile":
            return {"user_id": state.user_id}
        if tool == "map_fields":
            job_desc = state.context.get("job_description", "")
            return {"job_description_preview": job_desc[:50]}
        if tool == "draft_answers":
            fields = list(state.context.get("fields", {}).keys())
            return {"fields": fields, "skills_count": len(getattr(state.profile, "skills", []) or [])}
        if tool == "request_user_input":
            return {"prompt": "Please paste the job description or key requirements."}
        if tool == "analyze_job":
            jd = state.context.get("job_description", "")
            return {"job_description_preview": jd[:80]}
        if tool == "score_fit":
            return {
                "profile_skills": getattr(state.profile, "skills", []),
                "must_have": state.job_analysis.get("must_have_skills", []),
                "nice_to_have": state.job_analysis.get("nice_to_have_skills", []),
            }
        if tool == "decide_apply_strategy":
            return {"fit_score": state.fit_score, "threshold": state.constraints.get("min_fit_score", 0.6)}
        if tool == "select_resume":
            return {"resumes_checked": True, "target_resume_type": state.constraints.get("target_resume_type")}
        if tool == "identify_missing_fields":
            return {"required_fields": ["work_authorization", "notice_period", "expected_salary", "relocation", "visa_sponsorship", "location"]}
        if tool == "build_application_package":
            return {"has_answers": bool(state.proposed_answers), "selected_resume_id": state.selected_resume_id}
        if tool == "detect_portal":
            return {"page_url": state.context.get("page_url")}
        if tool == "discover_fields":
            return {"portal": state.context.get("portal"), "page_url": state.context.get("page_url")}
        if tool == "map_to_canonical":
            return {"discovered_fields": len(state.context.get("discovered_fields", []))}
        if tool == "build_fill_actions":
            return {"fill_actions": len(state.context.get("fill_actions", []))}
        return {}

    def _canonical_key_for_field(self, field: Dict[str, Any]) -> Optional[str]:
        if hasattr(field, "dict"):
            field = field.dict()

        def normalize(text: Optional[str]) -> str:
            return (text or "").strip().lower()

        haystack = " ".join(
            [
                normalize(field.get("label")),
                normalize(field.get("raw_name")),
                normalize(field.get("placeholder")),
                normalize(field.get("type")),
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

    def _tool_fetch_profile(self, state: AgentState, db: Optional[Session] = None) -> Dict[str, Any]:
        profile = state.profile

        if state.user_id in store.profiles:
            profile = store.profiles[state.user_id]
            note = "Loaded existing profile with skills."
            return {"profile": profile, "note": note}

        job_desc = state.context.get("job_description", "")
        seed_skills = []

        jd_lower = job_desc.lower()
        for kw in ["python", "fastapi", "sql", "docker", "rest", "postgresql"]:
            if kw in jd_lower:
                seed_skills.append(kw.upper() if kw == "sql" else kw)

        profile = profile or Profile(user_id=state.user_id, skills=seed_skills)
        note = f"No profile on record; bootstrapped skills from job description: {seed_skills or 'none'}."
        return {"profile": profile, "note": note}


    def _tool_map_fields(self, state: AgentState, db: Optional[Session] = None) -> Dict[str, Any]:
        context = dict(state.context)
        job_desc = context.get("job_description", "")
        fields = {
            "cover_letter": "cover_letter",
            "key_skills": "key_skills",
            "years_experience": "years_experience",
        }
        context["fields"] = fields
        note = f"Mapped fields for job description length {len(job_desc)}."
        return {"context": context, "note": note}

    def _tool_draft_answers(self, state: AgentState, db: Optional[Session] = None) -> Dict[str, Any]:
        fields = state.context.get("fields", {})
        skills = ", ".join(getattr(state.profile, "skills", []) or ["relevant technologies"])
        answers = {
            fields.get("cover_letter", "cover_letter"): (
                f"Excited to apply. Background in {skills} aligns with the role."
            ),
            fields.get("key_skills", "key_skills"): skills,
            fields.get("years_experience", "years_experience"): state.constraints.get("years_experience", "5"),
        }
        note = "Drafted answers using profile skills."
        return {"answers": answers, "note": note}

    def _tool_request_user_input(self, state: AgentState, db: Optional[Session] = None) -> Dict[str, Any]:
        note = "User input required to proceed."
        return {"note": note}

    def _tool_analyze_job(self, state: AgentState, db: Optional[Session] = None) -> Dict[str, Any]:
        jd = (state.context.get("job_description") or "").lower()
        must_have = []
        nice_to_have = []
        keywords = []
        seniority = "mid"

        heuristics_must = ["python", "fastapi", "sql", "postgres", "machine learning", "ml", "data"]
        heuristics_nice = ["aws", "gcp", "azure", "docker", "kubernetes", "llm", "langchain", "vector"]

        for term in heuristics_must:
            if term in jd:
                must_have.append(term)
        for term in heuristics_nice:
            if term in jd:
                nice_to_have.append(term)

        keywords = list(set(must_have + nice_to_have))

        import re

        years_matches = re.findall(r"(\\d+)\\+?\\s*years", jd)
        if years_matches:
            max_years = max(int(y) for y in years_matches)
            if max_years >= 8:
                seniority = "senior"
            elif max_years <= 2:
                seniority = "junior"
            else:
                seniority = "mid"

        job_analysis = {
            "must_have_skills": must_have,
            "nice_to_have_skills": nice_to_have,
            "keywords": keywords,
            "seniority_guess": seniority,
        }
        state.job_analysis = job_analysis
        return {"note": "Analyzed job description.", "job_analysis": job_analysis}

    def _tool_score_fit(self, state: AgentState, db: Optional[Session] = None) -> Dict[str, Any]:
        profile_skills = [s.lower() for s in getattr(state.profile, "skills", []) or []]
        must_have = [s.lower() for s in state.job_analysis.get("must_have_skills", [])]
        nice_to_have = [s.lower() for s in state.job_analysis.get("nice_to_have_skills", [])]

        must_hits = sum(1 for s in must_have if s in profile_skills)
        nice_hits = sum(1 for s in nice_to_have if s in profile_skills)

        must_total = max(len(must_have), 1)
        nice_total = max(len(nice_to_have), 1)

        score = (2 * (must_hits / must_total) + (nice_hits / nice_total)) / 3
        score = max(0.0, min(1.0, score))
        state.fit_score = score

        reasons = {
            "must_have_hit": must_hits,
            "must_have_total": len(must_have),
            "nice_have_hit": nice_hits,
            "nice_have_total": len(nice_to_have),
        }
        return {"note": f"Computed fit score {score:.2f}.", "fit_score": score, "reasons": reasons}

    def _tool_decide_apply_strategy(self, state: AgentState, db: Optional[Session] = None) -> Dict[str, Any]:
        threshold = float(state.constraints.get("min_fit_score", 0.6))
        decision = "apply" if (state.fit_score or 0) >= threshold else "skip"
        state.apply_decision = decision
        if decision == "skip":
            state.status = "skipped"
            state.completed = True
        return {"note": f"Decision: {decision} (threshold {threshold}).", "decision": decision, "threshold": threshold}


    def _tool_identify_missing_fields(self, state: AgentState, db: Optional[Session] = None) -> Dict[str, Any]:
        required_fields = [
            "work_authorization",
            "notice_period",
            "expected_salary",
            "relocation",
            "visa_sponsorship",
            "location",
        ]
        context = state.context or {}
        missing_fields = []
        for field in required_fields:
            value = context.get(field)
            if value is None:
                value = context.get("user_inputs", {}).get(field)
            if isinstance(value, str):
                is_valid = bool(value.strip())
            elif isinstance(value, bool):
                is_valid = True
            else:
                is_valid = value is not None
            if not is_valid:
                missing_fields.append(field)

        next_questions = []
        for field in missing_fields:
            if field in {"work_authorization", "relocation", "visa_sponsorship"}:
                next_questions.append(
                    {
                        "field": field,
                        "question": f"Please confirm your {field.replace('_', ' ')} (yes/no).",
                        "input_type": "boolean",
                        "options": ["yes", "no"],
                        "required": True,
                    }
                )
            else:
                next_questions.append(
                    {
                        "field": field,
                        "question": f"Please provide your {field.replace('_', ' ')}.",
                        "input_type": "text",
                        "options": None,
                        "required": True,
                    }
                )

        state.missing_fields = missing_fields
        if not missing_fields:
            return {
                "context": {"missing_fields_checked": True, "missing_fields": []},
                "note": "No missing fields.",
            }
        return {
            "context": {
                "missing_fields_checked": True,
                "missing_fields": missing_fields,
                "next_questions": next_questions,
            },
            "note": f"Missing fields: {', '.join(missing_fields)}",
        }

    def _tool_build_application_package(self, state: AgentState, db: Optional[Session] = None) -> Dict[str, Any]:
        package = {
            "selected_resume_id": state.selected_resume_id,
            "fit_score": state.fit_score,
            "decision": state.apply_decision,
            "proposed_answers": state.proposed_answers,
            "missing_fields": state.missing_fields,
            "portal": state.context.get("portal"),
            "discovered_fields": state.context.get("discovered_fields", []),
            "fill_actions": state.context.get("fill_actions", []),
        }
        state.context["application_package"] = package
        return {"note": "Prepared application package.", "application_package": package}

    def _tool_detect_portal(self, state: AgentState, db: Optional[Session] = None) -> Dict[str, Any]:
        url = state.context.get("page_url", "")
        html = state.context.get("page_html", "")
        adapter = pick_adapter(url, html)
        portal_name = getattr(adapter, "name", "generic")
        return {"note": f"Detected portal: {portal_name}", "portal": portal_name}

    def _tool_discover_fields(self, state: AgentState, db: Optional[Session] = None) -> Dict[str, Any]:
        import asyncio

        from app.services.portals.browser_fetch import fetch_html_with_playwright, looks_like_js_shell

        url = state.context.get("page_url", "")
        html = state.context.get("page_html", "") or ""

        adapter = pick_adapter(url, html)

        # 1) Try normal discovery first
        fields = adapter.discover_fields(url, html)

        # 2) Decide whether to retry with Playwright (discovery-only)
        should_retry = False
        if getattr(adapter, "name", "") == "workday":
            should_retry = True
        if len(fields) < 3 and looks_like_js_shell(html):
            should_retry = True

        browser_note = None
        if should_retry:
            snap = asyncio.run(fetch_html_with_playwright(url))
            browser_note = snap.notes
            if snap.used_browser and snap.html:
                # Re-pick adapter because final HTML may contain signals
                adapter2 = pick_adapter(snap.final_url or url, snap.html)
                fields2 = adapter2.discover_fields(snap.final_url or url, snap.html)

                # Use browser results if better
                if len(fields2) >= len(fields):
                    fields = fields2
                    state.context["page_html"] = snap.html
                    state.context["page_url"] = snap.final_url or url
                    adapter = adapter2
                    state.context["portal"] = getattr(adapter2, "name", state.context.get("portal"))

        serialized = [field.dict() for field in fields]

        note = f"Discovered {len(serialized)} fields using {getattr(adapter, 'name', 'generic')}."
        if browser_note:
            note += f" Browser: {browser_note}"

        return {"note": note, "discovered_fields": serialized}


    def _tool_map_to_canonical(self, state: AgentState, db: Optional[Session] = None) -> Dict[str, Any]:
        discovered = state.context.get("discovered_fields", [])
        canonical_map: Dict[str, str] = {}
        for field in discovered:
            field_dict = field.dict() if isinstance(field, DiscoveredField) else field
            key = self._canonical_key_for_field(field_dict)
            if key:
                canonical_map[str(field_dict.get("field_id"))] = key
        return {"note": "Mapped fields to canonical keys.", "canonical_field_map": canonical_map}

    def _tool_build_fill_actions(self, state: AgentState, db: Optional[Session] = None) -> Dict[str, Any]:
        url = state.context.get("page_url", "")
        html = state.context.get("page_html", "")
        adapter = pick_adapter(url, html)
        fields = []
        for field in state.context.get("discovered_fields", []):
            if isinstance(field, DiscoveredField):
                fields.append(field)
            else:
                fields.append(DiscoveredField(**field))
        answers: Dict[str, str] = {}
        answers.update(state.proposed_answers)
        answers.update(state.context.get("user_inputs", {}))
        actions = adapter.build_fill_actions(fields, answers)
        serialized = [action.dict() for action in actions]
        return {"note": f"Built {len(serialized)} fill actions.", "fill_actions": serialized}

    def _tool_select_resume(self, state: AgentState, db: Optional[Session] = None) -> Dict[str, Any]:
        if db is None:
            return {
                "context": {"resume_selection_skipped": True},
                "note": "DB not provided; skipping resume selection.",
                }

        from app.models.db_models import Resume  # local import to avoid cycle

        resumes = (
            db.query(Resume)
            .filter(Resume.user_id == state.user_id)
            .all()
        )
        if not resumes:
            return {"note": "No resumes found; skipping selection."}

        must_have = [s.lower() for s in state.job_analysis.get("must_have_skills", [])]
        nice_to_have = [s.lower() for s in state.job_analysis.get("nice_to_have_skills", [])]
        target_type = (state.constraints or {}).get("target_resume_type")

        def score_resume(resume: Resume) -> float:
            parsed = resume.parsed_json or {}
            skills = [s.lower() for s in parsed.get("skills", [])] if isinstance(parsed, dict) else []
            text_blobs = " ".join(parsed.get("projects", []) if isinstance(parsed, dict) else [])
            if isinstance(text_blobs, list):
                text_blobs = " ".join(text_blobs)
            text_lower = text_blobs.lower() if text_blobs else ""
            must_hits = sum(1 for s in must_have if s in skills or s in text_lower)
            nice_hits = sum(1 for s in nice_to_have if s in skills or s in text_lower)
            base = 2 * must_hits + nice_hits
            if target_type and resume.resume_type and resume.resume_type.lower() == str(target_type).lower():
                base += 1.5
            return base

        best = None
        best_score = -1.0
        for res in resumes:
            s = score_resume(res)
            if s > best_score:
                best = res
                best_score = s

        if best:
            state.selected_resume_id = str(best.id)
            return {
                "note": f"Selected resume {best.id}",
                "selected_resume_id": str(best.id),
                "score": best_score,
                "resume_type": best.resume_type,
            }
        return {"note": "Unable to select a resume."}

    def _log_step(self, db: Optional[Session], run_db_obj: Any, step_num: int, step: AgentStep) -> None:
        if db is None or run_db_obj is None:
            return
        from app.models.db_models import AgentStepLog  # local import to avoid cycle

        db_entry = AgentStepLog(
            run_id=run_db_obj.id,
            step_num=step_num,
            name=step.name,
            tool=step.tool,
            status=step.status,
            details=step.details,
        )
        db.add(db_entry)
        db.commit()

    def _load_user_facts(self, db: Session, user_id: str) -> Dict[str, Any]:
        from app.models.db_models import UserFact  # local import to avoid cycle

        facts = db.query(UserFact).filter(UserFact.user_id == user_id).all()
        return {fact.key: fact.value for fact in facts}

    def _persist_user_facts(self, db: Session, user_id: str, user_inputs: Dict[str, Any]) -> None:
        from app.models.db_models import UserFact  # local import to avoid cycle

        if not user_inputs:
            return
        now = datetime.utcnow()
        for key, value in user_inputs.items():
            if value is None:
                continue
            existing = (
                db.query(UserFact)
                .filter(UserFact.user_id == user_id, UserFact.key == key)
                .one_or_none()
            )
            if existing:
                existing.value = value
                existing.source = "user_confirmed"
                existing.last_confirmed_at = now
                existing.updated_at = now
                db.add(existing)
            else:
                db.add(
                    UserFact(
                        user_id=user_id,
                        key=key,
                        value=value,
                        source="user_confirmed",
                        last_confirmed_at=now,
                        created_at=now,
                        updated_at=now,
                    )
                )
        db.commit()


agent_orchestrator = AgentOrchestrator()
