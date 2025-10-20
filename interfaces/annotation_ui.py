import gradio as gr
from core.annotation_interface import AnnotationBusinessLogic

class AnnotationUI:
    def __init__(self, db, role):
        self.controller = AnnotationBusinessLogic(db)
        self.annotation_options = self.controller.annotation_options
        self.visible = True

    def create_interface(self, user_state: gr.State) -> gr.Blocks:
        with gr.Blocks(title="图像质量标注系统", theme=gr.themes.Soft()) as demo:

            with gr.Row():
                # 左半部分:图像显示
                with gr.Column(scale=4):
                    user_info = gr.Textbox(label="当前用户", interactive=False)
                    with gr.Row():
                        with gr.Column():
                            lq_image = gr.Image(label="低质量图像", interactive=False, height=400)
                        with gr.Column():
                            hq_image = gr.Image(label="修复图像", interactive=False, height=400)
                    status = gr.Textbox(label="任务状态", interactive=False)
                    with gr.Row():
                        prev_btn = gr.Button("⬅️ 上一张", variant="secondary")
                        next_btn = gr.Button("下一张 ➡️", variant="primary")
                        cancel_btn = gr.Button("❌ 取消当前任务", variant="stop")
                        stats_btn = gr.Button("📊 查看统计")
                    stats_output = gr.Textbox(label="标注统计", interactive=False, lines=6)

                # 右半部分:标注和文本
                with gr.Column(scale=3):
                    selected_options = {}
                    angles = list(self.annotation_options.keys())
                    for i in range(0, len(angles), 2):
                        with gr.Row():
                            a1 = angles[i]
                            opts1 = self.annotation_options[a1]
                            slider1 = gr.Slider(minimum=opts1["minimum"], maximum=opts1["maximum"], step=opts1["step"], value=opts1["value"], label=opts1["name"], info=opts1["description"])
                            selected_options[a1] = slider1
                            if i + 1 < len(angles):
                                a2 = angles[i + 1]
                                opts2 = self.annotation_options[a2]
                                slider2 = gr.Slider(minimum=opts2["minimum"], maximum=opts2["maximum"], step=opts2["step"], value=opts2["value"], label=opts2["name"], info=opts2["description"])
                                selected_options[a2] = slider2

                    user_text = gr.Textbox(
                        label="评价文本",
                        lines=10,
                        max_lines=15,
                        placeholder="AI生成的评价文本将显示在此处,用户可在此进行编辑...",
                        interactive=True,
                        visible=self.visible
                    )
                    with gr.Row():
                        generate_btn = gr.Button("生成评价文本", variant="primary", visible=self.visible)
                        clear_text_btn = gr.Button("清空文本", variant="secondary", visible=self.visible)
                    with gr.Row():
                        save_btn = gr.Button("💾 保存标注", variant="primary", size="lg")
                        save_status = gr.Textbox(label="保存状态", interactive=False)

            current_task_id_state = gr.State(None)

            # Helper functions
            def update_user_info(user_id):
                return self.controller.get_user_display_info(user_id)

            def load_previous(user_id):
                result = self.controller.load_previous_task(user_id)
                task_id = result.get('status', '').split(' ')[1] if '当前任务:' in result['status'] else None
                return (
                    update_user_info(user_id),
                    result['lq_image'], result['hq_image'], result['status'],
                    *[result['selected_options'].get(a, self.annotation_options[a]["value"]) for a in self.annotation_options.keys()],
                    result['user_text'],
                    "",
                    task_id
                )

            def load_next(user_id):
                result = self.controller.load_next_task(user_id)
                new_task_id = result.get('status', '').split(' ')[1] if '当前任务:' in result['status'] else None
                return (
                    update_user_info(user_id),
                    result['lq_image'], result['hq_image'], result['status'],
                    *[result['selected_options'].get(a, self.annotation_options[a]["value"]) for a in self.annotation_options.keys()],
                    result['user_text'],
                    "",
                    new_task_id
                )
            
            def cancel_task(user_id, task_id):
                if not task_id:
                    return update_user_info(user_id), "无任务可取消", None
                msg = self.controller.cancel_current_task(user_id, task_id)
                return update_user_info(user_id), msg, None
            
            def generate_text(task_id, *args):
                tag = self.controller.get_tag(task_id)
                num_angles = len(self.annotation_options)
    
                selected_options = {}
                for i, angle in enumerate(self.annotation_options.keys()):
                    selected_options[angle] = args[i]

                lq_image_input = args[num_angles]
                hq_image_input = args[num_angles + 1]
                
                result = self.controller.generate_text_with_llm(
                    selected_options, lq_image_input, hq_image_input, tag
                )
                return result
            
            def save_anno(user_id, task_id, *args):
                if not user_id or not task_id:
                    return "请先登录并加载任务"
                selected_options = {}
                for i, angle in enumerate(self.annotation_options.keys()):
                    selected_options[angle] = args[i]

                user_text = args[len(self.annotation_options)] if len(args) > len(self.annotation_options) else ""
                
                result = self.controller.save_annotations(user_id, task_id, selected_options, user_text)
                return result
            
            def get_stats():
                stats = self.controller.get_annotation_statistics()
                stats_text = f"""
                标注统计:
                - 待标注: {stats.get('pending', 0)}
                - 标注中: {stats.get('annotating', 0)}
                - 已标注: {stats.get('annotated', 0)}
                - 总计: {stats.get('total', 0)}
                """
                return stats_text

            def clear_text():
                return ""

            demo.load(update_user_info, inputs=user_state, outputs=user_info)

            next_btn.click(
                load_next,
                inputs=[user_state],
                outputs=[user_info, lq_image, hq_image, status] + 
                    [selected_options[angle] for angle in self.annotation_options.keys()] + 
                    [user_text, save_status, current_task_id_state]
            )
            
            prev_btn.click(
                load_previous,
                inputs=user_state,
                outputs=[user_info, lq_image, hq_image, status] + 
                    [selected_options[angle] for angle in self.annotation_options.keys()] + 
                    [user_text, save_status, current_task_id_state]
            )

            cancel_btn.click(
                cancel_task,
                inputs=[user_state, current_task_id_state],
                outputs=[user_info, status, current_task_id_state]
            )

            generate_btn.click(
                generate_text,
                inputs=[current_task_id_state] + [selected_options[a] for a in self.annotation_options.keys()] + [lq_image, hq_image],
                outputs=[user_text]
            )

            clear_text_btn.click(clear_text, outputs=[user_text])

            save_btn.click(
                save_anno,
                inputs=[user_state, current_task_id_state] + [selected_options[a] for a in self.annotation_options.keys()] + [user_text],
                outputs=[save_status]
            )

            stats_btn.click(get_stats, outputs=[stats_output])

        return demo