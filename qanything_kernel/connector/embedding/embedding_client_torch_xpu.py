import numpy as np
import time
from qanything_kernel.utils.custom_log import debug_logger
from .base import EmbeddingBase
from transformers import AutoTokenizer
from bigdl.llm.transformers import AutoModel
import os
import intel_extension_for_pytorch as ipex
import torch


class EmbeddingClientTorchXPU(EmbeddingBase):

    def __init__(self):
        super().__init__()
        self.max_batchsz: int = 8
        self._get_model()

    def _get_model(self) -> None:
        current_script_path = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(current_script_path + '/embedding_torch_models', exist_ok=True)
        self._tokenizer = AutoTokenizer.from_pretrained('maidalun1020/bce-embedding-base_v1',
                                                        cache_dir=current_script_path + '/embedding_torch_models')
        self._model = AutoModel.from_pretrained('maidalun1020/bce-embedding-base_v1',
                                                cache_dir=current_script_path + '/embedding_torch_models',
                                                load_in_low_bit='fp16', use_cache=True, torch_dtype=torch.float16)
        self._model = self._model.to('xpu')

    def get_embedding(self, sentences, max_length=512):
        inputs_pt = self._tokenizer(sentences, padding=True, truncation=True, max_length=max_length,
                                    return_tensors='pt')
        inputs_pt = {k: v.to('xpu') for k, v in inputs_pt.items()}
        print(inputs_pt['input_ids'].shape)
        print(inputs_pt['attention_mask'].shape)
        start_time = time.time()
        torch.xpu.synchronize()
        outputs_pt = self._model(**inputs_pt, return_dict=False)
        torch.xpu.synchronize()
        debug_logger.info(f"embedding infer time: {time.time() - start_time}")
        embedding = outputs_pt[0][:, 0].cpu().detach().numpy()
        print(embedding.dtype)
        debug_logger.info(f'embedding shape: {embedding.shape}')
        norm_arr = np.linalg.norm(embedding, axis=1, keepdims=True)
        embeddings_normalized = embedding / norm_arr

        return embeddings_normalized.tolist()

    # def getModelVersion(self):
    #     return self.embed_version