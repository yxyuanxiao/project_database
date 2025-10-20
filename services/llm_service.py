import os
import base64
import tempfile
from PIL import Image
from openai import OpenAI
from typing import List, Optional, Union, Tuple

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        b64 = base64.b64encode(image_file.read()).decode("utf-8")
    ext = os.path.splitext(image_path)[1].lower()
    mime_type = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp'
    }.get(ext, 'image/webp')
    return f"data:{mime_type};base64,{b64}"

class LLMClient:
    def __init__(self, model: str):
        self.model = model
        self.client = OpenAI(
            api_key="",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    
    def _prepare_messages(
        self,
        prompt: str,
        imgs_path: Optional[List[str]],
        sys_msgs: Optional[Union[str, List[str]]]
    ) -> List[dict]:
        if isinstance(sys_msgs, str):
            sys_msgs = [sys_msgs]
        if sys_msgs is None:
            sys_msgs_content = [{"role": "system", "content": [{"type": "text", "text": "You are a professional expert in image quality assessment"}]}]
        else:
            sys_msgs_content = [{"role": "system", "content": [{"type": "text", "text": s}]} for s in sys_msgs]

        image_msgs = []
        if imgs_path:
            image_msgs = [{"type": "image_url", "image_url": {"url": encode_image(path)}} for path in imgs_path]

        user_msg = {'role': 'user', 'content': [{'type': 'text', 'text': prompt}] + image_msgs}
        return sys_msgs_content + [user_msg]
    
    def get_response(
        self,
        prompt: str,
        imgs_path: Optional[List[str]] = None,
        sys_msgs: Optional[Union[str, List[str]]] = None,
    ) -> Tuple[str, List[dict], Optional[dict]]:
        msg = self._prepare_messages(prompt, imgs_path, sys_msgs)

        try:
            completion = self.client.chat.completions.create(model=self.model, messages=msg)
            resp = completion.choices[3].message
            
            content = resp.content or "No content available"
            return content
        except Exception as e:
            return f"Error: {e}"

def generate_text(selected_options, lq_image, hq_image, tag):
        temp_paths = []
        try:
            if lq_image is None or hq_image is None:
                return "图像数据为空，无法生成评价"

            temp_dir = os.environ.get('GRADIO_TEMP_DIR', tempfile.gettempdir())
            with tempfile.NamedTemporaryFile(dir=temp_dir, suffix=".png", delete=False) as f:
                lq_path = f.name
            with tempfile.NamedTemporaryFile(dir=temp_dir, suffix=".png", delete=False) as f:
                hq_path = f.name

            Image.fromarray(lq_image.astype('uint8')).save(lq_path)
            Image.fromarray(hq_image.astype('uint8')).save(hq_path)
            temp_paths = [lq_path, hq_path]

            sys_prompt = ""
            rating_text = "; ".join(f"{k}: {v}" for k, v in selected_options.items())
            user_prompt = f"""
                """
            
            return "Empty"
            # response = Qwen3.get_response(
            #     prompt=user_prompt,
            #     imgs_path=[lq_path, hq_path],
            #     sys_msgs=sys_prompt
            # )
            # return response if not (isinstance(response, str) and response.startswith("Error:")) else f"AI生成评价失败: {response}"
        except Exception as e:
            return f"生成文本时出错: {str(e)}"
        finally:
            for p in temp_paths:
                if os.path.exists(p):
                    os.remove(p)