from app.db_external.schema import get_db_schema
from app.ai.chat import AIChat
from app.ai.sql_generator import SQLGenerator
from app.db_external.connection import get_external_connection
import os
import json
import logging

class ChatPipeline:

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        # Parse opcional do filtro de schema via ENV (JSON)
        self.tables_and_columns = None
        schema_filter = os.getenv("SCHEMA_FILTER_JSON")
        if schema_filter:
            try:
                self.tables_and_columns = json.loads(schema_filter)
            except Exception:
                self.tables_and_columns = None
        self.db_schema = get_db_schema(tables_and_columns=self.tables_and_columns)
        self.ai = AIChat(self.api_key, self.db_schema)

    def ask(self, question: str, history_msgs=None):
        clarification = None
        # 1. IA gera SQL
        sql_prompt = SQLGenerator.build_sql_prompt(question, self.db_schema)
        sql = self.ai.ask(sql_prompt, history=history_msgs)
        sql_clean = sql.replace('```sql', '').replace('```', '').strip()
        # 2. Executa SQL no banco externo
        try:
            conn = get_external_connection()
            with conn.cursor() as cursor:
                cursor.execute(sql_clean)
                result = cursor.fetchall()
        except Exception as e:
            logging.getLogger(__name__).exception("Falha ao executar SQL gerado")
            clarification = (
                "Sua pergunta não foi clara ou não foi possível gerar uma consulta válida. "
                "Você pode reformular ou dar mais detalhes?"
            )
            return clarification, sql_clean, None, clarification
        finally:
            try:
                conn.close()
            except:
                pass
        # 3. Se resultado vazio, tenta busca aproximada e mostra amostra dos dados
        if not result:
            # Tenta identificar a(s) tabela(s) do SQL
            import re
            tables = re.findall(r'from\s+([\w_]+)', sql_clean, re.IGNORECASE)
            if not tables:
                tables = re.findall(r'join\s+([\w_]+)', sql_clean, re.IGNORECASE)
            sample_data = {}
            for table in set(tables):
                try:
                    conn = get_external_connection()
                    with conn.cursor() as cursor:
                        cursor.execute(f"SELECT * FROM {table} LIMIT 10")
                        sample_data[table] = cursor.fetchall()
                except Exception:
                    sample_data[table] = []
                finally:
                    try:
                        conn.close()
                    except:
                        pass
            # Prompt para IA tentar nova consulta baseada nos dados reais
            fuzzy_prompt = (
                f"A consulta SQL abaixo não retornou resultados:\n{sql_clean}\n"
                f"Aqui estão exemplos reais de dados das tabelas envolvidas: {sample_data}\n"
                "Gere um novo SQL para buscar por aproximação (usando LIKE, %palavra%, ou funções de similaridade) "
                "ou adapte a consulta para tentar encontrar registros relacionados à pergunta. Não explique, apenas gere o SQL puro."
            )
            fuzzy_sql = self.ai.ask(fuzzy_prompt, history=history_msgs)
            fuzzy_sql_clean = fuzzy_sql.replace('```sql', '').replace('```', '').strip()
            try:
                conn = get_external_connection()
                with conn.cursor() as cursor:
                    cursor.execute(fuzzy_sql_clean)
                    fuzzy_result = cursor.fetchall()
            except Exception as e:
                logging.getLogger(__name__).exception("Falha ao executar SQL de busca aproximada")
                clarification = (
                    "Nenhum resultado encontrado e não foi possível realizar uma busca por aproximação no momento."
                )
                return clarification, fuzzy_sql_clean, None, clarification
            finally:
                try:
                    conn.close()
                except:
                    pass
            # IA responde baseado no resultado fuzzy
            answer = self.ai.answer(question, fuzzy_result)
            return answer, fuzzy_sql_clean, fuzzy_result, clarification
        # 4. IA responde baseado no resultado do SQL original
        answer = self.ai.answer(question, result)
        return answer, sql_clean, result, clarification