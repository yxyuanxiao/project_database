import gradio as gr

markdown_content = """
# 评分标准说明

"""


class HelperUI:
    def create_interface(self):
        with gr.Blocks(title="图像质量标注系统", theme=gr.themes.Soft()) as demo:
            gr.Markdown(markdown_content)
        return demo