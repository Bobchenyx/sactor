from typing import override

from openai import AzureOpenAI

from .llm import LLM


class AzureOpenAILLM(LLM):
    '''
    Azure OpenAI LLM

    '''
    def __init__(self, config, encoding=None, system_msg=None):
        super().__init__(
            config,
            encoding=encoding,
            system_msg=system_msg
        )
        api_key = config['AzureOpenAI']['api_key']
        endpoint = config['AzureOpenAI']['endpoint']
        api_version = config['AzureOpenAI']['api_version']

        self.client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint,
        )

    @override
    def _query_impl(self, prompt, model) -> str:
        if model is None:
            model = self.config['AzureOpenAI']['model']

        messages = []
        if self.system_msg is not None:
            messages.append({"role": "system", "content": self.system_msg})
        messages.append({"role": "user", "content": f"{prompt}"})

        temperature =  self.config['AzureOpenAI'].get('temperature') # default is 1 if not set
        max_tokens = self.config['AzureOpenAI'].get('max_tokens')
        max_completion_tokens = self.config['AzureOpenAI'].get('max_completion_tokens')

        # GPT-5 使用 max_completion_tokens 而不是 max_tokens，并且需要处理temperature
        if model.startswith('gpt-5'):
            # GPT-5 只支持默认temperature (1)，不能为null
            if temperature is None:
                temperature = 1
                
            if max_completion_tokens is not None:
                resp = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_completion_tokens=max_completion_tokens,
                )
            else:
                resp = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_completion_tokens=max_tokens,
                )
        else:
            resp = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        if resp.choices[0].message.content is None:
            raise Exception(f"Failed to generate response: {resp}")
        return resp.choices[0].message.content
