"""The SQL migrations (Postgres) must stay in sync with the ORM models used by SQLite/dev."""

import pytest
import sqlglot
from sqlglot import exp

from drishti.db.migrate import MIGRATIONS, pending, render, required_var
from drishti.db.models import Base


def _tables(sql: str) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for stmt in sqlglot.parse(sql, dialect="postgres"):
        if isinstance(stmt, exp.Create) and stmt.args.get("kind") == "TABLE":
            schema = stmt.this
            name = schema.this.name
            out[name] = {c.name for c in schema.expressions if isinstance(c, exp.ColumnDef)}
    return out


def test_core_schema_matches_orm_models():
    sql = (MIGRATIONS / "001_core_schema.sql").read_text()
    sql_tables = _tables(sql)
    for table in Base.metadata.sorted_tables:
        assert table.name in sql_tables, f"{table.name} missing from migrations"
        assert {c.name for c in table.columns} == sql_tables[table.name], f"column drift in {table.name}"


def test_all_migrations_parse_as_postgres():
    for f in sorted(MIGRATIONS.glob("*.sql")):
        sql = render(f.read_text(), {"EMBEDDING_DIM": "768", "READONLY_PASSWORD": "x"})
        assert sqlglot.parse(sql, dialect="postgres"), f.name


def test_migrations_are_ordered_and_numbered():
    names = [p.name for p in sorted(MIGRATIONS.glob("*.sql"))]
    assert names == sorted(names) and all(n[:3].isdigit() for n in names) and len(names) >= 3
    assert [p.name for p in pending({names[0]})] == names[1:]


def test_render_substitutes_and_rejects_unset_vars():
    assert render("vector({{EMBEDDING_DIM}})", {"EMBEDDING_DIM": "768"}) == "vector(768)"
    assert render("'{{P}}'", {"P": "a'b"}) == "'a''b'"  # quotes escaped
    with pytest.raises(KeyError):
        render("{{NOPE}}", {})


def test_optional_file_declares_its_requirement():
    assert required_var((MIGRATIONS / "003_readonly_role.sql").read_text()) == "READONLY_PASSWORD"
    assert required_var((MIGRATIONS / "001_core_schema.sql").read_text()) is None


def test_default_label_never_granted_to_agent_role():
    sql = (MIGRATIONS / "003_readonly_role.sql").read_text()
    grant = sql[sql.index("GRANT SELECT ("): sql.index("ON customers")]
    assert "default_label" not in grant
