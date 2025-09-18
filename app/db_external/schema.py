from typing import Dict, Iterable, Optional, Set

from sqlalchemy import inspect, MetaData, Table, select, func, text
from sqlalchemy.engine import Engine
from .connection import get_sqlalchemy_engine


def _build_sqlalchemy_engine() -> Engine:
    # Reusa o helper centralizado no módulo de conexão
    return get_sqlalchemy_engine()


def _default_schema_for_dialect(dialect_name: str, inspector) -> Optional[str]:
    """Resolve o schema default por SGBD, usando o inspector quando possível."""
    try:
        # Disponível em várias engines
        default_from_inspector = getattr(inspector, "default_schema_name", None)
        if default_from_inspector:
            return default_from_inspector
    except Exception:
        pass
    if dialect_name == "postgresql":
        return "public"
    if dialect_name == "mssql":
        return "dbo"
    # MySQL não usa schema separado do database; Oracle usa o usuário atual
    return None


def get_db_schema(tables_and_columns: Dict[str, Optional[Iterable[str]]] | None = None) -> str:
    """
    Retorna o schema (tabelas, colunas, PK, índices/uniques, FKs, contagem e exemplos) do banco externo como string.

    tables_and_columns: dict opcional no formato {"tabela1": ["col1", "col2"], "tabela2": None, ...}
    Se None, pega todas as tabelas e colunas.
    """
    # Tenta criar engine e inspector; se falhar, retorna mensagem amigável para não derrubar o app
    try:
        engine = _build_sqlalchemy_engine()
        insp = inspect(engine)
    except Exception as e:
        return f"Schema indisponível no momento (erro de conexão/reflection): {e}"
    dialect = engine.dialect.name  # 'mysql', 'postgresql', 'oracle', 'mssql'
    target_schema = _default_schema_for_dialect(dialect, insp)

    # Lista de tabelas disponíveis no schema alvo
    try:
        tables_all = insp.get_table_names(schema=target_schema)
    except Exception as e:
        return f"Schema indisponível (falha ao listar tabelas): {e}"
    if tables_and_columns is None:
        tables = tables_all
    else:
        tables = [t for t in tables_all if t in tables_and_columns]

    # Normaliza filtro de colunas
    def allowed_for(table_name: str) -> Optional[Set[str]]:
        if tables_and_columns is None:
            return None
        if table_name not in tables_and_columns:
            return None
        cols = tables_and_columns[table_name]
        if not cols:  # None ou [] => todas
            return None
        return set(cols)

    lines: list[str] = []
    all_fks_global: list[tuple[str, str, str, str]] = []

    metadata = MetaData()
    try:
        with engine.connect() as conn:
            for table in tables:
                lines.append(f"Tabela: {table}")

                # Carrega metadados da tabela
                try:
                    tbl_obj = Table(table, metadata, schema=target_schema, autoload_with=engine)
                except Exception:
                    tbl_obj = None

                # Contagem de registros
                try:
                    if tbl_obj is not None:
                        count_val = conn.execute(select(func.count()).select_from(tbl_obj)).scalar_one()
                    else:
                        # Fallback simples
                        fq_name = f"{target_schema}.{table}" if target_schema else table
                        count_val = conn.execute(select(func.count()).select_from(text(fq_name))).scalar()
                    lines.append(f"  Total de registros: {count_val}")
                except Exception:
                    pass

                # Chave primária
                try:
                    pk_info = insp.get_pk_constraint(table, schema=target_schema) or {}
                    pk_cols = pk_info.get("constrained_columns") or []
                    if pk_cols:
                        lines.append(f"  Primary Key: {', '.join(pk_cols)}")
                except Exception:
                    pass

                # Uniques e Indexes
                unique_cols: Set[str] = set()
                normal_idx_cols: Set[str] = set()
                try:
                    for uc in insp.get_unique_constraints(table, schema=target_schema) or []:
                        for c in uc.get("column_names") or []:
                            unique_cols.add(c)
                except Exception:
                    pass
                try:
                    for idx in insp.get_indexes(table, schema=target_schema) or []:
                        cols = idx.get("column_names") or []
                        if idx.get("unique"):
                            unique_cols.update(cols)
                        else:
                            normal_idx_cols.update(cols)
                except Exception:
                    pass
                if unique_cols:
                    lines.append(f"  Unique: {', '.join(sorted(unique_cols))}")
                if normal_idx_cols:
                    lines.append(f"  Indexes: {', '.join(sorted(normal_idx_cols))}")

                # Colunas detalhadas
                try:
                    cols_info = insp.get_columns(table, schema=target_schema)
                    allowed_cols = allowed_for(table)
                    for col in cols_info:
                        name = col.get("name") or col.get("key")
                        if allowed_cols and name not in allowed_cols:
                            continue
                        coltype = str(col.get("type"))
                        details = [f"{name} {coltype}"]
                        if not col.get("nullable", True):
                            details.append("NOT NULL")
                        if col.get("default") is not None:
                            details.append(f"DEFAULT {col['default']}")
                        if name in unique_cols:
                            details.append("UNIQUE")
                        lines.append(f"  Coluna: {' '.join(details)}")
                except Exception:
                    pass

                # Foreign keys
                try:
                    fks = insp.get_foreign_keys(table, schema=target_schema) or []
                    allowed_cols = allowed_for(table)
                    if fks:
                        lines.append("  Foreign Keys:")
                    for fk in fks:
                        cols = fk.get("constrained_columns") or []
                        ref_t = fk.get("referred_table")
                        ref_cols = fk.get("referred_columns") or []
                        for i, c in enumerate(cols):
                            if allowed_cols and c not in allowed_cols:
                                continue
                            ref_c = ref_cols[i] if i < len(ref_cols) else "?"
                            lines.append(f"    {c} -> {ref_t}.{ref_c}")
                            all_fks_global.append((table, c, ref_t or "?", ref_c))
                except Exception:
                    pass

                # Exemplos reais de dados
                try:
                    allowed_cols = allowed_for(table)
                    if tbl_obj is not None:
                        if allowed_cols:
                            cols = [tbl_obj.c[c] for c in tbl_obj.c.keys() if c in allowed_cols]
                            if not cols:  # se filtro não existe nas colunas, pula
                                cols = list(tbl_obj.c)
                            stmt = select(*cols).limit(3)
                        else:
                            stmt = select(tbl_obj).limit(3)
                        result = conn.execute(stmt).fetchall()
                        if result:
                            lines.append("  Exemplos de dados:")
                            for row in result:
                                mapping = getattr(row, "_mapping", None)
                                if mapping is not None:
                                    items = mapping.items()
                                else:
                                    # Fallback para tuplas sem nomes
                                    items = list(zip([c.key for c in (cols if allowed_cols else tbl_obj.c)], row))
                                if allowed_cols:
                                    items = [(k, v) for k, v in items if k in allowed_cols]
                                row_str = ", ".join([f"{k}: {v}" for k, v in items])
                                lines.append(f"    {row_str}")
                except Exception:
                    pass

    except Exception as e:
        lines.append(f"\nObservação: introspecção interrompida por erro de conexão/consulta: {e}")

    if all_fks_global:
        lines.append("\nRelações entre tabelas:")
        for t, col, ref_t, ref_col in all_fks_global:
            lines.append(f"  {t}.{col} -> {ref_t}.{ref_col}")

    return "\n".join(lines)
