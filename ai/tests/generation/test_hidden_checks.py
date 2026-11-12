"""생성 설정에서 숨은 함정 목록을 만드는 규칙."""

from ai.src.datagen import ColumnSpec, DatasetSpec, hidden_checks_from_spec


def _spec(*columns: ColumnSpec) -> DatasetSpec:
    return DatasetSpec(filename="s.csv", columns=list(columns), n_rows=10)


def test_lists_only_planted_traps():
    spec = _spec(
        ColumnSpec(name="date", dtype="date", description="", null_rate=0.0),
        ColumnSpec(name="sales", dtype="int", description="", null_rate=0.03, anomaly_rate=0.02),
        ColumnSpec(name="branch", dtype="string", description="", anomaly_rate=0.1),  # 문자열엔 이상치가 안 심긴다
    )
    checks = hidden_checks_from_spec(spec)
    assert [c.title for c in checks] == ["sales 결측", "sales 이상치 (정상 범위의 5~10배)"]
    assert [c.id for c in checks] == ["H1", "H2"]


def test_clean_spec_has_no_traps():
    assert hidden_checks_from_spec(_spec(ColumnSpec(name="a", dtype="int", description=""))) == []
