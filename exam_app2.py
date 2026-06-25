import tkinter as tk
from tkinter import messagebox, filedialog
import json
import os
import sys

# ========== 路径适配工具函数 ==========
def resource_path(relative_path):
    """获取内置资源的绝对路径，兼容开发环境和PyInstaller打包后"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_exe_dir():
    """获取exe/脚本所在的目录，用于保存用户答题记录（持久化）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


class Question:
    def __init__(self, qid, q_type, title, options, answer):
        self.qid = qid
        self.type = q_type
        self.title = title
        self.options = options
        self.answer = answer
        self.user_answer = None
        self.is_correct = None


# ========== 启动封面欢迎页 ==========
class WelcomePage(tk.Frame):
    def __init__(self, root, start_callback):
        super().__init__(root)
        self.root = root
        self.start_callback = start_callback
        self.pack(expand=True, fill="both")
        bg_color = "#f5f7fa"
        self.config(bg=bg_color)

        tk.Label(self, text="国际法期末考试刷题系统", font=("微软雅黑", 24, "bold"), bg=bg_color, fg="#2c3e50").pack(pady=60)
        tk.Label(self, text="单选/多选全真模拟 | 即时判分解析 | 答题记录永久保存", font=("微软雅黑", 12), bg=bg_color, fg="#34495e").pack(pady=10)
        
        btn_frame = tk.Frame(self, bg=bg_color)
        btn_frame.pack(pady=40)

        tk.Button(btn_frame, text="开始模考", width=15, height=2, font=("微软雅黑", 14, "bold"), 
                  bg="#3498db", fg="white", command=self.on_start).pack(pady=10)
        
        tk.Button(btn_frame, text="清空历史记录", width=15, height=2, font=("微软雅黑", 12), 
                  bg="#e67e22", fg="white", command=self.clear_history).pack(pady=10)

        tk.Label(self, text="内置国际法期末题库，答题记录自动保存在软件同级目录", font=("微软雅黑", 10), bg=bg_color, fg="#7f8c8d").pack(pady=20)

    def on_start(self):
        self.destroy()
        self.start_callback()

    def clear_history(self):
        """清空exe同级目录下的答题记录"""
        history_path = os.path.join(get_exe_dir(), "user_history.json")
        if os.path.exists(history_path):
            try:
                os.remove(history_path)
                messagebox.showinfo("清理成功", "刷题记录已全部清空，重启软件后生效！", parent=self.root)
            except Exception as e:
                messagebox.showerror("清理失败", f"无法删除记录文件：{e}", parent=self.root)
        else:
            messagebox.showinfo("提示", "当前没有历史记录，无需清空。", parent=self.root)


# ========== 刷题主界面 ==========
class ExamApp:
    def __init__(self, root, question_list, json_path):
        self.root = root
        self.root.title("国际法期末考试刷题系统")
        self.root.geometry("800x550")
        self.questions = question_list
        self.total = len(question_list)
        self.current_idx = 0
        self.opt_vars = {}
        
        self.history_path = os.path.join(get_exe_dir(), "user_history.json")
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)

        # 顶部状态栏
        top_frame = tk.Frame(root, pady=10)
        top_frame.pack(fill="x", padx=25)
        self.progress_label = tk.Label(top_frame, text="", font=("微软雅黑", 10))
        self.progress_label.pack(side="left")
        self.type_label = tk.Label(top_frame, text="", font=("微软雅黑", 10, "bold"), fg="#8e44ad")
        self.type_label.pack(side="left", padx=20)
        self.score_label = tk.Label(top_frame, text="", font=("微软雅黑", 10), fg="#2c3e50")
        self.score_label.pack(side="right")

        # 题干区域
        q_frame = tk.Frame(root, padx=25, pady=10)
        q_frame.pack(fill="x")
        self.q_title = tk.Label(q_frame, text="", wraplength=700, justify="left", font=("微软雅黑", 12, "bold"))
        self.q_title.pack(anchor="w")

        # 选项区域
        self.opt_frame = tk.Frame(root, padx=45, pady=10)
        self.opt_frame.pack(fill="both", expand=True)

        # 结果提示
        self.result_label = tk.Label(root, text="", font=("微软雅黑", 11, "bold"))
        self.result_label.pack(pady=5)

        # 底部按钮栏
        btn_frame = tk.Frame(root, pady=15)
        btn_frame.pack()
        
        tk.Button(btn_frame, text="上一题", width=8, command=self.prev_question, font=("微软雅黑", 10)).pack(side="left", padx=6)
        tk.Button(btn_frame, text="看答案解析", width=10, command=self.check_current_answer, font=("微软雅黑", 10), bg="#f39c12", fg="white").pack(side="left", padx=6)
        tk.Button(btn_frame, text="下一题", width=8, command=self.next_question, font=("微软雅黑", 10)).pack(side="left", padx=6)
        
        tk.Button(btn_frame, text="交卷出分", width=10, command=self.show_final_result, font=("微软雅黑", 10, "bold"), bg="#27ae60", fg="white").pack(side="left", padx=15)
        
        tk.Button(btn_frame, text="保存并退出", width=10, command=self.save_and_exit, font=("微软雅黑", 10), bg="#e74c3c", fg="white").pack(side="left", padx=6)

        self.load_question(0)
        self.update_stats()

    def auto_save_current(self):
        q = self.questions[self.current_idx]
        user_ans = self.get_user_answer(q)
        
        if user_ans: 
            q.user_answer = user_ans
            q.is_correct = (user_ans == q.answer)
        else:
            q.user_answer = None
            q.is_correct = None
            
        self.save_history()
        self.update_stats()

    def on_option_select(self):
        self.result_label.config(text="")
        self.auto_save_current()

    def load_question(self, idx):
        if idx < 0 or idx >= self.total: return
        self.current_idx = idx
        q = self.questions[idx]

        for widget in self.opt_frame.winfo_children(): widget.destroy()
        self.opt_vars.clear()
        self.result_label.config(text="")

        self.q_title.config(text=f"{q.qid}. {q.title}")
        self.type_label.config(text="【单选题】" if q.type == "single" else "【多选题】")

        opt_keys = sorted(q.options.keys())
        if q.type == "single":
            var = tk.StringVar(master=self.opt_frame, value="None")
            self.opt_vars["single"] = var
            for key in opt_keys:
                tk.Radiobutton(self.opt_frame, text=f"{key}. {q.options[key]}", variable=var, value=key, 
                               font=("微软雅黑", 11), command=self.on_option_select).pack(anchor="w", pady=6)
        else:
            for key in opt_keys:
                var = tk.BooleanVar(master=self.opt_frame, value=False)
                self.opt_vars[key] = var
                tk.Checkbutton(self.opt_frame, text=f"{key}. {q.options[key]}", variable=var, 
                               font=("微软雅黑", 11), command=self.on_option_select).pack(anchor="w", pady=6)

        if q.user_answer:
            self.restore_user_answer(q)

    def restore_user_answer(self, q):
        if q.type == "single":
            self.opt_vars["single"].set(q.user_answer)
        else:
            for k in self.opt_vars:
                self.opt_vars[k].set(k in q.user_answer)

    def get_user_answer(self, q):
        if q.type == "single":
            val = self.opt_vars["single"].get().strip()
            return "" if val == "None" else val
        else:
            selected = [k for k, v in self.opt_vars.items() if v.get()]
            selected.sort()
            return "".join(selected)

    def check_current_answer(self):
        q = self.questions[self.current_idx]
        user_ans = self.get_user_answer(q)
        if len(user_ans) == 0:
            messagebox.showinfo("提示", "请先选择选项", parent=self.root)
            return
        
        if q.is_correct:
            self.result_label.config(text="✅ 回答正确！", fg="#27ae60")
        else:
            self.result_label.config(text=f"❌ 回答错误，您的答案：{q.user_answer} | 正确答案：{q.answer}", fg="#e74c3c")

    def show_final_result(self):
        self.auto_save_current()
        correct = sum(1 for q in self.questions if q.is_correct)
        done = sum(1 for q in self.questions if q.user_answer)
        unanswered = self.total - done
        rate = f"{correct/done*100:.1f}%" if done > 0 else "0%"
        
        msg = f"【国际法期末模考报告】\n\n总题数：{self.total} 道\n已作答：{done} 道\n未作答：{unanswered} 道\n\n答对：{correct} 道\n正确率：{rate}"
        messagebox.showinfo("交卷出分", msg, parent=self.root)

    def prev_question(self):
        self.auto_save_current()
        if self.current_idx > 0: self.load_question(self.current_idx - 1)

    def next_question(self):
        self.auto_save_current()
        if self.current_idx < self.total - 1:
            self.load_question(self.current_idx + 1)
        else:
            messagebox.showinfo("提示", "已经是最后一题了，可以点击【交卷出分】查看总成绩。", parent=self.root)

    def update_stats(self):
        done = sum(1 for q in self.questions if q.user_answer)
        correct = sum(1 for q in self.questions if q.is_correct)
        rate = f"{correct/done*100:.1f}%" if done > 0 else "-"
        self.progress_label.config(text=f"进度：{self.current_idx+1} / {self.total}")
        self.score_label.config(text=f"已答 {done} 题 | 正确 {correct} 题 | 正确率 {rate}")

    def save_history(self):
        history_data = {}
        for q in self.questions:
            if q.user_answer:
                history_data[str(q.qid)] = {
                    "user_answer": q.user_answer,
                    "is_correct": q.is_correct
                }
        try:
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(history_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存记录失败: {e}")

    def on_window_close(self):
        self.auto_save_current()
        self.root.destroy()

    def save_and_exit(self):
        self.auto_save_current()
        self.root.destroy()


# ========== 程序入口 ==========
if __name__ == "__main__":
    root = tk.Tk()
    root.title("国际法期末考试刷题系统")
    root.geometry("800x550")

    def start_exam():
        json_path = resource_path("question_bank2.json")
        
        if not os.path.exists(json_path):
            json_path = filedialog.askopenfilename(
                title="选择题库JSON文件", filetypes=[("JSON题库文件", "*.json")], parent=root)
            if not json_path:
                root.destroy()
                return
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                q_data = json.load(f)
            question_list = [Question(item["id"], item["type"], item["question"], item["options"], item["answer"]) for item in q_data]

            history_path = os.path.join(get_exe_dir(), "user_history.json")
            if os.path.exists(history_path):
                with open(history_path, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
                for q in question_list:
                    qid_str = str(q.qid)
                    if qid_str in history_data:
                        q.user_answer = history_data[qid_str]["user_answer"]
                        q.is_correct = history_data[qid_str]["is_correct"]

            ExamApp(root, question_list, json_path)
            
        except Exception as e:
            messagebox.showerror("加载失败", f"题库读取出错：{str(e)}", parent=root)
            root.destroy()

    WelcomePage(root, start_exam)
    root.mainloop()