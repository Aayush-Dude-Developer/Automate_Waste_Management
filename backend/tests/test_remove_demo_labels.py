from datetime import date
import re

from backend.seed_purchase_demo import build_documents


def test_generated_purchase_records_use_operational_names_and_ids():
    records = build_documents(date(2026, 10, 11))

    for _path, document_id, document in records:
        flattened = f"{document_id} " + " ".join(str(value) for value in document.values())
        assert not re.search(r"(?i)(?<![A-Za-z0-9])(sample|demo|testing|dummy)(?=$|[^A-Za-z0-9])", flattened)
