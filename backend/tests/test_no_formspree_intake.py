from pathlib import Path


def test_intake_form_has_no_formspree_dependency():
    intake_source = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "src"
        / "pages"
        / "IntakeForm.js"
    ).read_text(encoding="utf-8")

    forbidden = [
        "formspree.io",
        "REACT_APP_FORMSPREE_ID",
        "VITE_FORMSPREE_ID",
        "formspreePayload",
        "formspreePromise",
        "isPlaceholderId",
        "Simulation Sandbox",
    ]

    for token in forbidden:
        assert token not in intake_source, f"Clinical intake must not depend on Formspree: found {token}"

    assert "/clinical/intake" in intake_source
