import logging

from langchain_community.llms import Ollama

from .bam_client import BAMClient

logger = logging.getLogger(__name__)


# NOTE Heavily inspired by bam_client.py and we should ultimately merge the
# two drivers to create a generic one.
class OllamaClient(BAMClient):
    def __init__(self, inference_url):
        super().__init__(inference_url=inference_url)
        self._prediction_url = self._inference_url

    def get_chat_model(self, model_id):
        return Ollama(
            # base_url=self._prediction_url,
            base_url="http://192.168.1.191:11434",
            model=model_id,
        )
