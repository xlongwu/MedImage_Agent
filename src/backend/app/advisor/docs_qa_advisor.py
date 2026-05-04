"""Docs Q&A Advisor — answer questions using project documentation."""
from __future__ import annotations

from typing import Any

from src.backend.app.advisor.advisor_safety import (
    is_llm_enabled,
    wrap_advisor_response,
    advisor_fallback,
)


def advise_docs_qa(
    question: str = "",
    context_docs: list[str] | None = None,
) -> dict[str, Any]:
    context_docs = context_docs or []
    docs_content = _load_docs(context_docs)

    # Deterministic keyword matching
    keywords = question.lower().split()
    relevant_sections = []
    for doc_name, content in docs_content.items():
        score = sum(1 for kw in keywords if kw in content.lower())
        if score > 0:
            relevant_sections.append({"doc": doc_name, "relevance": score, "excerpt": content[:200]})

    relevant_sections.sort(key=lambda x: -x["relevance"])
    top = relevant_sections[:3]

    answer = f"Question: {question}\n\n"
    if top:
        answer += f"Found {len(relevant_sections)} relevant document sections.\n"
        for s in top:
            answer += f"- {s['doc']}: {s['excerpt'][:150]}...\n"
    else:
        answer += "No relevant documentation found for this question."

    result = {
        "question": question,
        "answer": answer,
        "source_docs": [s["doc"] for s in top],
        "related_topics": _suggest_related(keywords),
    }

    if is_llm_enabled():
        try:
            llm_answer = _llm_docs_qa(question, docs_content)
            result["answer"] = llm_answer
        except Exception:
            pass

    return wrap_advisor_response(result, "docs-qa")


def _load_docs(doc_list: list[str]) -> dict[str, str]:
    from pathlib import Path
    docs = {}
    for doc_name in doc_list:
        path = Path(doc_name)
        if path.exists() and path.is_file():
            try:
                docs[doc_name] = path.read_text(encoding="utf-8")[:2000]
            except Exception:
                docs[doc_name] = f"[Could not read {doc_name}]"
    # Always include README if available
    readme = Path("README.md")
    if readme.exists():
        docs["README.md"] = readme.read_text(encoding="utf-8")[:2000]
    return docs


def _suggest_related(keywords: list[str]) -> list[str]:
    topic_map = {
        "pipeline": ["SPM pipeline", "DPABI wrapper", "Python-only pipeline", "Pipeline YAML schema"],
        "spm": ["SPM preprocessing", "MATLAB integration", "SPM chain validation"],
        "dpabi": ["DPABI wrapper", "DPABI safety", "DPABI single function"],
        "qc": ["Motion QC", "Registration QC", "Normalization QC", "QC thresholds"],
        "error": ["Error Knowledge Base", "Error diagnosis", "Retry runtime"],
        "alff": ["ALFF/fALFF computation", "GPU ALFF", "Frequency band selection"],
        "reho": ["ReHo computation", "KCC algorithm", "Neighborhood size"],
        "fc": ["Functional Connectivity", "ROI correlation", "FC matrix"],
    }
    related = []
    for kw in keywords:
        for topic_kw, topics in topic_map.items():
            if topic_kw in kw and topics:
                related.extend(topics[:2])
    return list(set(related))[:5]


def _llm_docs_qa(question: str, docs_content: dict[str, str]) -> str:
    from src.backend.app.advisor.protocol_advisor import _call_llm
    from src.backend.app.advisor.advisor_safety import get_llm_config

    config = get_llm_config()
    docs_summary = "\n---\n".join(f"{k}: {v[:500]}" for k, v in docs_content.items())
    prompt = (
        f"Answer this question about the MedImage Agent project using the documentation below.\n\n"
        f"Question: {question}\n\n"
        f"Documentation:\n{docs_summary[:3000]}\n\n"
        f"Be concise. Do NOT suggest executing pipelines or modifying data."
    )
    return _call_llm(config, prompt)
