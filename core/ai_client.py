import os
import logging
import requests

AI_URL = os.getenv("IQAC_AI_URL", "http://127.0.0.1:8699")

logger = logging.getLogger(__name__)

class AIClient:
    def __init__(self, base: str = AI_URL, timeout: int = 25):
        self.base = base.rstrip("/")
        self.timeout = timeout

    def _post(self, path: str, payload: dict):
        url = f"{self.base}{path}"
        logger.debug("POST %s payload=%s", url, payload)
        resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def need_analysis(self, ctx: dict):
        return self._post("/generate/need_analysis", ctx)

    def objectives(self, ctx: dict):
        return self._post("/generate/objectives", ctx)

    def outcomes(self, ctx: dict):
        return self._post("/generate/outcomes", ctx)

    def report(self, ctx: dict):
        return self._post("/generate/report", ctx)
