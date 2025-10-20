import gradio as gr
from core.review_interface import ReviewBusinessLogic

class ReviewUI:
    def __init__(self, db, role):
        self.controller = ReviewBusinessLogic(db)
        self.annotation_options = self.controller.annotation_options
        self.visible = True
        self.role = role

    def create_interface(self, user_state: gr.State) -> gr.Blocks:
        with gr.Blocks(title="标注结果展示界面", theme=gr.themes.Soft()) as review_demo:
            task_id_input = gr.State()
            with gr.Row():
                # 左侧：任务列表和筛选
                with gr.Column(scale=1):
                    with gr.Row():
                        filter_status = gr.Dropdown(
                            choices=["annotated", "pending", "annotating", "all"],
                            value="annotated",
                            label="筛选状态"
                        )
                        search_task_id = gr.Textbox(label="按任务ID搜索", placeholder="输入完整的任务ID")
                    with gr.Row():
                        refresh_list_btn = gr.Button("🔄 刷新列表", variant="secondary")
                        search_btn = gr.Button("查找任务", variant="primary")

                    task_list = gr.Dataframe(
                        headers=["任务ID", "方法", "图像名", "状态", "标注人", "标注时间"],
                        datatype=["str", "str", "str", "str", "str", "str"],
                        interactive=False,
                        label="标注任务列表",
                        show_search="search",
                        show_copy_button=True
                    )

                    with gr.Row():
                        page_num = gr.Number(value=1, label="页码", precision=0)
                        page_size = gr.Dropdown(choices=["5", "10", "20", "50", "100", "1000"], value="10", label="每页数量")
                        total_pages = gr.Number(label="总页数", interactive=False)

                    with gr.Row():
                        prev_page_btn = gr.Button("上一页", variant="secondary")
                        next_page_btn = gr.Button("下一页", variant="primary")
                        jump_btn = gr.Button("跳转", variant="primary")

                    with gr.Tab("导出", visible=self.visible):
                        export_query = gr.Textbox(label="查询条件 (JSON)", placeholder='{"status": "annotated"}')
                        export_filename = gr.Textbox(label="导出文件名", value="exported_annotations.json")
                        export_btn = gr.Button("📤 导出", variant="primary")
                        export_status = gr.Textbox(label="导出状态", interactive=False)

                    with gr.Tab("导入", visible=self.visible):
                        import_file = gr.File(label="选择JSON文件", file_types=[".json"])
                        import_btn = gr.Button("📥 导入", variant="primary")
                        import_status = gr.Textbox(label="导入状态", interactive=False)

                # 右侧：任务详情和编辑
                with gr.Column(scale=2):
                    with gr.Row():
                        # task_id_input = gr.Textbox(label="当前任务ID", interactive=False)
                        status_msg = gr.Textbox(label="任务状态", interactive=False)

                    with gr.Row():
                        with gr.Column():
                            lq_image = gr.Image(label="低质量图像", interactive=False, height=400)
                        with gr.Column():
                            hq_image = gr.Image(label="修复图像", interactive=False, height=400)

                    selected_options = {}
                    angles = list(self.annotation_options.keys())
                    for i in range(0, len(angles), 2):
                        with gr.Row():
                            a1 = angles[i]
                            opts1 = self.annotation_options[a1]
                            slider1 = gr.Slider(minimum=opts1["minimum"], maximum=opts1["maximum"], step=opts1["step"], value=opts1["value"], label=opts1["Chinese"], info=opts1["description"])
                            selected_options[a1] = slider1
                            if i + 1 < len(angles):
                                a2 = angles[i + 1]
                                opts2 = self.annotation_options[a2]
                                slider2 = gr.Slider(minimum=opts2["minimum"], maximum=opts2["maximum"], step=opts2["step"], value=opts2["value"], label=opts2["Chinese"], info=opts2["description"])
                                selected_options[a2] = slider2

                    user_text = gr.Textbox(
                        label="评价文本",
                        lines=8,
                        max_lines=15,
                        interactive=True,
                        visible=self.visible
                    )

                    with gr.Row():
                        generate_btn = gr.Button("生成评价文本", variant="primary", visible=self.visible)
                        update_task_btn = gr.Button("💾 更新标注", variant="primary")
                    update_status = gr.Textbox(label="更新状态", interactive=False)

            # Event handlers
            def load_task_list(page=1, page_size=10, filter_status="annotated", user_state=None):
                return self.controller.load_task_list(int(page), int(page_size), filter_status, role=self.role, user_id=user_state)

            def jump_to_page(target_page, page_size, filter_status, user_state=None):
                target = int(target_page) if target_page else 1
                return load_task_list(target, page_size, filter_status, user_state=user_state)
            
            def load_selected_task(evt: gr.SelectData):
                row = evt.row_value
                if not row or len(row) < 1:
                    default_opts = [self.annotation_options[a]["value"] for a in self.annotation_options.keys()]
                    return [None, "无效任务"] + [None, None] + default_opts + ["", ""]
                task_id = row[0]
                result = self.controller.load_task_for_review(task_id)
                lq_img, hq_img, status, opts, txt, err = result
                opt_vals = [
                    opts.get(a, self.annotation_options[a]["value"]) 
                    for a in self.annotation_options.keys()
                ]
                return [task_id, status, lq_img, hq_img] + opt_vals + [txt, err or ""]

            def update_task(task_id, *args):
                selected = {a: args[i] for i, a in enumerate(self.annotation_options.keys())}
                user_txt = args[len(self.annotation_options)]
                return self.controller.update_task_in_db(task_id, selected, user_txt)

            def generate_text(*args):
                num = len(self.annotation_options)
                selected = {a: args[i] for i, a in enumerate(self.annotation_options.keys())}
                lq_img = args[num]
                hq_img = args[num + 1]
                return self.controller.generate_text_with_llm(selected, lq_img, hq_img)

            def handle_page_change(current_page, delta, page_size, filter_status, user_state=None):
                new_page = int(current_page) + int(delta)
                new_page = max(1, new_page)
                data, total, _ = load_task_list(new_page, page_size, filter_status, user_state=user_state)
                return data, total, new_page

            def search_task_by_id(task_id: str, user_state):
                if not task_id or not task_id.strip():
                    return [None, None, None, "请输入任务ID"] + [self.annotation_options[a]["value"] for a in self.annotation_options.keys()] + [""]
                
                task_id = task_id.strip()
                if self.role not in ['admin', 'super_admin']:
                    if not user_state:
                        return [None, None, None, "未登录"] + [self.annotation_options[a]["value"] for a in self.annotation_options.keys()] + [""]
                    task = self.controller.db.get_annotation_by_id(task_id)
                    if not task:
                        return [None, None, None, f"任务 {task_id} 不存在"] + [self.annotation_options[a]["value"] for a in self.annotation_options.keys()] + [""]
                    
                    task_user_id = task.get('last_updated_by')
                    if task_user_id != user_state:
                        return [None, None, None, f"无权访问任务 {task_id}"] + [self.annotation_options[a]["value"] for a in self.annotation_options.keys()] + [""]

                result = self.controller.load_task_for_review(task_id.strip())
                lq_img, hq_img, status_msg, opts, txt, err = result
                
                if err:
                    return [None, None, None, err] + [self.annotation_options[a]["value"] for a in self.annotation_options.keys()] + [""]
                
                opt_vals = [
                    opts.get(a, self.annotation_options[a]["value"]) 
                    for a in self.annotation_options.keys()
                ]
                return [task_id.strip(), lq_img, hq_img, status_msg] + opt_vals + [txt]

            def export_data(query_str, filename):
                return self.controller.export_data(query_str, filename)

            def import_data(file_obj):
                if not file_obj:
                    return "请选择文件"
                return self.controller.import_data(file_obj.name)

            # Bind events
            refresh_list_btn.click(
                load_task_list,
                inputs=[page_num, page_size, filter_status, user_state],
                outputs=[task_list, total_pages, page_num]
            )

            task_list.select(
                load_selected_task,
                outputs=[task_id_input, status_msg, lq_image, hq_image] +
                        [selected_options[a] for a in self.annotation_options.keys()] +
                        [user_text, update_status]
            )

            generate_btn.click(
                generate_text,
                inputs=[selected_options[a] for a in self.annotation_options.keys()] + [lq_image, hq_image],
                outputs=[user_text]
            )

            update_task_btn.click(
                update_task,
                inputs=[task_id_input] + [selected_options[a] for a in self.annotation_options.keys()] + [user_text],
                outputs=[update_status]
            )

            prev_page_btn.click(
                handle_page_change,
                inputs=[page_num, gr.Number(value=-1, visible=False), page_size, filter_status, user_state],
                outputs=[task_list, total_pages, page_num]
            )

            next_page_btn.click(
                handle_page_change,
                inputs=[page_num, gr.Number(value=1, visible=False), page_size, filter_status, user_state],
                outputs=[task_list, total_pages, page_num]
            )

            jump_btn.click(
                jump_to_page,
                inputs=[page_num, page_size, filter_status, user_state],
                outputs=[task_list, total_pages, page_num]
            )

            search_btn.click(
                search_task_by_id,
                inputs=[search_task_id, user_state],
                outputs=[task_id_input, lq_image, hq_image, status_msg] +
                    [selected_options[a] for a in self.annotation_options.keys()] +
                    [user_text]
            )

            export_btn.click(export_data, inputs=[export_query, export_filename], outputs=[export_status])
            import_btn.click(import_data, inputs=[import_file], outputs=[import_status])

            review_demo.load(load_task_list, inputs=[page_num, page_size, filter_status, user_state],
                             outputs=[task_list, total_pages, page_num])

        return review_demo