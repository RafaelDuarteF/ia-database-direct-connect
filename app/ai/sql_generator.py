class SQLGenerator:
    @staticmethod
    def build_sql_prompt(question: str, db_schema: str) -> str:
        return f"""
Abaixo está a estrutura do banco de dados:
{db_schema}

Pergunta do usuário: {question}

Gere apenas um único SQL SELECT, sem explicações, obedecendo às regras:
- Use somente colunas/tabelas/relacionamentos presentes no schema e exemplos acima.
- Não use LIMIT dentro de subqueries em IN/ALL/ANY/SOME; se precisar limitar, reescreva com JOIN/CTE ou limite na query externa.
- Em subqueries que podem retornar múltiplos valores, use IN ao invés de '='.
- Evite funções ou features não suportadas pela versão MySQL padrão.
- Para ordenações customizadas (ex.: maior prioridade), use FIELD(...) ou CASE respeitando os valores reais.
- Se precisar identificar registros por nome informado na pergunta, filtre por LIKE '%valor%'.
- Não inclua markdown (```), nem comentários; retorne apenas o SQL executável.
"""
