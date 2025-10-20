import argparse
from database import Database
from interfaces.login_ui import LoginUI
from interfaces.annotation_ui import AnnotationUI
from interfaces.review_ui import ReviewUI
from interfaces.helper_ui import HelperUI

import gradio as gr

def parse_args():
    parser = argparse.ArgumentParser(description="Image Quality Annotation")
    parser.add_argument('--server_name', type=str, default='0.0.0.0')
    parser.add_argument('--server_port', type=int, default=8866)
    parser.add_argument('--mongodb_uri', type=str, default='mongodb://localhost:27017/')
    parser.add_argument('--db_name', type=str, default='annotation')
    parser.add_argument('--collection_name', type=str, default='annotations')
    parser.add_argument('--role', type=str, default='user')
    args = parser.parse_args()

    return args


def main(args):
    # 初始化
    db = Database(mongodb_uri=args.mongodb_uri, db_name=args.db_name, collection_name=args.collection_name)

    # 创建各 UI
    login_ui = LoginUI(db)
    annotation_ui = AnnotationUI(db, args.role)
    review_ui = ReviewUI(db, args.role)
    help_ui = HelperUI()

    # 合并 Tabs
    with gr.Blocks(title="图像质量标注系统") as app:
        gr.Markdown("# 图像质量标注系统")
        user_state = gr.State(None)
        with gr.Tab("用户登录"):
            login_ui.create_interface(user_state)
        with gr.Tab("标注界面"):
            annotation_ui.create_interface(user_state)
        with gr.Tab("评分标准"):
            help_ui.create_interface()
        with gr.Tab("标注结果展示"):
            review_ui.create_interface(user_state)

    app.launch(
        server_name=args.server_name,
        server_port=args.server_port,
        debug=True,
        show_error=True,
    )

if __name__ == "__main__":
    args = parse_args()
    main(args)