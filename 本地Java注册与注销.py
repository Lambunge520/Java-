import os
import sys
import ctypes

# =====================================================================
# 1. 前置处理：提权与隐藏控制台窗口 (必须放在最前面执行)
# =====================================================================

def hide_console():
    """调用 Windows API 隐藏当前的控制台窗口"""
    whnd = ctypes.windll.kernel32.GetConsoleWindow()
    if whnd != 0:
        ctypes.windll.user32.ShowWindow(whnd, 0) # 0 表示隐藏 (SW_HIDE)

def is_admin():
    """检查是否拥有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# 如果不是管理员，尝试提权运行
if not is_admin():
    # 使用 runas 提权重新运行自己
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
    sys.exit()

# 如果已经有管理员权限了，立刻隐藏背后的黑框控制台！
hide_console()

# =====================================================================
# 2. 导入其余模块并定义核心业务逻辑 (提权和隐藏窗口之后再导入)
# =====================================================================

import winreg
import tkinter as tk
from tkinter import filedialog, messagebox

class JavaRegistryManager:
    def __init__(self, root):
        self.root = root
        self.root.title("HMCL 本地 Java 注册管理工具")
        self.root.geometry("600x450")
        
        self.reg_base_path = r"SOFTWARE\JavaSoft\JDK"
        
        # 扫描到的待注册 Java 列表
        self.scanned_javas = [] 
        # 已在注册表中的 Java 列表
        self.registered_javas = []

        self.setup_ui()
        self.refresh_registered_list()

    def setup_ui(self):
        # 左侧面板：扫描与注册
        left_frame = tk.LabelFrame(self.root, text="添加/注册本地 Java (解压版)", padx=10, pady=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Button(left_frame, text="选择存放 Java 的文件夹", command=self.scan_folder).pack(fill=tk.X, pady=5)
        
        # 待注册列表框 (支持多选)
        self.lb_unreg = tk.Listbox(left_frame, selectmode=tk.MULTIPLE, height=15)
        self.lb_unreg.pack(fill=tk.BOTH, expand=True, pady=5)

        # 全选/取消全选按钮组
        btn_frame1 = tk.Frame(left_frame)
        btn_frame1.pack(fill=tk.X)
        tk.Button(btn_frame1, text="全选", command=lambda: self.select_all(self.lb_unreg)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(btn_frame1, text="取消全选", command=lambda: self.deselect_all(self.lb_unreg)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        tk.Button(left_frame, text="注册选中的 Java", command=self.register_selected, bg="#d4edda").pack(fill=tk.X, pady=10)

        # 右侧面板：注销已注册的 Java
        right_frame = tk.LabelFrame(self.root, text="管理已注册的 Java", padx=10, pady=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(right_frame, text="系统注册表中已存在的 Java：").pack(anchor=tk.W, pady=5)

        # 已注册列表框 (支持多选)
        self.lb_reg = tk.Listbox(right_frame, selectmode=tk.MULTIPLE, height=15)
        self.lb_reg.pack(fill=tk.BOTH, expand=True, pady=5)

        # 全选/取消全选按钮组
        btn_frame2 = tk.Frame(right_frame)
        btn_frame2.pack(fill=tk.X)
        tk.Button(btn_frame2, text="全选", command=lambda: self.select_all(self.lb_reg)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(btn_frame2, text="取消全选", command=lambda: self.deselect_all(self.lb_reg)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        tk.Button(right_frame, text="取消注册选中的 Java", command=self.unregister_selected, bg="#f8d7da").pack(fill=tk.X, pady=10)

    def select_all(self, listbox):
        listbox.select_set(0, tk.END)

    def deselect_all(self, listbox):
        listbox.selection_clear(0, tk.END)

    def scan_folder(self):
        folder_path = filedialog.askdirectory(title="选择包含 Java 的父文件夹")
        if not folder_path:
            return

        self.scanned_javas.clear()
        self.lb_unreg.delete(0, tk.END)

        found_count = 0
        for item in os.listdir(folder_path):
            full_path = os.path.join(folder_path, item)
            if os.path.isdir(full_path):
                java_exe = os.path.join(full_path, "bin", "java.exe")
                if os.path.exists(java_exe):
                    version_str = item.replace("jdk-", "").replace("jdk", "").strip()
                    if not version_str:
                        version_str = f"Custom_{found_count}"
                    
                    self.scanned_javas.append({"version": version_str, "path": full_path})
                    self.lb_unreg.insert(tk.END, f"{version_str} ({item})")
                    found_count += 1
        
        if found_count == 0:
            messagebox.showinfo("提示", "未在该目录下找到包含 bin\\java.exe 的文件夹。")

    def refresh_registered_list(self):
        self.registered_javas.clear()
        self.lb_reg.delete(0, tk.END)
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, self.reg_base_path, 0, winreg.KEY_READ)
            index = 0
            while True:
                try:
                    sub_key_name = winreg.EnumKey(key, index)
                    self.registered_javas.append(sub_key_name)
                    self.lb_reg.insert(tk.END, f"版本: {sub_key_name}")
                    index += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except FileNotFoundError:
            pass

    def register_selected(self):
        selected_indices = self.lb_unreg.curselection()
        if not selected_indices:
            messagebox.showwarning("警告", "请先在左侧列表中勾选要注册的 Java！")
            return

        success_count = 0
        for i in selected_indices:
            java_info = self.scanned_javas[i]
            version_str = java_info["version"]
            java_home = java_info["path"]
            registry_path = rf"{self.reg_base_path}\{version_str}"

            try:
                key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, registry_path, 0, winreg.KEY_WRITE)
                winreg.SetValueEx(key, "JavaHome", 0, winreg.REG_SZ, java_home)
                
                jvm_path = os.path.join(java_home, "bin", "server", "jvm.dll")
                if not os.path.exists(jvm_path):
                    jvm_path = os.path.join(java_home, "bin", "jvm.dll")
                if os.path.exists(jvm_path):
                    winreg.SetValueEx(key, "RuntimeLib", 0, winreg.REG_SZ, jvm_path)
                    
                winreg.CloseKey(key)
                success_count += 1
            except Exception as e:
                messagebox.showerror("错误", f"注册 {version_str} 失败: {e}")

        messagebox.showinfo("成功", f"成功注册了 {success_count} 个 Java 版本！")
        self.refresh_registered_list()

    def unregister_selected(self):
        selected_indices = self.lb_reg.curselection()
        if not selected_indices:
            messagebox.showwarning("警告", "请先在右侧列表中勾选要取消注册的 Java！")
            return

        if not messagebox.askyesno("确认", "确定要从系统注册表中移除选中的 Java 吗？\n(仅移除注册信息，不会删除文件)"):
            return

        success_count = 0
        try:
            parent_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, self.reg_base_path, 0, winreg.KEY_ALL_ACCESS)
            
            for i in selected_indices:
                version_to_remove = self.registered_javas[i]
                try:
                    winreg.DeleteKey(parent_key, version_to_remove)
                    success_count += 1
                except Exception as e:
                    messagebox.showerror("错误", f"删除 {version_to_remove} 失败，可能存在子项: {e}")
            
            winreg.CloseKey(parent_key)
        except Exception as e:
            messagebox.showerror("错误", f"打开注册表父项失败: {e}")

        messagebox.showinfo("成功", f"成功注销了 {success_count} 个 Java 版本！")
        self.refresh_registered_list()

if __name__ == "__main__":
    root = tk.Tk()
    app = JavaRegistryManager(root)
    root.mainloop()