# config.py
import os
os.environ['GRADIO_TEMP_DIR'] = './gradio_tmp'

# LLM 模型配置
LLM_MODEL_NAME = "qwen3-vl-plus"

OPTIONS = {
    "Dimension 1": {
        "minimum": 0,
        "maximum": 5,
        "step": 1,
        "value": 0,
        "description": "0: Bad, 5:Great",
        "na me": "Dimension 1"
        },
    "Dimension 2": {
        "minimum": 0,
        "maximum": 5,
        "step": 1,
        "value": 0,
        "description": "0: Bad, 5:Great",
        "name": "Dimension 2"
        },
    "Dimension 3": {
        "minimum": 0,
        "maximum": 5,
        "step": 1,
        "value": 0,
        "description": "0: Bad, 5:Great",
        "name": "Dimension 3"
        },
    "Dimension 4": {
        "minimum": 0,
        "maximum": 5,
        "step": 1,
        "value": 0,
        "description": "0: Bad, 5:Great",
        "name": "Dimension 4"
        },
    "Dimension 5": {
        "minimum": 0,
        "maximum": 5,
        "step": 1,
        "value": 0,
        "description": "0: Bad, 5:Great",
        "name": "Dimension 5"
        },
    "Dimension 6": {
        "minimum": 0,
        "maximum": 5,
        "step": 1,
        "value": 0,
        "description": "0: Bad, 5:Great",
        "name": "Dimension 1"
        },
    "Dimension 7": {
        "minimum": 0,
        "maximum": 5,
        "step": 1,
        "value": 0,
        "description": "0: Bad, 5:Great",
        "name": "Dimension 7"
        },
    "Total score": {
        "minimum": 0,
        "maximum": 5,
        "step": 1,
        "value": 0,
        "description": "0: Bad, 4: Great",
        "name":  "Total score"
        }
    }