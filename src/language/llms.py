import os
from litellm import completion

class LiteLLM_Wrapper:
    def __init__(self, model, **kwargs):
        self.model = model
        self.kwargs = kwargs

    def invoke(self, input_messages):
        # Convert input to litellm format
        messages = []
        if isinstance(input_messages, str):
            messages = [{"role": "user", "content": input_messages}]
        elif isinstance(input_messages, list):
            for msg in input_messages:
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    messages.append({"role": role, "content": content})
                elif isinstance(msg, tuple):
                    # LangChain format ("system", "text")
                    role = msg[0].replace("human", "user")
                    content = msg[1]
                    messages.append({"role": role, "content": content})
                else:
                    # fallback
                    messages.append({"role": "user", "content": str(msg)})
        
        response = completion(model=self.model, messages=messages, **self.kwargs)
        content = response.choices[0].message.content
        return type('Response', (object,), {'content': content})()

class LLM:
    def __init__(self, model_name : str, temperature : float, max_tokens : int, top_p : float, **kwargs):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
    
    def __repr__(self):
        return f'LLM(model = {self.model_name}, temperature = {self.temperature}, max token = {self.max_tokens}, top p = {self.top_p})'

class API_LLM(LLM):
    def __init__(self, model_name : str, temperature : float, max_tokens : int, top_p : float, **kwargs):
        super().__init__(model_name, temperature, max_tokens, top_p)

    def get_pipeline(self):
        # Use LiteLLM wrapper
        # Check keys presence (LiteLLM handles this, but good to warn)
        if "gemini" in self.model_name and "GOOGLE_API_KEY" not in os.environ:
             print("Warning: GOOGLE_API_KEY not found.")
        if "gpt" in self.model_name and "OPENAI_API_KEY" not in os.environ:
             print("Warning: OPENAI_API_KEY not found.")
             
        return LiteLLM_Wrapper(
            model=self.model_name, 
            temperature=self.temperature, 
            max_tokens=self.max_tokens, 
            top_p=self.top_p
        )
