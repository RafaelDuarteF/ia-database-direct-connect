import os
from sqlalchemy import create_engine

def get_external_connection():
    type_db = os.getenv("TYPE_DB", "mysql").lower()
    if type_db == "mysql":
        return get_mysql_connection()
    
    if type_db == "postgresql":
        return get_postgresql_connection()
    
    if type_db == "oracle":
        return get_oracle_connection()  
    
    if type_db == "sqlserver":
        return get_sqlserver_connection()
    
    
def get_mysql_connection():
    import pymysql
    return pymysql.connect(
        host=os.getenv("EXT_MYSQL_HOST"),
        user=os.getenv("EXT_MYSQL_USER"),
        password=os.getenv("EXT_MYSQL_PASSWORD"),
        database=os.getenv("EXT_MYSQL_DB"),
        port=int(os.getenv("EXT_MYSQL_PORT", 3306)),
        cursorclass=pymysql.cursors.DictCursor
    )

def get_postgresql_connection():
    import psycopg2
    return psycopg2.connect(
        host=os.getenv("EXT_PG_HOST"),
        user=os.getenv("EXT_PG_USER"),
        password=os.getenv("EXT_PG_PASSWORD"),
        dbname=os.getenv("EXT_PG_DB"),
        port=int(os.getenv("EXT_PG_PORT", 5432))
    )

def get_oracle_connection():
    import oracledb
    # oracledb thin mode não precisa de Instant Client
    user = os.getenv("EXT_ORACLE_USER")
    password = os.getenv("EXT_ORACLE_PASSWORD")
    host = os.getenv("EXT_ORACLE_HOST")
    port = int(os.getenv("EXT_ORACLE_PORT", 1521))
    service = os.getenv("EXT_ORACLE_SERVICE")
    dsn = oracledb.makedsn(host, port, service_name=service)
    return oracledb.connect(user=user, password=password, dsn=dsn)

def get_sqlserver_connection():
    import pyodbc
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={os.getenv('EXT_MSSQL_HOST')},{os.getenv('EXT_MSSQL_PORT', 1433)};"
        f"DATABASE={os.getenv('EXT_MSSQL_DB')};"
        f"UID={os.getenv('EXT_MSSQL_USER')};"
        f"PWD={os.getenv('EXT_MSSQL_PASSWORD')}"
    )
    return pyodbc.connect(conn_str)

def get_sqlalchemy_engine():
    """Cria um SQLAlchemy Engine baseado nas mesmas variáveis de ambiente do get_external_connection."""
    type_db = os.getenv("TYPE_DB", "mysql").lower()
    if type_db == "mysql":
        import pymysql  # ensure driver installed
        user = os.getenv("EXT_MYSQL_USER")
        pwd = os.getenv("EXT_MYSQL_PASSWORD")
        host = os.getenv("EXT_MYSQL_HOST")
        port = int(os.getenv("EXT_MYSQL_PORT", 3306))
        db = os.getenv("EXT_MYSQL_DB")
        url = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}"
        return create_engine(
            url,
            connect_args={"connect_timeout": 5},
            pool_pre_ping=True,
        )
    if type_db == "postgresql":
        import psycopg2  # ensure driver installed
        user = os.getenv("EXT_PG_USER")
        pwd = os.getenv("EXT_PG_PASSWORD")
        host = os.getenv("EXT_PG_HOST")
        port = int(os.getenv("EXT_PG_PORT", 5432))
        db = os.getenv("EXT_PG_DB")
        # connect_timeout funciona passado no DSN
        url = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}?connect_timeout=5"
        return create_engine(url, pool_pre_ping=True)
    if type_db == "oracle":
        import oracledb  # ensure driver installed
        user = os.getenv("EXT_ORACLE_USER")
        pwd = os.getenv("EXT_ORACLE_PASSWORD")
        host = os.getenv("EXT_ORACLE_HOST")
        port = int(os.getenv("EXT_ORACLE_PORT", 1521))
        service = os.getenv("EXT_ORACLE_SERVICE")
        # SQLAlchemy usa 'oracle+oracledb' para o driver novo
        url = f"oracle+oracledb://{user}:{pwd}@{host}:{port}/?service_name={service}"
        return create_engine(url, connect_args={"timeout": 5}, pool_pre_ping=True)
    if type_db == "sqlserver":
        import pyodbc  # ensure driver installed
        user = os.getenv("EXT_MSSQL_USER")
        pwd = os.getenv("EXT_MSSQL_PASSWORD")
        host = os.getenv("EXT_MSSQL_HOST")
        port = int(os.getenv("EXT_MSSQL_PORT", 1433))
        db = os.getenv("EXT_MSSQL_DB")
        driver = os.getenv("EXT_MSSQL_DRIVER", "ODBC Driver 17 for SQL Server").replace(" ", "+")
        # Connection Timeout (segundos) via ODBC
        params = f"driver={driver}&TrustServerCertificate=yes&Connection+Timeout=5"
        url = f"mssql+pyodbc://{user}:{pwd}@{host}:{port}/{db}?{params}"
        return create_engine(url, pool_pre_ping=True)
    raise ValueError(f"Banco não suportado: {type_db}")