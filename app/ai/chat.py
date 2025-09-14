import openai
import os
from app.utils.prompt import build_initial_prompt, build_answer_prompt

class AIChat:
    def __init__(self, api_key: str, db_schema: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.initial_prompt = build_initial_prompt(db_schema)
        self.answer_system = build_answer_prompt()

    def ask(self, question: str, history=None):
        messages = [{"role": "system", "content": self.initial_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": question})
        response = self.client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            # temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.2")),
            messages=messages
        )
        return response.choices[0].message.content

    def answer(self, question: str, result_obj) -> str:
        messages = [{"role": "system", "content": self.answer_system}]
        # Passa o resultado como texto compacto
        content = (
            f"Pergunta: {question}\n" 
            f"Resultado: {result_obj}"
        )
        messages.append({"role": "user", "content": content})
        response = self.client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            # temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.2")),
            messages=messages
        )
        return response.choices[0].message.content
