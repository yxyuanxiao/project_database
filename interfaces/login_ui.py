import gradio as gr
from database import Database


class LoginUI:
    def __init__(self, db: Database):
        self.db = db

    def create_interface(self, user_state: gr.State) -> gr.Blocks:
        with gr.Blocks() as login_demo:
            with gr.Tab("用户登录"):
                login_username = gr.Textbox(label="用户名", placeholder="请输入用户名")
                login_btn = gr.Button("登录", variant="primary")
                login_status = gr.Textbox(label="登录状态", interactive=False)

            with gr.Tab("用户注册"):
                reg_username = gr.Textbox(label="用户名", placeholder="请输入用户名")
                register_btn = gr.Button("注册", variant="secondary")
                reg_status = gr.Textbox(label="注册状态", interactive=False)

            def login(username):
                if not username:
                    return "用户名不能为空"
                user = self.db.login_user(username)
                if user:
                    return user.user_id, f"登录成功！欢迎，{user.username}"
                else:
                    return None, "用户名错误"

            def register(username):
                if not username:
                    return "用户名不能为空"
                try:
                    user = self.db.register_user(username)
                    if user:
                        return user.user_id, f"注册成功！用户ID: {user.user_id}"
                    else:
                        return None, "注册失败"
                except Exception as e:
                    return None, f"注册时出错: {str(e)}"

            login_btn.click(
                login,
                inputs=[login_username],
                outputs=[user_state, login_status]
            )
            register_btn.click(
                register,
                inputs=[reg_username],
                outputs=[user_state, reg_status]
            )

        return login_demo