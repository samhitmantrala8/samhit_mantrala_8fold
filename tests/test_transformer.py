from __future__ import annotations

import json
from pathlib import Path

from backend.transformer.pipeline import transform_paths


ROOT = Path(__file__).resolve().parents[1]


def test_default_profile_normalizes_and_merges_sources():
    result = transform_paths(
        [
            ROOT / "samples" / "recruiter_export.csv",
            ROOT / "samples" / "ats_profile.json",
            ROOT / "samples" / "recruiter_notes.txt",
        ],
        default_region="US",
    )
    profile = result["default_profile"]

    assert result["validation_errors"] == []
    assert profile["full_name"] == "Samhit Mantrala"
    assert profile["emails"][0] == "samhit.mantrala@example.com"
    assert profile["phones"][0] == "+14155550198"
    assert profile["links"]["github"] == "https://github.com/samhitmantrala8"
    assert any(skill["name"] == "React" for skill in profile["skills"])
    assert any(skill["name"] == "Python" for skill in profile["skills"])
    assert profile["provenance"]


def test_custom_projection_supports_renames_and_arrays():
    config = json.loads((ROOT / "configs" / "custom_output.json").read_text(encoding="utf-8"))
    result = transform_paths(
        [ROOT / "samples" / "recruiter_export.csv", ROOT / "samples" / "recruiter_notes.txt"],
        config=config,
        default_region="US",
    )
    projected = result["custom_output"]

    assert result["validation_errors"] == []
    assert projected["primary_email"] == "samhit.mantrala@example.com"
    assert projected["phone"] == "+14155550198"
    assert "React" in projected["skills"]
    assert "overall_confidence" in projected
    assert projected["provenance"]


def test_bad_or_sparse_source_degrades_gracefully():
    result = transform_paths([ROOT / "samples" / "bad_source.txt"], default_region="US")
    profile = result["default_profile"]

    assert result["validation_errors"] == []
    assert profile["candidate_id"].startswith("cand_")
    assert profile["full_name"] is None
    assert profile["emails"] == []


def test_resume_shaped_text_extracts_sections_without_llm(tmp_path):
    resume = tmp_path / "resume.txt"
    resume.write_text(
        """
Aarav Mehta Email: aarav@example.com LinkedIn : Aarav Mehta Mobile: +91-9876543210
GitHub : github.com/aaravmehta
Education
• Indian Institute of Information Technology Jabalpur Jabalpur, India
Bachelor of Technology - Computer Science and Engineering; CGPA: 8.5/10 November 2022 - May 2026
Courses: Data Structures and Algorithms, Artificial Intelligence, Database Management Systems
Experience
• MindTickle (SDE (Applied AI) Intern) Pune, Maharashtra, India
(Team: Centre of Excellence for Machine Learning) January 2026 - Present
? Developed asynchronous RPC services using gRPC, Kafka, Redis, protobuf, Golang, LangGraph ReAct Agent, RAG, AWS OpenSearch, Cohere-Rerank-3.5, Docker, Kubernetes and Helm Charts.
• CREW (Machine Learning Intern) Sydney, Australia (Remote)
(Team: Machine Learning) June 2025 - October 2025
? Deployed a Flask app on Google Cloud Run using FFMPeg and Google Cloud APIs.
Projects
• CodeForces Future Rating Predictor : Github Link: June 2025
? Tech Stack: ReactJS, TailwindCSS, Flask, MongoDB.
Skills Summary
• Programming Languages and Databases: C++, Golang, Python, MongoDB, MySQL
• Frameworks: ReactJS, Flask, FastAPI, LangGraph, PyTorch
""".strip(),
        encoding="utf-8",
    )

    result = transform_paths([resume], default_region="IN")
    profile = result["default_profile"]
    skill_names = {skill["name"] for skill in profile["skills"]}

    assert result["validation_errors"] == []
    assert profile["full_name"] == "Aarav Mehta"
    assert profile["phones"] == ["+919876543210"]
    assert profile["links"]["github"] == "https://github.com/aaravmehta"
    assert profile["education"][0]["institution"] == "Indian Institute of Information Technology Jabalpur"
    assert profile["education"][0]["field"] == "Computer Science and Engineering"
    assert profile["education"][0]["end_year"] == 2026
    assert profile["experience"][0]["company"] == "MindTickle"
    assert profile["experience"][0]["title"] == "SDE (Applied AI) Intern"
    assert profile["experience"][0]["start"] == "2026-01"
    assert profile["experience"][0]["end"] is None
    assert profile["headline"] == "SDE (Applied AI) Intern at MindTickle"
    assert {"Go", "Kafka", "Redis", "gRPC", "Kubernetes", "LangGraph", "ReAct Agents", "C++"} <= skill_names
