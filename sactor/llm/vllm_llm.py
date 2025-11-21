try:
    from typing import override
except ImportError:
    # Python < 3.12 compatibility
    def override(func):
        return func

from openai import OpenAI

from .llm import LLM


class VLLMLLM(LLM):
    '''
    vLLM Language Model Wrapper
    
    vLLM 提供 OpenAI 兼容的 API 接口，默认运行在 http://localhost:8000/v1
    使用方式：
    1. 启动 vLLM 服务：
       python -m vllm.entrypoints.openai.api_server \
         --model Qwen/Qwen2.5-1.5B-Instruct \
         --port 8000
    2. 配置 sactor.toml：
       [general]
       llm = "VLLM"
       
       [VLLM]
       base_url = "http://localhost:8000/v1"
       api_key = "EMPTY"  # vLLM 不需要真实的 API key
       model = "Qwen/Qwen2.5-1.5B-Instruct"
       max_tokens = 8192
    '''

    def __init__(self, config, encoding=None, system_msg=None):
        super().__init__(
            config,
            encoding=encoding,
            system_msg=system_msg
        )
        
        # vLLM 配置
        base_url = config['VLLM'].get('base_url', 'http://localhost:8000/v1')
        api_key = config['VLLM'].get('api_key', 'EMPTY')  # vLLM 通常不需要真实的 API key
        
        # Optional
        organization = config['VLLM'].get('organization')
        project_id = config['VLLM'].get('project_id')

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            organization=organization,
            project=project_id
        )
        self.config_key = 'VLLM'

    @override
    def _query_impl(self, prompt, model) -> str:
        if model is None:
            model = self.config[self.config_key]['model']

        messages = []
        if self.system_msg is not None:
            messages.append({"role": "system", "content": self.system_msg})
        messages.append({"role": "user", "content": f"{prompt}"})

        temperature = self.config[self.config_key].get('temperature', 0.7)
        max_tokens = self.config[self.config_key].get('max_tokens', 8192)

        resp = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if resp.choices[0].message.content is None:
            raise Exception(f"Failed to generate response: {resp}")
        return resp.choices[0].message.content

