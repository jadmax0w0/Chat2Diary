from volcenginesdkarkruntime import Ark


class LLM():
    def __init__(self):
        self.prompts_history: list[dict] = []
    
    def llm_init(self, apikey: str, **kwargs):
        raise NotImplementedError()
    
    def llm_close(self):
        raise NotImplementedError()
    
    def llm_prompt(self, chat_messages: str, system_prompt: str, streaming = False) -> str:
        raise NotImplementedError()
    
    def _append_new_prompts(self, chat_messages: str, system_prompt: str) -> list[dict]:
        prompts_new = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': chat_messages},
        ]
        self.prompts_history.extend(prompts_new)
        return prompts_new


class DoubaoLLM(LLM):
    def __init__(self):
        super().__init__()
        self.client: Ark = None
        self.modelid: str = None

    def llm_init(self, apikey: str, **kwargs):
        if "modelid" in kwargs:
            self.modelid = kwargs["modelid"]
        assert self.modelid is not None
        self.client = Ark(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=apikey,
        )

    def llm_close(self):
        if self.client.is_closed() == False:
            self.client.close()

    def llm_prompt(self, chat_messages: str, system_prompt: str, streaming = False) -> str:
        assert self.client is not None
        assert self.modelid is not None
        prompts_new = self._append_new_prompts(chat_messages, system_prompt)
        if streaming:
            prompts_new = [d.copy() for d in self.prompts_history]
        completion = self.client.chat.completions.create(
            model=self.modelid,
            messages=prompts_new,
            extra_headers={'x-is-encrypted': 'true'},
        )
        return completion.choices[0].message.content