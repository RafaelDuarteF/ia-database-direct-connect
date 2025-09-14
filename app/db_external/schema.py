import pymysql
from .connection import get_external_connection

import json
def get_db_schema(tables_and_columns: dict = None) -> str:
    """
    Retorna o schema (SHOW TABLES, DESCRIBE, exemplos e FKs) do banco externo como string formatada.
    tables_and_columns: dict opcional no formato {"tabela1": ["col1", "col2"], "tabela2": None, ...}
    Se None, pega todas as tabelas e colunas.
    """
    conn = get_external_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES;")
            all_tables = [row[list(row.keys())[0]] for row in cursor.fetchall()]
            # Se não passar filtro, pega todas
            if tables_and_columns is None:
                tables = all_tables
            else:
                tables = [t for t in all_tables if t in tables_and_columns]
            schema = []
            all_fks = []
            for table in tables:
                cursor.execute(f"DESCRIBE {table};")
                columns = cursor.fetchall()
                # Filtra colunas se necessário
                allowed_cols = None
                if tables_and_columns is not None and table in tables_and_columns:
                    # None ou [] significa todas as colunas
                    if tables_and_columns[table] is None:
                        allowed_cols = None
                    else:
                        allowed_cols = set(tables_and_columns[table])
                schema.append(f"Tabela: {table}")
                # Contagem de registros
                try:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table};")
                    count = cursor.fetchone()['count']
                    schema.append(f"  Total de registros: {count}")
                except Exception:
                    pass
                # Chave primária
                pk_cols = [col['Field'] for col in columns if col['Key'] == 'PRI']
                if pk_cols:
                    schema.append(f"  Primary Key: {', '.join(pk_cols)}")
                # Uniques e Indexes
                try:
                    cursor.execute(f"SHOW INDEX FROM {table};")
                    indexes = cursor.fetchall()
                    unique_indexes = set()
                    normal_indexes = set()
                    for idx in indexes:
                        if idx['Non_unique'] == 0:
                            unique_indexes.add(idx['Column_name'])
                        else:
                            normal_indexes.add(idx['Column_name'])
                    if unique_indexes:
                        schema.append(f"  Unique: {', '.join(sorted(unique_indexes))}")
                    if normal_indexes:
                        schema.append(f"  Indexes: {', '.join(sorted(normal_indexes))}")
                except Exception:
                    pass
                # Colunas detalhadas
                for col in columns:
                    if allowed_cols and col['Field'] not in allowed_cols:
                        continue
                    details = [f"{col['Field']} {col['Type']}"]
                    if col.get('Null', '').upper() == 'NO':
                        details.append("NOT NULL")
                    if col.get('Default') is not None:
                        details.append(f"DEFAULT {col['Default']}")
                    if col['Key'] == 'UNI':
                        details.append("UNIQUE")
                    schema.append(f"  Coluna: {' '.join(details)}")
                # Foreign keys
                cursor.execute(f"SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_NAME='{table}' AND REFERENCED_TABLE_NAME IS NOT NULL;")
                fks = cursor.fetchall()
                if fks:
                    schema.append(f"  Foreign Keys:")
                for fk in fks:
                    if allowed_cols and fk['COLUMN_NAME'] not in allowed_cols:
                        continue
                    schema.append(f"    {fk['COLUMN_NAME']} -> {fk['REFERENCED_TABLE_NAME']}.{fk['REFERENCED_COLUMN_NAME']}")
                    all_fks.append((table, fk['COLUMN_NAME'], fk['REFERENCED_TABLE_NAME'], fk['REFERENCED_COLUMN_NAME']))
                # Exemplos reais de dados
                try:
                    # Só seleciona as colunas permitidas
                    if allowed_cols:
                        col_list = ', '.join([f'`{c}`' for c in allowed_cols])
                        cursor.execute(f"SELECT {col_list} FROM {table} LIMIT 3;")
                    else:
                        cursor.execute(f"SELECT * FROM {table} LIMIT 3;")
                    rows = cursor.fetchall()
                    if rows:
                        schema.append(f"  Exemplos de dados:")
                        for row in rows:
                            # Só mostra as colunas permitidas
                            if allowed_cols:
                                row_str = ', '.join([f"{k}: {v}" for k, v in row.items() if k in allowed_cols])
                            else:
                                row_str = ', '.join([f"{k}: {v}" for k, v in row.items()])
                            schema.append(f"    {row_str}")
                except Exception:
                    pass
            # Bloco global de relações
            if all_fks:
                schema.append("\nRelações entre tabelas:")
                for t, col, ref_t, ref_col in all_fks:
                    schema.append(f"  {t}.{col} -> {ref_t}.{ref_col}")
            return '\n'.join(schema)
    finally:
        conn.close()
