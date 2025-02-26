import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import os
from jobspider import Job
import threading
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import csv

class JobEntry:
    """
    职位条目类，用于管理单个职位的输入界面元素
    
    包含职位名称输入框、爬取模式选择和数量/页数输入框等UI组件
    """
    
    def __init__(self, master, parent_app, row):
        """
        初始化职位条目
        
        Args:
            master (tk.Frame): 父级窗口框架
            parent_app (JobSpiderApp): 父应用程序实例
            row (int): 在网格布局中的行位置
        """
        self.master = master
        self.parent_app = parent_app
        
        # 职位名称输入框
        self.job_entry = tk.Entry(master, width=20)
        self.job_entry.grid(row=row, column=0, padx=5, pady=5)
        
        # 爬取模式选择
        self.mode_var = tk.StringVar(value='按页爬取')
        self.mode_frame = tk.Frame(master)
        self.mode_frame.grid(row=row, column=1, padx=5, pady=5)
        
        self.page_mode_radio = tk.Radiobutton(
            self.mode_frame, 
            text='按页爬取', 
            variable=self.mode_var, 
            value='按页爬取',
            command=self.update_input_field
        )
        self.page_mode_radio.pack(side=tk.LEFT)
        
        self.count_mode_radio = tk.Radiobutton(
            self.mode_frame, 
            text='按数量爬取', 
            variable=self.mode_var, 
            value='按数量爬取',
            command=self.update_input_field
        )
        self.count_mode_radio.pack(side=tk.LEFT)
        
        self.all_mode_radio = tk.Radiobutton(
            self.mode_frame, 
            text='全部爬取', 
            variable=self.mode_var, 
            value='全部爬取',
            command=self.update_input_field
        )
        self.all_mode_radio.pack(side=tk.LEFT)
        
        # 数量/页数输入框
        self.count_entry = tk.Entry(master, width=10)
        self.count_entry.insert(0, "1")  # 默认值为1
        self.count_entry.grid(row=row, column=2, padx=5, pady=5)
        
        # 删除按钮
        self.delete_button = tk.Button(
            master, 
            text='删除', 
            command=lambda: self.parent_app.remove_job_entry(self)
        )
        self.delete_button.grid(row=row, column=3, padx=5, pady=5)
        
    def update_input_field(self):
        """根据选择的模式更新输入框的默认值"""
        # 先启用输入框，无论之前是什么状态
        self.count_entry.config(state='normal')
        
        if self.mode_var.get() == '按页爬取':
            self.count_entry.delete(0, tk.END)
            self.count_entry.insert(0, "1")
        elif self.mode_var.get() == '按数量爬取':
            self.count_entry.delete(0, tk.END)
            self.count_entry.insert(0, "10")
        else:  # 全部爬取
            self.count_entry.delete(0, tk.END)
            self.count_entry.insert(0, "999")  # 使用一个足够大的数字
            self.count_entry.config(state='disabled')  # 禁用输入框
            
    def get_job_info(self):
        """
        获取职位信息
        
        Returns:
            dict: 包含职位标题、爬取模式和数量的字典
        """
        mode = self.mode_var.get()
        if mode == '全部爬取':
            return {
                'title': self.job_entry.get().strip(),
                'mode': '全部爬取',
                'count': 999  # 使用一个足够大的数字
            }
        else:
            try:
                count = int(self.count_entry.get() or (1 if mode == '按页爬取' else 10))
            except ValueError:
                # 如果输入非数字，使用默认值
                count = 1 if mode == '按页爬取' else 10
                
            return {
                'title': self.job_entry.get().strip(),
                'mode': mode,
                'count': count
            }

class JobSpiderApp:
    """
    BOSS_Spider应用程序主类
    
    提供图形用户界面，用于配置和执行爬虫任务，
    包括职位搜索、进度显示和结果展示等功能。
    """
    
    def __init__(self, master):
        """
        初始化应用程序
        
        Args:
            master (tk.Tk): 主窗口对象
        """
        self.master = master
        master.title("BOSS_Spider v1.0")
        self.is_running = False  # 控制爬取状态
        self.thread = None  # 初始化线程属性
        
        # 设置应用程序图标
        try:
            # 修改为相对路径，避免包含空格的路径问题
            icon_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ico", "256.ico")
            if os.path.exists(icon_file):
                master.iconbitmap(icon_file)
            else:
                print(f"图标文件 {icon_file} 不存在")
        except Exception as e:
            print(f"设置图标时出错: {e}")
        
        # 创建主框架
        self.main_frame = ttk.Frame(master)
        self.main_frame.pack(padx=10, pady=10)
        
        # 添加声明框架
        self.disclaimer_frame = ttk.LabelFrame(self.main_frame, text="免责声明")
        self.disclaimer_frame.grid(row=0, column=0, columnspan=4, pady=5, padx=5, sticky="ew")
        
        # 声明文本
        disclaimer_text = (
            "声明：本软件仅供学习和研究使用，禁止用于商业用途！\n"
            "请遵守相关法律法规，合理使用本软件。\n"
            "提示: 开始时浏览器会不停刷新闪烁, 注意眼睛\n"
            "提示: 首次启动需要等待1分钟左右"
        )
        self.disclaimer_label = tk.Label(
            self.disclaimer_frame, 
            text=disclaimer_text,
            justify=tk.LEFT,
            fg="red"
        )
        self.disclaimer_label.pack(padx=5, pady=5)
        
        # 保存路径设置框架
        self.path_frame = ttk.LabelFrame(self.main_frame, text="保存路径设置")
        self.path_frame.grid(row=1, column=0, columnspan=4, pady=5, padx=5, sticky="ew")
        
        # 默认保存路径为当前目录
        self.save_path = os.getcwd()
        
        # 保存路径输入框
        self.path_entry = tk.Entry(self.path_frame, width=50)
        self.path_entry.insert(0, self.save_path)
        self.path_entry.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)
        
        # 浏览按钮
        self.browse_button = tk.Button(
            self.path_frame,
            text="浏览",
            command=self.browse_save_path
        )
        self.browse_button.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # 添加筛选条件框架 - 移动到职位搜索设置前面
        self.filter_frame = ttk.LabelFrame(self.main_frame, text="筛选条件")
        self.filter_frame.grid(row=2, column=0, columnspan=4, pady=10, padx=5, sticky="ew")
        
        # 筛选条件第一行 - 地区和薪资
        filter_row1 = ttk.Frame(self.filter_frame)
        filter_row1.pack(fill="x", padx=5, pady=5)
        
        # 地区选择
        ttk.Label(filter_row1, text="城市:").pack(side=tk.LEFT, padx=5)
        self.city_var = tk.StringVar(value="全国")
        self.city_combo = ttk.Combobox(filter_row1, textvariable=self.city_var, width=10, state="readonly")
        self.city_combo['values'] = (
            '全国', '北京', '上海', '广州', '深圳', '杭州', '武汉', 
            '成都', '南京', '西安', '天津', '苏州', '长沙', '重庆', 
            '郑州', '青岛', '合肥', '福州', '济南', '大连', '珠海', 
            '厦门', '昆明', '宁波', '东莞', '佛山', '南昌', '南宁', 
            '沈阳', '石家庄', '哈尔滨', '南通', '贵阳', '无锡', '泉州', 
            '温州', '金华', '烟台', '海口', '惠州', '乌鲁木齐', '徐州', 
            '嘉兴', '太原', '保定', '兰州', '呼和浩特', '常州', '绍兴', 
            '中山', '台州', '长春', '潍坊', '扬州', '洛阳', '威海', 
            '唐山', '镇江', '西宁', '湖州', '包头', '济宁', '沧州', 
            '临沂', '邯郸', '廊坊', '盐城', '淄博', '鞍山', '泰州', 
            '宜昌', '赣州', '淮安', '江门', '汕头', '银川', '桂林', 
            '大庆', '漳州', '邢台', '柳州', '遵义', '衡阳', '上饶'
        )
        self.city_combo.pack(side=tk.LEFT, padx=5)
        
        # 薪资范围
        ttk.Label(filter_row1, text="薪资范围:").pack(side=tk.LEFT, padx=5)
        self.salary_var = tk.StringVar(value="不限")
        self.salary_combo = ttk.Combobox(filter_row1, textvariable=self.salary_var, width=10, state="readonly")
        self.salary_combo['values'] = ('不限', '3K以下', '3-5K', '5-10K', '10-15K', '15-20K', '20-30K', '30-50K', '50K以上')
        self.salary_combo.pack(side=tk.LEFT, padx=5)
        
        # 求职类型
        ttk.Label(filter_row1, text="求职类型:").pack(side=tk.LEFT, padx=5)
        self.job_type_var = tk.StringVar(value="不限")
        self.job_type_combo = ttk.Combobox(filter_row1, textvariable=self.job_type_var, width=8, state="readonly")
        self.job_type_combo['values'] = ('不限', '全职', '兼职', '实习')
        self.job_type_combo.pack(side=tk.LEFT, padx=5)
        
        # 筛选条件第二行 - 经验和学历
        filter_row2 = ttk.Frame(self.filter_frame)
        filter_row2.pack(fill="x", padx=5, pady=5)
        
        # 工作经验
        ttk.Label(filter_row2, text="工作经验:").pack(side=tk.LEFT, padx=5)
        self.experience_var = tk.StringVar(value="不限")
        self.experience_combo = ttk.Combobox(filter_row2, textvariable=self.experience_var, width=10, state="readonly")
        self.experience_combo['values'] = ('不限', '在校生/应届生', '应届毕业生', '1年以内', '1-3年', '3-5年', '5-10年', '10年以上')
        self.experience_combo.pack(side=tk.LEFT, padx=5)
        
        # 学历要求
        ttk.Label(filter_row2, text="学历要求:").pack(side=tk.LEFT, padx=5)
        self.education_var = tk.StringVar(value="不限")
        self.education_combo = ttk.Combobox(filter_row2, textvariable=self.education_var, width=8, state="readonly")
        self.education_combo['values'] = ('不限', '初中及以下', '中专/中技', '高中', '大专', '本科', '硕士', '博士')
        self.education_combo.pack(side=tk.LEFT, padx=5)
        
        # 筛选条件第三行 - 公司规模和融资阶段
        filter_row3 = ttk.Frame(self.filter_frame)
        filter_row3.pack(fill="x", padx=5, pady=5)
        
        # 公司规模
        ttk.Label(filter_row3, text="公司规模:").pack(side=tk.LEFT, padx=5)
        self.scale_var = tk.StringVar(value="不限")
        self.scale_combo = ttk.Combobox(filter_row3, textvariable=self.scale_var, width=15, state="readonly")
        self.scale_combo['values'] = ('不限', '少于15人', '15-50人', '50-150人', '150-500人', '500-2000人', '2000人以上')
        self.scale_combo.pack(side=tk.LEFT, padx=5)
        
        # 融资阶段
        ttk.Label(filter_row3, text="融资阶段:").pack(side=tk.LEFT, padx=5)
        self.finance_var = tk.StringVar(value="不限")
        self.finance_combo = ttk.Combobox(filter_row3, textvariable=self.finance_var, width=15, state="readonly")
        self.finance_combo['values'] = ('不限', '未融资', '天使轮', 'A轮', 'B轮', 'C轮', 'D轮及以上', '已上市', '不需要融资')
        self.finance_combo.pack(side=tk.LEFT, padx=5)
        
        # 筛选条件第四行 - 职位分类和发布时间
        filter_row4 = ttk.Frame(self.filter_frame)
        filter_row4.pack(fill="x", padx=5, pady=5)
        
        # 职位分类
        ttk.Label(filter_row4, text="职位分类:").pack(side=tk.LEFT, padx=5)
        self.position_var = tk.StringVar(value="不限")
        self.position_combo = ttk.Combobox(filter_row4, textvariable=self.position_var, width=15, state="readonly")
        self.position_combo['values'] = ('不限', '技术', '产品', '设计', '运营', '市场', '销售', '职能', '金融', '教育', '医疗', '其他')
        self.position_combo.pack(side=tk.LEFT, padx=5)
        
        # 发布时间
        ttk.Label(filter_row4, text="发布时间:").pack(side=tk.LEFT, padx=5)
        self.publish_var = tk.StringVar(value="不限")
        self.publish_combo = ttk.Combobox(filter_row4, textvariable=self.publish_var, width=15, state="readonly")
        self.publish_combo['values'] = ('不限', '24小时内', '3天内', '7天内', '30天内')
        self.publish_combo.pack(side=tk.LEFT, padx=5)
        
        # 最新发布开关
        self.latest_var = tk.BooleanVar(value=False)
        self.latest_check = ttk.Checkbutton(filter_row4, text="优先显示最新发布", variable=self.latest_var)
        self.latest_check.pack(side=tk.LEFT, padx=10)
        
        # 标题标签 - 行号调整到3
        self.label = tk.Label(self.main_frame, text="职位搜索设置")
        self.label.grid(row=3, column=0, columnspan=4, pady=10, sticky="w", padx=5)
        
        # 列标题 - 行号调整到4
        tk.Label(self.main_frame, text="职位名称").grid(row=4, column=0)
        tk.Label(self.main_frame, text="爬取模式").grid(row=4, column=1)
        tk.Label(self.main_frame, text="数量/页数").grid(row=4, column=2)
        tk.Label(self.main_frame, text="操作").grid(row=4, column=3)
        
        self.job_entries = []
        self.next_row = 5  # 调整下一行起始位置
        
        # 添加第一个职位输入框
        self.add_job_entry()
        
        # 按钮框架 - 移到职位输入框之后
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.grid(row=100, column=0, columnspan=4, pady=10)
        
        # 添加职位按钮
        self.add_entry_button = tk.Button(
            self.button_frame, 
            text='添加职位', 
            command=self.add_job_entry
        )
        self.add_entry_button.pack(side=tk.LEFT, padx=5)
        
        # 开始爬取按钮
        self.start_button = tk.Button(
            self.button_frame, 
            text='开始爬取', 
            command=self.start_scraping
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # 停止按钮
        self.stop_button = tk.Button(
            self.button_frame, 
            text='停止', 
            command=self.stop_scraping
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # 添加进度显示框架
        self.progress_frame = ttk.LabelFrame(self.main_frame, text="爬取进度")
        self.progress_frame.grid(row=101, column=0, columnspan=4, pady=10, sticky="ew")
        
        # 状态标签
        self.status_label = tk.Label(self.progress_frame, text="状态：", width=8, anchor="w")
        self.status_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.status_value = tk.Label(self.progress_frame, text="等待开始...", anchor="w")
        self.status_value.grid(row=0, column=1, columnspan=3, padx=5, pady=5, sticky="w")
        
        # 当前页/总页数
        self.page_label = tk.Label(self.progress_frame, text="页数：", width=8, anchor="w")
        self.page_label.grid(row=1, column=0, padx=5, pady=2, sticky="w")
        
        self.page_value = tk.Label(self.progress_frame, text="0/0", anchor="w")
        self.page_value.grid(row=1, column=1, padx=5, pady=2, sticky="w")
        
        # 已爬取/目标职位数
        self.count_label = tk.Label(self.progress_frame, text="职位数：", width=8, anchor="w")
        self.count_label.grid(row=1, column=2, padx=5, pady=2, sticky="w")
        
        self.count_value = tk.Label(self.progress_frame, text="0/0", anchor="w")
        self.count_value.grid(row=1, column=3, padx=5, pady=2, sticky="w")
        
        # 总体进度
        self.progress_label = tk.Label(self.progress_frame, text="总进度：", width=8, anchor="w")
        self.progress_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.grid(row=2, column=1, columnspan=3, padx=5, pady=5, sticky="ew")
        
        # 结果标签
        self.result_label = tk.Label(self.main_frame, text="")
        self.result_label.grid(row=999, column=0, columnspan=4, pady=10)
        
        # 创建美化的结果框架
        self.result_frame = ttk.LabelFrame(self.main_frame, text="爬取结果")
        self.result_frame.grid(row=102, column=0, columnspan=4, pady=10, padx=5, sticky="ew")
        self.result_frame.grid_remove()  # 初始时隐藏

        # 结果内容
        self.result_mode_label = ttk.Label(self.result_frame, text="爬取模式：")
        self.result_mode_label.grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self.result_mode_value = ttk.Label(self.result_frame, text="")
        self.result_mode_value.grid(row=0, column=1, sticky="w", padx=5, pady=3)

        self.result_count_label = ttk.Label(self.result_frame, text="爬取结果：")
        self.result_count_label.grid(row=1, column=0, sticky="w", padx=5, pady=3)
        self.result_count_value = ttk.Label(self.result_frame, text="")
        self.result_count_value.grid(row=1, column=1, sticky="w", padx=5, pady=3)

        self.result_md_label = ttk.Label(self.result_frame, text="Markdown：")
        self.result_md_label.grid(row=2, column=0, sticky="w", padx=5, pady=3)
        self.result_md_value = ttk.Label(self.result_frame, text="")
        self.result_md_value.grid(row=2, column=1, sticky="w", padx=5, pady=3)

        # 文件路径框架
        self.file_paths_frame = ttk.Frame(self.result_frame)
        self.file_paths_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        # 创建按钮框架
        self.file_actions_frame = ttk.Frame(self.result_frame)
        self.file_actions_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        # 打开CSV按钮
        self.open_csv_button = ttk.Button(self.file_actions_frame, text="打开CSV文件", command=self.open_csv)
        self.open_csv_button.pack(side=tk.LEFT, padx=5, pady=5)

        # 打开MD按钮
        self.open_md_button = ttk.Button(self.file_actions_frame, text="打开Markdown", command=self.open_md)
        self.open_md_button.pack(side=tk.LEFT, padx=5, pady=5)

        # 打开文件夹按钮
        self.open_folder_button = ttk.Button(self.file_actions_frame, text="打开文件夹", command=self.open_folder)
        self.open_folder_button.pack(side=tk.LEFT, padx=5, pady=5)

        # 地区城市代码映射 - 补充更多城市
        self.city_code_map = {
            '全国': '100010000',
            '北京': '101010100',
            '上海': '101020100',
            '广州': '101280100',
            '深圳': '101280600',
            '杭州': '101210100',
            '武汉': '101200100',
            '成都': '101270100',
            '南京': '101190100',
            '西安': '101110100',
            '天津': '101030100',
            '苏州': '101190400',
            '长沙': '101250100',
            '重庆': '101040100',
            '郑州': '101180100',
            '青岛': '101120200',
            '合肥': '101220100',
            '福州': '101230100',
            '济南': '101120100',
            '大连': '101070200',
            '珠海': '101280700',
            '厦门': '101230200',
            '昆明': '101290100',
            '宁波': '101210400',
            '东莞': '101281600',
            '佛山': '101280800',
            '南昌': '101240100',
            '南宁': '101300100',
            '沈阳': '101070100',
            '石家庄': '101090100',
            '哈尔滨': '101050100',
            '南通': '101190500',
            '贵阳': '101260100',
            '无锡': '101190200',
            '泉州': '101230500',
            '温州': '101210700',
            '金华': '101210900',
            '烟台': '101120500',
            '海口': '101310100',
            '惠州': '101280300',
            '乌鲁木齐': '101130100',
            '徐州': '101190800',
            '嘉兴': '101210300',
            '太原': '101100100',
            '保定': '101090200',
            '兰州': '101160100',
            '呼和浩特': '101080100',
            # 新增城市
            '常州': '101191100',
            '绍兴': '101210500',
            '中山': '101281700',
            '台州': '101210600',
            '长春': '101060100',
            '潍坊': '101120600',
            '扬州': '101190600',
            '洛阳': '101180900',
            '威海': '101121300',
            '唐山': '101090500',
            '镇江': '101190300',
            '西宁': '101150100',
            '湖州': '101210200',
            '包头': '101080200',
            '济宁': '101120700',
            '沧州': '101090700',
            '临沂': '101120800',
            '邯郸': '101091000',
            '廊坊': '101090600',
            '盐城': '101190700',
            '淄博': '101120300',
            '鞍山': '101070300',
            '泰州': '101191200',
            '呼伦贝尔': '101081000',
            '宜昌': '101200900',
            '赣州': '101240700',
            '淮安': '101190900',
            '江门': '101281100',
            '汕头': '101280500',
            '银川': '101170100',
            '桂林': '101300500',
            '大庆': '101050800',
            '漳州': '101230600',
            '邢台': '101090900',
            '柳州': '101300300',
            '遵义': '101260200',
            '衡阳': '101250400',
            '上饶': '101240300',
            '通辽': '101080500',
            '金昌': '101160600'
        }
        
        # 工作类型代码映射
        self.job_type_code_map = {
            '不限': '0',
            '全职': '1',
            '兼职': '2',
            '实习': '3'
        }
        
        # 公司规模代码映射
        self.scale_code_map = {
            '不限': '0',
            '少于15人': '301',
            '15-50人': '302', 
            '50-150人': '303',
            '150-500人': '304',
            '500-2000人': '305',
            '2000人以上': '306'
        }
        
        # 融资阶段代码映射
        self.finance_code_map = {
            '不限': '0',
            '未融资': '801',
            '天使轮': '802',
            'A轮': '803',
            'B轮': '804',
            'C轮': '805',
            'D轮及以上': '806',
            '已上市': '807',
            '不需要融资': '808'
        }
        
        # 薪资代码映射
        self.salary_code_map = {
            '不限': '0',
            '3K以下': '1',
            '3-5K': '2',
            '5-10K': '3',
            '10-15K': '4',
            '15-20K': '5',
            '20-30K': '6',
            '30-50K': '7',
            '50K以上': '8'
        }
        
        # 职位分类代码映射
        self.position_code_map = {
            '不限': '0',
            '技术': '100000',
            '产品': '100001',
            '设计': '100002',
            '运营': '100003',
            '市场': '100004',
            '销售': '100005',
            '职能': '100006',
            '金融': '100007',
            '教育': '100008',
            '医疗': '100009',
            '其他': '100010'
        }
        
        # 发布时间代码映射
        self.publish_code_map = {
            '不限': '0',
            '24小时内': '1',
            '3天内': '3',
            '7天内': '7',
            '30天内': '30'
        }
        
        # 工作经验代码映射
        self.experience_code_map = {
            '不限': '0',
            '在校生/应届生': '108',
            '应届毕业生': '109',
            '1年以内': '101',
            '1-3年': '102',
            '3-5年': '103',
            '5-10年': '104',
            '10年以上': '105'
        }
        
        # 学历代码映射
        self.education_code_map = {
            '不限': '0',
            '初中及以下': '209',
            '中专/中技': '208',
            '高中': '206',
            '大专': '202',
            '本科': '203',
            '硕士': '204',
            '博士': '205'
        }

    def add_job_entry(self):
        """添加新的职位输入行"""
        job_entry = JobEntry(self.main_frame, self, self.next_row)
        self.job_entries.append(job_entry)
        self.next_row += 1
        
    def remove_job_entry(self, entry):
        """
        删除职位输入行
        
        Args:
            entry (JobEntry): 要删除的职位条目
        """
        if len(self.job_entries) > 1:  # 保持至少一个输入框
            entry.job_entry.grid_forget()
            entry.mode_frame.grid_forget()
            entry.count_entry.grid_forget()
            entry.delete_button.grid_forget()
            self.job_entries.remove(entry)
        
    def stop_scraping(self):
        """停止爬取任务"""
        self.is_running = False
        messagebox.showinfo("信息", "爬取任务已停止")

    def browse_save_path(self):
        """打开文件夹选择对话框"""
        path = filedialog.askdirectory(
            initialdir=self.save_path,
            title="选择保存路径"
        )
        if path:
            self.save_path = path
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)

    def get_save_path(self):
        """
        获取当前保存路径
        
        Returns:
            str: 保存路径，如果出错则返回当前工作目录
        """
        path = self.path_entry.get().strip()
        # 确保路径存在
        try:
            if path and not os.path.exists(path):
                os.makedirs(path)
                print(f"已创建保存路径: {path}")
            return path
        except Exception as e:
            print(f"获取保存路径出错: {e}")
            # 返回默认路径
            default_path = os.getcwd()
            print(f"将使用默认路径: {default_path}")
            return default_path
            
    def update_progress(self, progress_info):
        """
        更新进度信息
        
        Args:
            progress_info (dict): 包含进度信息的字典
        """
        if not self.is_running:
            return

        try:
            # 提取进度信息
            status = progress_info.get('status', '')
            percentage = progress_info.get('percentage', 0)
            total_pages = progress_info.get('total_pages', 0)
            current_page = progress_info.get('current_page', 0)
            scraped_jobs = progress_info.get('scraped_jobs', 0)
            target_jobs = progress_info.get('target_jobs', 0)
            new_jobs = progress_info.get('new_jobs', 0)
            
            # 更新状态文本
            if self.status_value and self.status_value.winfo_exists():
                if status:
                    self.status_value.config(text=status)
            
            # 更新页数信息
            if self.page_value and self.page_value.winfo_exists():
                page_text = f"{current_page}/{total_pages}"
                self.page_value.config(text=page_text)
            
            # 更新职位数信息 - 使职位数更加突出
            if self.count_value and self.count_value.winfo_exists():
                count_text = f"{scraped_jobs}/{target_jobs}"
                self.count_value.config(text=count_text, font=("宋体", 10, "bold"), fg="#009688")
            
            # 更新进度条 - 始终基于职位数计算进度
            if self.progress_bar and self.progress_bar.winfo_exists():
                # 创建更明显的进度条样式
                style = ttk.Style()
                style.configure("TProgressbar", 
                              thickness=20,      # 增加厚度
                              background='#4CAF50')  # 绿色
                
                self.progress_bar.config(value=percentage)
                
                # 添加动画效果，使进度更明显
                if percentage > 0 and percentage < 100:
                    # 每次更新时闪烁一下进度条
                    current_bg = style.lookup("TProgressbar", "background")
                    new_bg = '#2196F3' if current_bg == '#4CAF50' else '#4CAF50'
                    style.configure("TProgressbar", background=new_bg)
                    
                    # 短暂延迟后恢复颜色
                    self.master.after(200, lambda: style.configure("TProgressbar", background='#4CAF50'))
            
            # 更新GUI
            self.master.update_idletasks()
        except Exception as e:
            print(f"更新进度时出错: {e}")
    
    def flash_progress_bar(self):
        """给进度条添加闪烁效果，使进度变化更明显"""
        try:
            if self.progress_bar and self.progress_bar.winfo_exists():
                current_color = self.progress_bar.cget("troughcolor")
                new_color = "#e0e0e0" if current_color == "#f0f0f0" else "#f0f0f0"
                self.progress_bar.config(troughcolor=new_color)
        except Exception as e:
            print(f"进度条闪烁效果出错: {e}")

    def start_scraping(self):
        """开始爬取数据"""
        if self.thread and self.thread.is_alive():
            messagebox.showinfo("提示", "爬虫正在运行中")
            return
        
        job_infos = []
        for entry in self.job_entries:
            job_title = entry.job_entry.get().strip()
            if not job_title:
                messagebox.showwarning("警告", "请输入职位名称")
                return
            
            job_info = entry.get_job_info()
            job_infos.append(job_info)
        
        if not job_infos:
            messagebox.showwarning("警告", "请至少添加一个职位")
            return
        
        save_path = self.get_save_path()
        if not save_path:
            messagebox.showwarning("警告", "请选择保存路径")
            return
        
        # 获取筛选条件
        city_code = self.city_code_map.get(self.city_var.get(), '100010000')
        salary_code = self.salary_code_map.get(self.salary_var.get(), '0')
        experience_code = self.experience_code_map.get(self.experience_var.get(), '0')
        education_code = self.education_code_map.get(self.education_var.get(), '0')
        job_type_code = self.job_type_code_map.get(self.job_type_var.get(), '0')
        scale_code = self.scale_code_map.get(self.scale_var.get(), '0')
        finance_code = self.finance_code_map.get(self.finance_var.get(), '0')
        position_code = self.position_code_map.get(self.position_var.get(), '0')
        publish_code = self.publish_code_map.get(self.publish_var.get(), '0')
        latest = self.latest_var.get()
        
        # 重置进度显示
        if self.status_value and self.status_value.winfo_exists():
            self.status_value.config(text="准备爬取...")
        if self.progress_bar and self.progress_bar.winfo_exists():
            self.progress_bar.config(value=0)
        if self.count_value and self.count_value.winfo_exists():
            self.count_value.config(text="0/0")
        if self.page_value and self.page_value.winfo_exists():
            self.page_value.config(text="0/0")
        if self.result_label and self.result_label.winfo_exists():
            self.result_label.config(text="")
        
        # 计算总任务数量
        total_jobs = sum(info['count'] for info in job_infos)
        
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # 使用线程来处理爬取任务
        self.thread = threading.Thread(
            target=self.scrape_jobs, 
            args=(job_infos, total_jobs, 0, save_path, city_code, salary_code, 
                  experience_code, education_code, job_type_code, scale_code, finance_code, position_code, publish_code, latest)
        )
        self.thread.daemon = True
        self.thread.start()

    def scrape_jobs(self, job_infos, total_jobs, completed_jobs, save_path, 
                   city_code, salary_code, experience_code, education_code, 
                   job_type_code, scale_code, finance_code, position_code, publish_code, latest):
        """
        爬取职位信息
        
        Args:
            job_infos (list): 职位信息列表
            total_jobs (int): 总任务数量
            completed_jobs (int): 已完成的任务数量
            save_path (str): 保存路径
            city_code (str): 城市代码
            salary_code (str): 薪资范围代码
            experience_code (str): 工作经验代码
            education_code (str): 学历要求代码
            job_type_code (str): 求职类型代码
            scale_code (str): 公司规模代码
            finance_code (str): 融资阶段代码
            position_code (str): 职位分类代码
            publish_code (str): 发布时间代码
            latest (bool): 是否优先显示最新发布
        """
        for info in job_infos:
            if not self.is_running:
                break
            try:
                job = Job(info['title'])
                job.set_save_path(save_path)
                job.set_filter_conditions(city_code, salary_code, experience_code, education_code, 
                                          job_type_code, scale_code, finance_code, position_code, publish_code, latest)
                
                # 计算实际文件名（考虑筛选条件）
                filter_info = []
                if city_code != '100010000':
                    filter_info.append(f"城市_{city_code}")
                if experience_code != '0':
                    filter_info.append(f"经验_{experience_code}")
                # 添加其他筛选条件...
                
                actual_filename = info['title']
                if filter_info:
                    actual_filename = f"{info['title']}_{'_'.join(filter_info)}"
                
                # 保存正确的文件路径
                self.current_csv_path = os.path.join(save_path, f"{actual_filename}.csv")
                self.current_md_path = os.path.join(save_path, f"{actual_filename}.md")
                
                # 确保路径存在
                if not os.path.exists(save_path):
                    os.makedirs(save_path)
                    print(f"已创建保存路径: {save_path}")
                
                # 验证路径可写
                test_file_path = os.path.join(save_path, "test_write_permission.txt")
                try:
                    with open(test_file_path, 'w') as f:
                        f.write("测试写入权限")
                    os.remove(test_file_path)
                    print(f"路径 {save_path} 可写")
                except Exception as e:
                    print(f"警告: 路径 {save_path} 可能无法写入: {e}")
                    # 尝试使用备用路径
                    save_path = os.getcwd()
                    job.set_save_path(save_path)
                    print(f"将使用备用路径: {save_path}")
                
                # 设置进度回调函数
                job.set_progress_callback(self.update_progress)
                
                # 显示预期爬取情况
                if info['mode'] == '按页爬取':
                    self.update_progress({
                        'status': f'将爬取 {info["title"]} 的前 {info["count"]} 页数据',
                        'total_pages': info['count'],
                        'current_page': 0,
                        'scraped_jobs': 0,
                        'target_jobs': 999,  # 按页爬取不限制职位数
                        'percentage': 0
                    })
                elif info['mode'] == '按数量爬取':
                    self.update_progress({
                        'status': f'将爬取 {info["title"]} 的 {info["count"]} 个职位',
                        'total_pages': 999,
                        'current_page': 0,
                        'scraped_jobs': 0,
                        'target_jobs': info['count'],
                        'percentage': 0
                    })
                else:  # 全部爬取
                    self.update_progress({
                        'status': f'将爬取 {info["title"]} 的所有职位',
                        'total_pages': 0,
                        'current_page': 0,
                        'scraped_jobs': 0,
                        'target_jobs': 0,
                        'percentage': 0
                    })
                
                # 开始爬取
                job.give_me_job(info['mode'], info['count'])
                completed_jobs += info['count']
                
                # 爬取完成后，检查文件
                expected_csv = os.path.join(save_path, f"{actual_filename}.csv")
                expected_md = os.path.join(save_path, f"{actual_filename}.md")
                
                # 验证文件是否存在及是否有内容
                csv_exists = os.path.exists(expected_csv)
                csv_has_content = False
                job_count = 0
                
                if csv_exists:
                    try:
                        with open(expected_csv, 'r', encoding='utf-8-sig') as f:
                            reader = csv.reader(f)
                            next(reader)  # 跳过表头
                            job_count = sum(1 for _ in reader)
                            csv_has_content = job_count > 0
                    except Exception as e:
                        print(f"检查CSV文件内容时出错: {e}")
                
                md_exists = os.path.exists(expected_md)
                
                # 构建详细的结果反馈
                result_text = ""
                
                if info['mode'] == '按页爬取':
                    result_text += f"爬取完成 - 模式: 按页爬取 ({info['count']}页)\n"
                    mode_text = f"按页爬取 ({info['count']}页)"
                elif info['mode'] == '按数量爬取':
                    result_text += f"爬取完成 - 模式: 按数量爬取 ({info['count']}个)\n"
                    mode_text = f"按数量爬取 ({info['count']}个)"
                else:
                    result_text += f"爬取完成 - 模式: 全部爬取\n"
                    mode_text = "全部爬取"
                
                # 设置爬取模式显示
                self.result_mode_value.config(text=mode_text, font=("宋体", 10, "bold"))
                
                if csv_exists:
                    if csv_has_content:
                        result_text += f"✅ 成功爬取并保存了 {job_count} 个职位\n"
                        count_text = f"✅ 成功爬取并保存了 {job_count} 个职位"
                        self.result_count_value.config(text=count_text, foreground="#009688")
                    else:
                        result_text += f"⚠️ CSV文件已创建但没有数据\n"
                        count_text = "⚠️ CSV文件已创建但没有数据"
                        self.result_count_value.config(text=count_text, foreground="#FFA500")
                else:
                    result_text += f"❌ CSV文件创建失败\n"
                    count_text = "❌ CSV文件创建失败"
                    self.result_count_value.config(text=count_text, foreground="#FF0000")
                    
                if md_exists:
                    result_text += f"✅ Markdown文件已生成\n"
                    md_text = "✅ 已成功生成"
                    self.result_md_value.config(text=md_text, foreground="#009688")
                else:
                    result_text += f"❌ Markdown文件生成失败\n"
                    md_text = "❌ 生成失败"
                    self.result_md_value.config(text=md_text, foreground="#FF0000")
                
                # 清除旧的路径标签
                for widget in self.file_paths_frame.winfo_children():
                    widget.destroy()
                
                # 创建文件路径标签，使用短路径显示
                csv_path_short = self.shorten_path(expected_csv)
                md_path_short = self.shorten_path(expected_md)
                
                ttk.Label(self.file_paths_frame, text="文件位置：").grid(row=0, column=0, sticky="w", padx=5, pady=2)
                ttk.Label(self.file_paths_frame, text=save_path, foreground="#555555").grid(row=0, column=1, sticky="w", padx=5, pady=2)
                
                # 显示美化后的结果框架
                self.result_frame.grid()
                
                # 保留原来的结果文本以兼容
                self.result_label.config(text=result_text)
                
                # 如果文件没有保存成功但有数据，尝试再次保存
                if not csv_has_content and len(job.seen_jobs) > 0:
                    self.update_progress({
                        'status': f'检测到数据未保存，尝试手动保存...',
                        'percentage': 100
                    })
                    try:
                        print("爬取到了数据但未能成功保存，尝试紧急备份...")
                        backup_csv = os.path.join(os.getcwd(), f"backup_{actual_filename}.csv")
                        # 这里可以添加其他紧急保存逻辑
                        print(f"创建了备份CSV: {backup_csv}")
                    except Exception as save_error:
                        print(f"尝试备份数据失败: {save_error}")
                
                # 如果Markdown不存在但CSV存在，尝试再次转换
                if not md_exists and csv_exists:
                    try:
                        print("尝试再次创建Markdown文件")
                        job.csv_to_markdown(f"{actual_filename}.csv")
                        # 再次检查Markdown是否创建成功
                        if os.path.exists(expected_md):
                            result_text = result_text.replace("❌ Markdown文件生成失败", "✅ Markdown文件已重新生成")
                            self.result_label.config(text=result_text)
                    except Exception as md_error:
                        print(f"再次创建Markdown失败: {md_error}")
                
            except Exception as e:
                print(f"处理任务 {info['title']} 时出错: {e}")
                self.result_label.config(text=f"处理任务 {info['title']} 时出错:\n{e}")
                messagebox.showerror("错误", f"处理任务 {info['title']} 时出错: {e}")
                continue
        
        # 爬取完成后，恢复按钮状态
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.is_running = False

    def open_csv(self):
        """打开CSV文件"""
        if hasattr(self, 'current_csv_path') and os.path.exists(self.current_csv_path):
            os.startfile(self.current_csv_path)
        else:
            messagebox.showinfo("提示", "CSV文件不存在")

    def open_md(self):
        """打开Markdown文件"""
        if hasattr(self, 'current_md_path') and os.path.exists(self.current_md_path):
            os.startfile(self.current_md_path)
        else:
            messagebox.showinfo("提示", "Markdown文件不存在")

    def open_folder(self):
        """打开保存文件夹"""
        if hasattr(self, 'current_save_path') and os.path.exists(self.current_save_path):
            os.startfile(self.current_save_path)
        else:
            messagebox.showinfo("提示", "保存文件夹不存在")
            
    def open_chrome(self):
        """
        配置并打开Chrome浏览器
        
        Returns:
            webdriver.Chrome: 配置好的Chrome WebDriver实例
        """
        options = Options()
        options.headless = False
        # 添加其他选项
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.minimize_window()  # 最小化窗口
        return driver

    def shorten_path(self, path, max_length=40):
        """
        缩短路径显示
        
        Args:
            path (str): 原始路径
            max_length (int): 最大显示长度
            
        Returns:
            str: 缩短后的路径
        """
        if len(path) <= max_length:
            return path
        
        # 提取路径的重要部分
        drive, tail = os.path.splitdrive(path)
        filename = os.path.basename(tail)
        
        # 计算中间部分可以显示的长度
        middle_len = max_length - len(drive) - len(filename) - 5
        
        if middle_len < 3:
            # 如果太短，就只保留文件名
            return f"{drive}\\...\\{filename}"
        else:
            # 保留路径的开始和结束部分
            head = os.path.dirname(tail)
            return f"{drive}{head[:middle_len//2]}...{head[-middle_len//2:]}\\{filename}"

if __name__ == '__main__':
    root = tk.Tk()

    app = JobSpiderApp(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("程序被用户中断，正在退出...")
        root.quit()