"""자료 생성기 (v4): 표 사이 연결, 계산 열, 심은 사실이 설계도대로 정확히 들어가는지."""

import csv
import io
from collections import Counter

import pytest

from ai.src.datagen import Condition, DataPlan, FactPlan, build_dataset, check_plan
from ai.src.llms.fake import fake_response

SEED = 42


@pytest.fixture
def plan() -> DataPlan:
    return fake_response(DataPlan)  # 온새리빙 예시: stores / products / sales_daily / transfer_requests + 사실 4개


def _rows(data, filename: str) -> list[dict]:
    ds = next(d for d in data.datasets if d.filename == filename)
    return list(csv.DictReader(io.StringIO(ds.csv)))


def test_same_plan_and_seed_gives_same_csv(plan):
    a, b = build_dataset(plan, SEED), build_dataset(plan, SEED)
    assert not a.errors
    assert [d.csv for d in a.datasets] == [d.csv for d in b.datasets]


def test_references_and_lookups_are_consistent(plan):
    data = build_dataset(plan, SEED)
    stores = {r["store_code"]: r["store_name"] for r in _rows(data, "stores.csv")}
    sales = _rows(data, "sales_daily.csv")
    assert {r["store_code"] for r in sales} <= set(stores)
    # 표기 변형(H2)을 심은 강남점 외에는 지점명이 지점 목록과 같다
    assert all(r["store_name"] == stores[r["store_code"]] for r in sales if r["store_code"] != "ST-001")
    assert all(int(r["gross_sales"]) == int(r["qty"]) * int(r["unit_price"]) for r in sales)


def test_reference_column_is_marked(plan):
    data = build_dataset(plan, SEED)
    sales = next(d for d in data.datasets if d.filename == "sales_daily.csv")
    refs = {c.name: c.references for c in sales.columns}
    assert refs["store_code"] == "stores.store_code" and refs["store_name"] is None


def test_planted_facts_are_exact(plan):
    data = build_dataset(plan, SEED)
    sales = _rows(data, "sales_daily.csv")

    dup = Counter(tuple(r.values()) for r in sales if r["sale_date"] == "2026-03-31")
    assert sum(n - 1 for n in dup.values()) == 15  # H1 중복 15행
    assert not [r for r in sales if r["store_code"] == "ST-010" and r["sale_date"] == "2026-04-02"]  # H3 누락
    assert {r["store_name"] for r in sales if r["store_code"] == "ST-001"} & {"강남 점", "강남"}  # H2 표기 변형

    checks = {h.id: h for h in data.hidden_checks}
    assert set(checks) == {"H1", "H2", "H3", "H4"}
    assert "15행" in checks["H1"].location  # 적용 행 수를 코드가 계산해 남긴다


def test_fact_matching_nothing_is_an_error(plan):
    plan.facts.append(
        FactPlan(id="H9", title="없는 지점", kind="drop_rows", table="sales_daily",
                 where=[Condition(column="store_code", value="ST-999")], how_to_check="-")
    )
    data = build_dataset(plan, SEED)
    assert any("H9" in e and "0행" in e for e in data.errors)


def test_public_fact_becomes_note_not_hidden(plan):
    plan.facts[1].public = True  # H2 표기 변형을 공개 한계로
    data = build_dataset(plan, SEED)
    assert "강남점 지점명 표기 변형" in data.public_notes
    assert "H2" not in {h.id for h in data.hidden_checks}


def test_plan_errors_are_reported(plan):
    plan.tables[2].columns[1].ref = "shops.store_code"  # 없는 표
    plan.tables[2].columns[6].expr = "qty * price"  # 없는 열
    errors = check_plan(plan)
    assert any("ref" in e for e in errors) and any("계산식" in e for e in errors)
    assert build_dataset(plan, SEED).datasets == []
