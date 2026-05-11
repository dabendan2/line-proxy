import os
from google import genai

from config import DEFAULT_MODEL

class TaskRefactorer:
    def __init__(self, api_key=None, model_name=DEFAULT_MODEL):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        prompt_path = os.path.join(os.path.dirname(__file__), "task_refactor_prompt.md")
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt_template = f.read()

    def refactor(self, task_description):
        prompt = self.system_prompt_template.replace("{{task}}", task_description)
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            # Fallback to original if refactoring fails
            print(f"Refactor failed: {e}")
            return task_description
