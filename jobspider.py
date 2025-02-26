from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import time
import csv
import random
import urllib.parse
import os

class Job:
    """
    BOSS直聘职位爬虫类
    
    用于爬取BOSS直聘网站上指定职位的详细信息，支持多种爬取模式，
    并可保存为CSV和Markdown格式。
    """
    
    def __init__(self, name):
        """
        初始化爬虫实例
        
        Args:
            name (str): 要搜索的职位名称
        """
        self.name = name
        self.seen_jobs = set()  # 用于跟踪已经爬取的职位
        self.target_count = 0  # 目标爬取数量
        self.save_path = os.getcwd()  # 默认保存路径为当前目录
        self.progress_callback = None  # 进度回调函数
        self.consecutive_duplicates = 0  # 连续重复页面计数
        self.max_consecutive_duplicates = 3  # 最大允许连续重复页面数
        
        # 默认筛选条件
        self.city_code = '100010000'  # 默认全国
        self.salary_code = '0'  # 默认不限
        self.experience_code = '0'  # 默认不限
        self.education_code = '0'  # 默认不限
        self.job_type_code = '0'  # 默认不限（全职/兼职/实习）
        self.scale_code = '0'  # 默认不限（公司规模）
        self.finance_code = '0'  # 默认不限（融资阶段）
        self.position_code = '0'  # 默认不限（职位分类）
        self.publish_code = '0'  # 默认不限（发布时间）
        self.latest = False  # 默认不筛选最新发布
        
    def set_save_path(self, path):
        """
        设置保存路径
        
        Args:
            path (str): 爬取结果保存路径
        """
        self.save_path = path

    def set_progress_callback(self, callback):
        """
        设置进度回调函数
        
        Args:
            callback (function): 回调函数，用于更新UI进度
        """
        self.progress_callback = callback

    def set_filter_conditions(self, city_code='100010000', salary_code='0', 
                              experience_code='0', education_code='0',
                              job_type_code='0', scale_code='0', finance_code='0',
                              position_code='0', publish_code='0', latest=False):
        """
        设置筛选条件
        
        Args:
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
        self.city_code = city_code
        self.salary_code = salary_code
        self.experience_code = experience_code
        self.education_code = education_code
        self.job_type_code = job_type_code
        self.scale_code = scale_code
        self.finance_code = finance_code
        self.position_code = position_code
        self.publish_code = publish_code
        self.latest = latest

    def open_chrome(self):
        """
        配置并打开Chrome浏览器
        
        Returns:
            webdriver.Chrome: 配置好的Chrome WebDriver实例
        """
        options = Options()
        options.headless = False
        
        # 添加更多反爬虫检测的规避选项
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-infobars')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--ignore-certificate-errors')  # 忽略证书错误
        options.add_argument('--ignore-ssl-errors')  # 忽略SSL错误
        options.add_argument('--disable-web-security')  # 禁用网页安全性检查
        options.add_argument('--allow-running-insecure-content')  # 允许运行不安全内容
        options.add_argument('--disable-webgl')  # 禁用WebGL
        options.add_argument('--disable-software-rasterizer')  # 禁用软件光栅化器
        options.add_argument(f'--window-size={random.randint(1200,1600)},{random.randint(800,1000)}')
        options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        # 添加实验性选项
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        
        # 禁用日志
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # 修改 webdriver 属性
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # 设置页面加载超时
        driver.set_page_load_timeout(30)
        driver.set_script_timeout(30)
        
        return driver

    def save_to_csv(self, data, filename, mode='a'):
        """
        保存数据到CSV文件
        
        Args:
            data (list): 要保存的数据列表
            filename (str): CSV文件名
            mode (str): 文件打开模式，'a'为追加，'w'为覆盖
        """
        try:
            # 使用完整路径
            full_path = os.path.join(self.save_path, filename)
            print(f"准备保存数据到: {full_path}，模式: {mode}")
            
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(full_path)), exist_ok=True)
            
            # 确保写入UTF-8 with BOM
            if mode == 'w' or not os.path.exists(full_path):
                with open(full_path, mode, encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    if mode == 'w':
                        writer.writerow([
                            '职位名称', '薪资', '公司名称', '公司规模', '融资阶段',
                            '所属行业', '工作年限', '学历要求', '职位标签',
                            '工作地址', '职位描述', '岗位职责', '任职要求',
                            '公司福利', '面试地址'
                        ])
                        print(f"已创建CSV文件并写入表头: {full_path}")
            if data:
                with open(full_path, 'a', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(data)
                print(f"成功写入{len(data)}条数据到: {full_path}")
        except Exception as e:
            print(f"保存数据时出错: {e}")
            # 尝试使用备用方法保存
            try:
                backup_path = os.path.join(os.getcwd(), f"backup_{filename}")
                print(f"尝试保存到备用路径: {backup_path}")
                if data:
                    with open(backup_path, 'a', encoding='utf-8-sig', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerows(data)
                    print(f"成功保存到备用路径: {backup_path}")
            except Exception as backup_error:
                print(f"备用保存也失败: {backup_error}")
                
    def get_job_detail(self, driver, card):
        """
        获取职位详细信息
        
        Args:
            driver (webdriver.Chrome): Chrome WebDriver实例
            card (WebElement): 职位卡片元素
        
        Returns:
            list: 包含职位详细信息的列表，失败时返回None
        """
        try:
            # 保存主窗口句柄
            main_window = driver.current_window_handle
            
            # 获取职位链接并打开新标签
            job_link = card.find_element(By.CSS_SELECTOR, '.job-card-left').get_attribute('href')
            driver.execute_script(f"window.open('{job_link}', '_blank');")
            self.random_sleep(1, 2)
            
            # 切换到新标签
            new_window = [handle for handle in driver.window_handles if handle != main_window][0]
            driver.switch_to.window(new_window)
            
            # 等待详情页加载
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'job-detail'))
            )
            
            # 提取详细信息
            job_detail = {}
            
            # 基本信息
            job_detail['职位名称'] = self.safe_get_text(driver, '.job-detail .name')
            job_detail['薪资'] = self.safe_get_text(driver, '.job-detail .salary')
            job_detail['公司名称'] = self.safe_get_text(driver, '.company-info .name')
            
            # 公司信息
            company_tags = driver.find_elements(By.CSS_SELECTOR, '.company-info .tag-list span')
            if len(company_tags) >= 3:
                job_detail['公司规模'] = company_tags[0].text.strip()
                job_detail['融资阶段'] = company_tags[1].text.strip()
                job_detail['所属行业'] = company_tags[2].text.strip()
            else:
                job_detail['公司规模'] = job_detail['融资阶段'] = job_detail['所属行业'] = ''
            
            # 职位要求
            job_tags = driver.find_elements(By.CSS_SELECTOR, '.job-detail .tag-list span')
            if len(job_tags) >= 2:
                job_detail['工作年限'] = job_tags[0].text.strip()
                job_detail['学历要求'] = job_tags[1].text.strip()
            else:
                job_detail['工作年限'] = job_detail['学历要求'] = ''
            
            # 职位标签
            tags = driver.find_elements(By.CSS_SELECTOR, '.job-tags span')
            job_detail['职位标签'] = ' '.join([tag.text.strip() for tag in tags])
            
            # 地址信息
            job_detail['工作地址'] = self.safe_get_text(driver, '.location-address')
            
            # 职位描述
            desc_text = self.safe_get_text(driver, '.job-detail .job-sec-text')
            desc_parts = desc_text.split('\n')
            
            job_detail['职位描述'] = desc_text
            job_detail['岗位职责'] = ''
            job_detail['任职要求'] = ''
            
            # 尝试分离岗位职责和任职要求
            for part in desc_parts:
                if '岗位职责' in part or '工作职责' in part:
                    start_idx = desc_parts.index(part)
                    job_detail['岗位职责'] = '\n'.join(desc_parts[start_idx+1:])
                elif '任职要求' in part or '职位要求' in part:
                    start_idx = desc_parts.index(part)
                    job_detail['任职要求'] = '\n'.join(desc_parts[start_idx+1:])
            
            # 公司福利
            welfare_tags = driver.find_elements(By.CSS_SELECTOR, '.job-tags .tag-list span')
            job_detail['公司福利'] = ' '.join([tag.text.strip() for tag in welfare_tags])
            
            # 面试地址
            job_detail['面试地址'] = self.safe_get_text(driver, '.interview-description')
            
            # 关闭详情页并切回主页面
            driver.close()
            driver.switch_to.window(main_window)
            
            return [
                job_detail['职位名称'], job_detail['薪资'], job_detail['公司名称'],
                job_detail['公司规模'], job_detail['融资阶段'], job_detail['所属行业'],
                job_detail['工作年限'], job_detail['学历要求'], job_detail['职位标签'],
                job_detail['工作地址'], job_detail['职位描述'], job_detail['岗位职责'],
                job_detail['任职要求'], job_detail['公司福利'], job_detail['面试地址']
            ]
            
        except Exception as e:
            print(f"获取职位详情时出错: {e}")
            # 确保返回主窗口
            try:
                driver.close()
                driver.switch_to.window(main_window)
            except:
                pass
            return None

    def safe_get_text(self, driver, selector):
        """
        安全地获取元素文本
        
        Args:
            driver (webdriver.Chrome): Chrome WebDriver实例
            selector (str): CSS选择器
            
        Returns:
            str: 元素文本，找不到元素时返回空字符串
        """
        try:
            element = driver.find_element(By.CSS_SELECTOR, selector)
            return element.text.strip()
        except:
            return ''
        
    def random_sleep(self, min_time=1, max_time=3):
        """
        随机等待时间，避免被检测到爬虫行为
        
        Args:
            min_time (float): 最小等待时间(秒)
            max_time (float): 最大等待时间(秒)
        """
        time.sleep(random.uniform(min_time, max_time))
        
    def wait_and_find_element(self, driver, by, value, timeout=10, retries=3):
        """
        带重试的元素查找函数
        
        Args:
            driver (webdriver.Chrome): Chrome WebDriver实例
            by (By): 查找方式
            value (str): 查找值
            timeout (int): 每次查找的超时时间(秒)
            retries (int): 重试次数
            
        Returns:
            WebElement: 查找到的元素
            
        Raises:
            TimeoutException: 找不到元素且重试次数用完时抛出
        """
        wait = WebDriverWait(driver, timeout)
        for i in range(retries):
            try:
                return wait.until(EC.presence_of_element_located((by, value)))
            except TimeoutException:
                if i == retries - 1:
                    raise
                print(f"尝试第 {i+1} 次查找元素 {value}...")
                self.random_sleep(2, 4)

    def get_total_pages(self, driver):
        """
        获取搜索结果的总页数
        
        Args:
            driver (webdriver.Chrome): Chrome WebDriver实例
            
        Returns:
            int: 总页数，失败时返回1
        """
        try:
            # 等待页码元素加载
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.options-pages'))
            )
            
            # 获取所有页码链接
            page_links = driver.find_elements(By.CSS_SELECTOR, '.options-pages a')
            if not page_links:
                print("未找到分页链接")
                return 1
                
            # 获取最后一个数字页码
            total_pages = 1
            for link in page_links:
                try:
                    page_num = int(link.text.strip())
                    if page_num > total_pages:
                        total_pages = page_num
                except ValueError:
                    continue
            
            print(f"共有 {total_pages} 页搜索结果")
            return min(total_pages, 30)  # BOSS直聘最多显示30页
        
        except Exception as e:
            print(f"获取总页数失败: {e}")
            return 1

    def verify_page_loaded(self, driver, expected_page):
        """
        验证页面是否正确加载
        
        Args:
            driver (webdriver.Chrome): Chrome WebDriver实例
            expected_page (int): 期望的页码
            
        Returns:
            bool: 页面是否正确加载
        """
        try:
            # 等待职位卡片加载
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.job-card-wrapper'))
            )
            
            # 验证当前页码
            current_page_elem = driver.find_element(By.CSS_SELECTOR, '.options-pages .selected')
            current_page = int(current_page_elem.text.strip())
            
            if current_page != expected_page:
                print(f"页面加载验证失败：期望第{expected_page}页，实际第{current_page}页")
                return False
                
            return True
            
        except Exception as e:
            print(f"页面加载验证失败: {e}")
            return False

    def csv_to_markdown(self, csv_file):
        """
        将CSV文件转换为Markdown格式
        
        Args:
            csv_file (str): CSV文件名
        """
        try:
            # 使用完整路径
            csv_full_path = os.path.join(self.save_path, csv_file)
            md_file = csv_file.replace('.csv', '.md')
            md_full_path = os.path.join(self.save_path, md_file)
            
            print(f"准备将CSV转换为Markdown: {csv_full_path} -> {md_full_path}")
            
            if not os.path.exists(csv_full_path):
                print(f"错误: CSV文件不存在: {csv_full_path}")
                return
                
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(md_full_path)), exist_ok=True)
            
            with open(csv_full_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                headers = next(reader)  # 读取表头
                print(f"成功读取CSV文件: {csv_full_path}")
                
                # 准备markdown内容
                md_content = []
                
                # 添加标题
                md_content.append(f"# {self.name}职位信息\n")
                
                # 遍历每个职位
                row_count = 0
                rows = list(reader)  # 提前读取所有行到列表中
                for row in rows:
                    row_count += 1
                    if len(row) < 15:  # 防止索引越界
                        print(f"警告: 行 {row_count} 数据不完整，仅包含 {len(row)} 个字段")
                        continue
                        
                    md_content.append(f"## {row[0]} - {row[2]}\n")  # 职位名称和公司名称作为二级标题
                    
                    # 添加基本信息表格
                    md_content.append("### 基本信息\n")
                    md_content.append("| 项目 | 内容 |")
                    md_content.append("|------|------|")
                    md_content.append(f"| 薪资 | {row[1]} |")
                    md_content.append(f"| 公司规模 | {row[3]} |")
                    md_content.append(f"| 融资阶段 | {row[4]} |")
                    md_content.append(f"| 所属行业 | {row[5]} |")
                    md_content.append(f"| 工作年限 | {row[6]} |")
                    md_content.append(f"| 学历要求 | {row[7]} |")
                    md_content.append(f"| 工作地址 | {row[9]} |")
                    md_content.append("")
                    
                    # 添加职位标签
                    if row[8]:  # 职位标签
                        md_content.append("### 职位标签")
                        md_content.append(f"{row[8]}\n")
                    
                    # 添加职位描述
                    if row[10]:  # 职位描述
                        md_content.append("### 职位描述")
                        md_content.append(f"{row[10]}\n")
                    
                    # 添加岗位职责
                    if row[11]:  # 岗位职责
                        md_content.append("### 岗位职责")
                        md_content.append(f"{row[11]}\n")
                    
                    # 添加任职要求
                    if row[12]:  # 任职要求
                        md_content.append("### 任职要求")
                        md_content.append(f"{row[12]}\n")
                    
                    # 添加公司福利
                    if row[13]:  # 公司福利
                        md_content.append("### 公司福利")
                        md_content.append(f"{row[13]}\n")
                    
                    # 添加面试地址
                    if row[14]:  # 面试地址
                        md_content.append("### 面试地址")
                        md_content.append(f"{row[14]}\n")
                    
                    # 添加分隔线
                    md_content.append("---\n")
                
                print(f"处理了 {row_count} 条职位记录")
                
                # 如果没有职位记录，添加提示信息
                if row_count == 0:
                    md_content.append("*没有找到职位记录*\n")
                
                # 写入markdown文件
                with open(md_full_path, 'w', encoding='utf-8') as md:
                    md.write('\n'.join(md_content))
                
                print(f"已成功将数据转换为Markdown格式并保存到 {md_full_path}")
                
        except Exception as e:
            print(f"转换为Markdown格式时出错: {e}")
            # 尝试保存到备用位置
            try:
                backup_md_path = os.path.join(os.getcwd(), f"backup_{csv_file.replace('.csv', '.md')}")
                print(f"尝试将Markdown保存到备用位置: {backup_md_path}")
                with open(backup_md_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(md_content) if 'md_content' in locals() else f"# {self.name}职位信息\n\n转换失败，请检查CSV文件")
                print(f"已成功保存Markdown到备用位置: {backup_md_path}")
            except Exception as backup_error:
                print(f"备用保存Markdown也失败: {backup_error}")

    def give_me_job(self, mode, count):
        """
        开始爬取职位信息
        
        Args:
            mode (str): 爬取模式，'按页爬取'/'按数量爬取'/'全部爬取'
            count (int): 爬取页数或爬取数量
        """
        self.target_count = count  # 设置目标爬取数量
        driver = self.open_chrome()
        try:
            # 构建基础URL
            encoded_name = urllib.parse.quote(self.name)
            base_url = f"https://www.zhipin.com/web/geek/job"
            
            # 构建带有筛选条件的URL
            filter_params = []
            # 添加城市代码 (必须添加)
            filter_params.append(f"city={self.city_code}")
            
            # 添加薪资范围 (如果不是"不限")
            if self.salary_code != '0':
                filter_params.append(f"salary={self.salary_code}")
                
            # 添加工作经验 (如果不是"不限")
            if self.experience_code != '0':
                filter_params.append(f"experience={self.experience_code}")
                
            # 添加学历要求 (如果不是"不限")
            if self.education_code != '0':
                filter_params.append(f"education={self.education_code}")
                
            # 添加求职类型 (如果不是"不限")
            if self.job_type_code != '0':
                filter_params.append(f"jobType={self.job_type_code}")
                
            # 添加公司规模 (如果不是"不限")
            if self.scale_code != '0':
                filter_params.append(f"scale={self.scale_code}")
                
            # 添加融资阶段 (如果不是"不限")
            if self.finance_code != '0':
                filter_params.append(f"stage={self.finance_code}")
                
            # 添加职位分类 (如果不是"不限")
            if self.position_code != '0':
                filter_params.append(f"position={self.position_code}")
                
            # 添加发布时间 (如果不是"不限")
            if self.publish_code != '0':
                filter_params.append(f"publishTime={self.publish_code}")
                
            # 添加最新发布优先 (如果开启)
            if self.latest:
                filter_params.append("sortType=1")
            
            # 拼接URL参数
            params = "&".join(filter_params)
            
            # 访问第一页
            first_page_url = f"{base_url}?query={encoded_name}&{params}"
            print(f"搜索URL: {first_page_url}")
            driver.get(first_page_url)
            self.random_sleep(3, 5)

            # 获取总页数
            total_pages = self.get_total_pages(driver)
            print(f"准备爬取数据")
            
            # 估算每页职位数和总职位数
            estimated_jobs_per_page = 30  # BOSS直聘一页通常显示30个职位
            
            if mode == '按页爬取':
                estimated_total_jobs = min(count, total_pages) * estimated_jobs_per_page
                target_jobs = estimated_total_jobs
            elif mode == '按数量爬取':
                target_jobs = count
            else:  # 全部爬取
                estimated_total_jobs = total_pages * estimated_jobs_per_page
                target_jobs = estimated_total_jobs
            
            # 更新进度信息
            if self.progress_callback:
                self.progress_callback({
                    'status': '准备爬取',
                    'total_pages': total_pages,
                    'current_page': 0,
                    'scraped_jobs': 0,
                    'target_jobs': target_jobs, 
                    'estimated_total_jobs': target_jobs,  # 添加估计总职位数
                    'percentage': 0
                })

            csv_file = rf'{self.name}.csv'
            # 创建或清空CSV文件，并写入表头
            self.save_to_csv(None, csv_file, 'w')
            
            # 在文件名中添加筛选条件标识
            filter_info = []
            if self.city_code != '100010000':
                filter_info.append(f"城市_{self.city_code}")
            if self.salary_code != '0':
                filter_info.append(f"薪资_{self.salary_code}")
            if self.experience_code != '0':
                filter_info.append(f"经验_{self.experience_code}")
            if self.education_code != '0':
                filter_info.append(f"学历_{self.education_code}")
            if self.job_type_code != '0':
                filter_info.append(f"类型_{self.job_type_code}")
            if self.scale_code != '0':
                filter_info.append(f"规模_{self.scale_code}")
            if self.finance_code != '0':
                filter_info.append(f"融资_{self.finance_code}")
            if self.position_code != '0':
                filter_info.append(f"职位_{self.position_code}")
            if self.publish_code != '0':
                filter_info.append(f"发布_{self.publish_code}")
            if self.latest:
                filter_info.append("最新发布")
                
            if filter_info:
                csv_file = rf'{self.name}_{"_".join(filter_info)}.csv'
                # 重新创建有筛选条件的CSV文件
                self.save_to_csv(None, csv_file, 'w')

            consecutive_duplicates = 0
            max_consecutive_duplicates = 3

            if mode == '按页爬取':
                # 限制爬取页数
                pages_to_scrape = min(count, total_pages)
                print(f"将爬取 {pages_to_scrape} 页数据")
                total_saved_jobs = 0
                for page in range(1, pages_to_scrape + 1):
                    jobs_on_page = self.scrape_page(driver, page, csv_file, encoded_name, base_url, total_pages, is_page_mode=True, target_jobs=target_jobs, params=params)
                    total_saved_jobs += jobs_on_page
                    if jobs_on_page == 0:  # 如果这一页没爬到数据，考虑停止
                        consecutive_duplicates += 1
                        if consecutive_duplicates >= max_consecutive_duplicates:
                            print("连续多页都没有数据，停止爬取")
                            break
                    else:
                        consecutive_duplicates = 0
                print(f"按页爬取完成，共获取 {total_saved_jobs} 个职位")
            elif mode == '全部爬取':
                # 爬取所有页面的所有职位
                print(f"将爬取所有页面的所有职位，共 {total_pages} 页")
                for page in range(1, total_pages + 1):
                    if not self.scrape_page(driver, page, csv_file, encoded_name, base_url, total_pages, target_jobs=target_jobs, params=params):
                        break
            else:  # 按数量爬取
                print(f"将爬取 {count} 个职位")
                for page in range(1, total_pages + 1):
                    if len(self.seen_jobs) >= count:
                        print(f"已达到目标数量: {count}")
                        # 更新最终进度
                        if self.progress_callback:
                            self.progress_callback({
                                'status': '爬取完成',
                                'total_pages': total_pages,
                                'current_page': page,
                                'scraped_jobs': len(self.seen_jobs),
                                'target_jobs': self.target_count,
                                'percentage': 100
                            })
                        break
                    if not self.scrape_page(driver, page, csv_file, encoded_name, base_url, total_pages, target_jobs=target_jobs, params=params):
                        break

            print(f"\n爬取完成！共获取了 {len(self.seen_jobs)} 个不重复的职位详情")
            # 确保进度显示100%
            if self.progress_callback:
                self.progress_callback({
                    'status': '爬取完成',
                    'total_pages': total_pages,
                    'current_page': total_pages,
                    'scraped_jobs': len(self.seen_jobs),
                    'target_jobs': target_jobs if len(self.seen_jobs) < target_jobs else len(self.seen_jobs),
                    'percentage': 100
                })
            driver.quit()
            
            # 确保数据已保存
            print(f"最终检查CSV文件: {os.path.join(self.save_path, csv_file)}")
            try:
                with open(os.path.join(self.save_path, csv_file), 'r', encoding='utf-8-sig') as f:
                    reader = csv.reader(f)
                    headers = next(reader)  # 跳过表头
                    row_count = sum(1 for _ in reader)
                    print(f"CSV文件中包含 {row_count} 条职位记录")
                    
                    # 如果CSV为空，尝试重新保存一次
                    if row_count == 0 and len(self.seen_jobs) > 0:
                        print("警告: CSV文件为空但已爬取数据，尝试重新保存...")
                        # 这里可以添加紧急保存逻辑
            except Exception as e:
                print(f"检查CSV文件时出错: {e}")
            
            # 将CSV转换为Markdown格式
            self.csv_to_markdown(csv_file)
            
        except Exception as e:
            print(f"爬取失败: {e}")
            if self.progress_callback:
                self.progress_callback({
                    'status': f'爬取失败: {e}',
                    'percentage': 0
                })
            driver.quit()

    def scrape_page(self, driver, page, csv_file, encoded_name, base_url, total_pages, is_page_mode=False, target_jobs=0, params=""):
        """
        爬取单个页面的数据
        
        Args:
            driver (webdriver.Chrome): Chrome WebDriver实例
            page (int): 页码
            csv_file (str): CSV文件名
            encoded_name (str): URL编码后的职位名称
            base_url (str): 基础URL
            total_pages (int): 总页数
            is_page_mode (bool): 是否为按页爬取模式
            target_jobs (int): 目标职位数
            params (str): URL参数字符串
            
        Returns:
            int/bool: 按页模式下返回爬取的职位数量，非按页模式下返回是否继续爬取
        """
        try:
            # 构建完整的URL
            page_url = f"{base_url}?query={encoded_name}&{params}&page={page}"
            print(f"\n正在访问第 {page} 页: {page_url}")
            
            # 更新进度状态为正在访问页面
            if self.progress_callback:
                # 使用职位数而不是页数计算进度
                percentage = min(100, int((len(self.seen_jobs) / target_jobs) * 100) if target_jobs > 0 else 0)
                
                self.progress_callback({
                    'status': f'正在爬取第 {page}/{total_pages} 页',
                    'total_pages': total_pages,
                    'current_page': page,
                    'scraped_jobs': len(self.seen_jobs),
                    'target_jobs': target_jobs,
                    'percentage': percentage
                })
            
            # 访问页面
            driver.get(page_url)
            self.random_sleep(3, 5)
            
            # 验证页面是否正确加载
            retry_count = 0
            while retry_count < 3:
                if self.verify_page_loaded(driver, page):
                    break
                retry_count += 1
                # 更新进度状态为重试加载页面
                if self.progress_callback:
                    percentage = min(100, int((len(self.seen_jobs) / target_jobs) * 100) if target_jobs > 0 else 0)
                    self.progress_callback({
                        'status': f'第 {retry_count} 次重试加载第 {page}/{total_pages} 页',
                        'total_pages': total_pages,
                        'current_page': page,
                        'scraped_jobs': len(self.seen_jobs),
                        'target_jobs': target_jobs,
                        'percentage': percentage
                    })
                if retry_count < 3:
                    print(f"第 {retry_count} 次重试加载页面...")
                    driver.refresh()
                    self.random_sleep(3, 5)
            
            if retry_count == 3:
                print(f"页面 {page} 加载失败，停止爬取")
                if self.progress_callback:
                    percentage = min(100, int((len(self.seen_jobs) / target_jobs) * 100) if target_jobs > 0 else 0)
                    self.progress_callback({
                        'status': f'页面 {page}/{total_pages} 加载失败',
                        'total_pages': total_pages,
                        'current_page': page,
                        'scraped_jobs': len(self.seen_jobs),
                        'target_jobs': target_jobs,
                        'percentage': percentage
                    })
                return 0 if is_page_mode else False

            # 随机滚动
            for _ in range(3):
                scroll_height = random.randint(300, 700)
                driver.execute_script(f"window.scrollBy(0, {scroll_height});")
                self.random_sleep(0.5, 1.5)
            
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            self.random_sleep(2, 4)

            # 获取职位卡片
            job_cards = driver.find_elements(By.CSS_SELECTOR, '.job-card-wrapper')

            if not job_cards:
                print(f"第 {page} 页没有找到职位，尝试重新加载")
                if self.progress_callback:
                    percentage = min(100, int((len(self.seen_jobs) / target_jobs) * 100) if target_jobs > 0 else 0)
                    self.progress_callback({
                        'status': f'第 {page}/{total_pages} 页没有找到职位，正在重试',
                        'total_pages': total_pages,
                        'current_page': page,
                        'scraped_jobs': len(self.seen_jobs),
                        'target_jobs': target_jobs,
                        'percentage': percentage
                    })
                driver.refresh()
                self.random_sleep(3, 5)
                job_cards = driver.find_elements(By.CSS_SELECTOR, '.job-card-wrapper')
                if not job_cards:
                    print("重试后仍未找到职位，停止爬取")
                    if self.progress_callback:
                        percentage = min(100, int((len(self.seen_jobs) / target_jobs) * 100) if target_jobs > 0 else 0)
                        self.progress_callback({
                            'status': f'重试后第 {page}/{total_pages} 页仍未找到职位',
                            'total_pages': total_pages,
                            'current_page': page,
                            'scraped_jobs': len(self.seen_jobs),
                            'target_jobs': target_jobs,
                            'percentage': percentage
                        })
                    return 0 if is_page_mode else False

            # 更新进度状态为正在解析职位
            if self.progress_callback:
                percentage = min(100, int((len(self.seen_jobs) / target_jobs) * 100) if target_jobs > 0 else 0)
                self.progress_callback({
                    'status': f'正在解析第 {page}/{total_pages} 页的 {len(job_cards)} 个职位',
                    'total_pages': total_pages,
                    'current_page': page,
                    'scraped_jobs': len(self.seen_jobs),
                    'target_jobs': target_jobs,
                    'job_cards_on_page': len(job_cards),
                    'percentage': percentage
                })

            new_data_found = False
            new_rows = []
            
            job_card_counter = 0
            for card in job_cards:
                job_card_counter += 1
                try:
                    job_title = card.find_element(By.CSS_SELECTOR, '.job-title').text.strip()
                    company = card.find_element(By.CSS_SELECTOR, '.company-name').text.strip()
                    job_key = f"{job_title}_{company}"
                    
                    # 仅在控制台输出当前处理的职位信息，不更新UI进度
                    print(f"正在处理第 {page}/{total_pages} 页的第 {job_card_counter}/{len(job_cards)} 个职位: {job_title}")
                    
                    if job_key not in self.seen_jobs:
                        self.seen_jobs.add(job_key)
                        job_detail = self.get_job_detail(driver, card)
                        if job_detail:
                            new_data_found = True
                            new_rows.append(job_detail)
                            print(f"成功获取职位详情: {job_title}")
                            
                            # 每获取一个新职位就更新进度
                            if self.progress_callback:
                                # 直接使用已爬取职位数/目标职位数计算进度百分比
                                percentage = min(100, int((len(self.seen_jobs) / target_jobs) * 100) if target_jobs > 0 else 0)
                                self.progress_callback({
                                    'status': f'已获取 {len(self.seen_jobs)} 个职位信息 (第 {page}/{total_pages} 页)',
                                    'total_pages': total_pages,
                                    'current_page': page,
                                    'scraped_jobs': len(self.seen_jobs),
                                    'target_jobs': target_jobs,
                                    'percentage': percentage
                                })
                            
                            # 在按页爬取模式下，不检查职位数量限制
                            if not is_page_mode and len(self.seen_jobs) >= self.target_count:
                                print(f"已达到目标数量: {self.target_count}")
                                # 保存爬取到的最后一批数据
                                if new_rows:
                                    self.save_to_csv(new_rows, csv_file)
                                    print(f"保存最后一批数据，共 {len(new_rows)} 条")
                                return 0 if is_page_mode else False
                    
                except Exception as e:
                    print(f"处理职位卡片时出错: {e}")
                    continue

            if new_rows:
                self.save_to_csv(new_rows, csv_file)
                print(f"第 {page} 页爬取完成，获取并保存了 {len(new_rows)} 个职位详情")
                # 更新进度状态为页面爬取完成
                if self.progress_callback:
                    percentage = min(100, int((len(self.seen_jobs) / target_jobs) * 100) if target_jobs > 0 else 0)
                    self.progress_callback({
                        'status': f'第 {page}/{total_pages} 页完成，本页获取 {len(new_rows)} 个职位，总计 {len(self.seen_jobs)} 个',
                        'total_pages': total_pages,
                        'current_page': page,
                        'scraped_jobs': len(self.seen_jobs),
                        'new_jobs': len(new_rows),
                        'target_jobs': target_jobs,
                        'percentage': percentage
                    })
                # 如果这是按页爬取，返回这一页获取到的职位数
                if is_page_mode:
                    return len(new_rows)

            if not is_page_mode and not new_data_found:
                self.consecutive_duplicates += 1
                print(f"第 {page} 页没有新数据")
                if self.consecutive_duplicates >= self.max_consecutive_duplicates:
                    print("连续多页都是重复数据，停止爬取")
                    # 更新进度状态为重复数据停止爬取
                    if self.progress_callback:
                        percentage = min(100, int((len(self.seen_jobs) / target_jobs) * 100) if target_jobs > 0 else 0)
                        self.progress_callback({
                            'status': f'连续多页都是重复数据，停止爬取',
                            'total_pages': total_pages,
                            'current_page': page,
                            'scraped_jobs': len(self.seen_jobs),
                            'target_jobs': self.target_count,
                            'percentage': percentage
                        })
                    return 0 if is_page_mode else False
            else:
                self.consecutive_duplicates = 0

            # 对于按页爬取，返回0表示这一页没有新数据
            return 0 if is_page_mode and not new_data_found else len(new_rows) if is_page_mode else True

        except Exception as e:
            print(f'页面处理出错 {e}：第 {page} 页')
            # 更新进度状态为页面处理出错
            if self.progress_callback:
                percentage = min(100, int((len(self.seen_jobs) / target_jobs) * 100) if target_jobs > 0 else 0)
                self.progress_callback({
                    'status': f'页面处理出错 {e}：第 {page}/{total_pages} 页',
                    'total_pages': total_pages,
                    'current_page': page,
                    'scraped_jobs': len(self.seen_jobs),
                    'target_jobs': target_jobs,
                    'percentage': percentage
                })
            return 0 if is_page_mode else False

if __name__=='__main__':
    job_name = input("请输入要搜索的职位（例如：数据分析师）：")
    print(f"\n开始搜索'{job_name}'相关的职位...")
    job = Job(job_name)
    job.give_me_job('全部爬取', 999)
    print(f"\n搜索完成！结果已保存到 {job_name}.csv")