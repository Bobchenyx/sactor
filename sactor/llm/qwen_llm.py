try:
    from typing import override
except ImportError:
    # Python < 3.12 compatibility
    def override(func):
        return func

try:
    from .openai_llm import OpenAILLM
except ImportError:
    # 独立运行时的导入
    from openai_llm import OpenAILLM


class QwenLLM(OpenAILLM):
    '''
    Qwen LLM - 通义千问API
    
    使用OpenAI兼容的API接口
    '''

    def __init__(self, config, encoding=None, system_msg=None):
        super().__init__(
            config,
            encoding=encoding,
            system_msg=system_msg,
            config_key="Qwen"
        )

    @override
    def _query_impl_inner(self, prompt, model):
        if model is None:
            model = self.config[self.config_key]['model']
        
        messages = []
        # Qwen API只支持 user 和 assistant role，不支持 system
        # 将system message合并到user prompt中
        if self.system_msg is not None:
            # 将system message作为user prompt的前缀
            full_prompt = f"{self.system_msg}\n\n{prompt}"
            messages.append({"role": "user", "content": full_prompt})
        else:
            messages.append({"role": "user", "content": f"{prompt}"})

        temperature = self.config[self.config_key].get('temperature') # default is 1 if not set
        max_tokens = self.config[self.config_key].get('max_tokens')
        max_completion_tokens = self.config[self.config_key].get('max_completion_tokens')

        # Qwen模型参数处理
        # 不设置 enable_thinking 参数，让 API 使用默认值
        # 避免不同模型的参数兼容性问题
        extra_body = {}
        
        if max_completion_tokens is not None:
            # 优先使用max_completion_tokens
            resp = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_completion_tokens=max_completion_tokens,
                extra_body=extra_body,
            )
        else:
            # 使用max_tokens作为备用
            resp = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                extra_body=extra_body,
            )

        return resp

    @override
    def _query_impl(self, prompt, model) -> str:
        resp = self._query_impl_inner(prompt, model)

        if resp.choices[0].message.content is None:
            raise Exception(f"Failed to generate response: {resp}")
        return resp.choices[0].message.content
