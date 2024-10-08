# -*- coding: utf-8 -*-
'''
@File    :   dialogueAgnet.py
@Author  :   一力辉 
'''

from ..builder import AGENTS
from ..agentBase import BaseAgent
import re
import json
import httpx
import requests
from typing import List, Optional, Union
from digitalHuman.utils import logger
from digitalHuman.utils import AudioMessage, TextMessage
from digitalHuman.engine.engineBase import BaseEngine

__all__ = ["DifyAgent"]


@AGENTS.register("DifyAgent")
class DifyAgent(BaseAgent):

    def checkKeys(self) -> List[str]:
        return []
    
    def setup(self):
        pass

    async def run(
        self, 
        input: Union[TextMessage, AudioMessage], 
        streaming: bool,
        url: str,
        key: str,
        **kwargs
    ):
        try:
            if isinstance(input, AudioMessage):
                raise RuntimeError("RepeaterAgent does not support AudioMessage input")
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {key}'
            }
            responseMode = "streaming" if streaming else "blocking"
            payload = {
                "inputs": {},
                "query": input.data,
                "response_mode": responseMode,
                "user": "adh",
                "files":[]
            }

            pattern = re.compile(r'data:\s*({.*})')
            client = httpx.AsyncClient(headers=headers)
            if streaming:
                async with client.stream('POST', url + "/chat-messages", headers=headers, json=payload) as response:
                    async for chunk in response.aiter_bytes():
                        chunkStr = chunk.decode('utf-8').strip()
                        chunkData = pattern.search(chunkStr)
                        # 部分dify返回不完整，该模板匹配会失效
                        if not chunkData: 
                            logger.warning(f"[AGENT] Engine return truncated data: {chunkData}")
                            continue
                        chunkData = chunkData.group(1)

                        try:
                            data = json.loads(chunkData)
                            # 处理流式返回字符串
                            if "message" in data["event"]:
                                if 'answer' in data: yield bytes(data['answer'], encoding='utf-8')
                        except Exception as e:
                            logger.error(f"[AGENT] Engine run failed: {e}")
                            yield bytes("内部错误，请检查dify信息。", encoding='utf-8')

            else:
                response = await client.post(url + "/chat-messages", headers=headers, json=payload)
                data = json.loads(response.text)
                yield bytes(data['answer'], encoding='utf-8')
        except Exception as e:
            logger.error(f"[AGENT] Engine run failed: {e}")
            yield bytes("内部错误，请检查dify信息。", encoding='utf-8')