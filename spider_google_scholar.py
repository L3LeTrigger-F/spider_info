import random
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import re
import xlrd
import openpyxl
from tqdm import tqdm
import pyautogui
from bs4 import BeautifulSoup
import lxml
import pandas as pd
from enum import Enum
import pyperclip
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
import os
import nltk
from nltk.corpus import stopwords
nltk.download('punkt')
nltk.download('stopwords')
 
 
class Errors(Enum):
    SUCCESS         = '成功'
    SERVER_ERROR    = '服务器错误'
 
 
class Scholar:
    def __init__(self, out_filepath) -> None:
        self.out_filepath = out_filepath
        if not os.path.exists(self.out_filepath):
            os.mkdir(self.out_filepath)
        self.driver = None
        self.results = []
 
    def start_browser(self, wait_time=10):
        # 创建ChromeOptions对象
        options = Options()
        # 启用无头模式
        # options.add_argument("--headless")
        # 启用无痕模式
        options.add_argument("--incognito")
        options.add_argument("--disable-domain-reliability")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-client-side-phishing-detection")
        options.add_argument("--no-first-run")
        options.add_argument("--use-fake-device-for-media-stream")
        options.add_argument("--autoplay-policy=user-gesture-required")
        options.add_argument("--disable-features=ScriptStreaming")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-save-password-bubble")
        options.add_argument("--mute-audio")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-webgl")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-full-form-autofill-ios")
        options.add_argument("--disable-autofill-keyboard-accessory-view[8]")
        options.add_argument("--disable-single-click-autofill")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-blink-features")
        # 禁用实验性QUIC协议
        options.add_experimental_option("excludeSwitches", ["enable-quic"])
        # 创建Chrome浏览器实例
        self.driver = webdriver.Chrome(options=options, service=Service(ChromeDriverManager().install()))
        self.driver.maximize_window()
        # 等待页面加载完成
        self.driver.implicitly_wait(wait_time)
 
    def __search_onepage(self):
        """爬取当前页面文章的的信息"""
        results = []
 
        if not self.check_element_exist(check_type='ID', value='gs_res_ccl_mid'):
            print('>> 当前页面不存在文章列表')
            return []
        gs_scl = self.driver.find_element(by=By.ID, value='gs_res_ccl_mid').find_elements(by=By.CLASS_NAME, value='gs_scl')
        for i, item in tqdm(enumerate(gs_scl)):
            gs_rt = item.find_element(by=By.CLASS_NAME, value='gs_rt')
            gs_a = item.find_element(by=By.CLASS_NAME, value='gs_a')
            gs_rt_a = gs_rt.find_element(by=By.TAG_NAME, value='a') if self.check_element_exist(check_type='TAG_NAME', value='a', source=gs_rt.get_attribute('innerHTML')) else None
            publisher_info = gs_a.text.strip().replace('\n', '')
            # 论文标题
            title = gs_rt.text.strip().replace('\n', '').split(']')[-1].strip()
            # 论文链接
            href = gs_rt_a.get_attribute('href') if gs_rt_a else ''
            # 发表年份
            year = re.findall(r'\d{4}', publisher_info)
            year = year[-1] if year else -1
            
            # print(f'[{i}] {title} => {href} => {publisher_info} => {year}')
            results.append({'title': title, 'href':href, 'year': year})
        return results
 
    def check_element_exist(self, value, check_type='CLASS_NAME', source=None) -> bool:
        """检查页面是否存在指定元素"""
        page_source = source if source else self.driver.page_source
        soup = BeautifulSoup(page_source, 'lxml')
        if check_type == 'ID':
            return len(soup.find_all(id=value)) != 0
        elif check_type == 'CLASS_NAME':
            return len(soup.find_all(class_=value)) != 0
        elif check_type == 'TAG_NAME':
            return len(soup.find_all(value)) != 0
        elif check_type == 'FULL':
            return value in page_source
        else:
            print(f'>> 检查条件[{check_type}]不对')
        return False
 
    def check_captcha(self) -> bool:
        """检查是否需要人机验证；一个是谷歌学术的、一个是谷歌搜索的"""
        return self.check_element_exist(check_type='ID', value='gs_captcha_f') or \
               self.check_element_exist(check_type='ID', value='captcha-form')
 
    def process_error(self, error: Errors) -> bool:
        """尽可能尝试解决错误"""
        success = False
        if error == Errors.SERVER_ERROR:
            pass
        
        return success
    
    def check_error(self, try_solve = True) -> Errors:
        """检查当前页面是否出错"""
        error = Errors.SUCCESS
        if self.check_element_exist(check_type='FULL', value='服务器错误'):
            error = Errors.SERVER_ERROR
        
        # 尝试解决错误
        if try_solve and error != Errors.SUCCESS:
            error = Errors.SUCCESS if self.process_error(error) else error
        return error
 
    def __scroll2bottom(self):
        # 将滚动条移动到页面的底部
        self.driver.switch_to.default_content()
        js = "var q=document.documentElement.scrollTop=100000"
        self.driver.execute_script(js)
        
    def search(self, keywords, sort_bydate=False, as_ylo='', as_yhi='', max_pages=100, delay=0):
        keywords = keywords.replace(' ', '+')
        sort_bydate = 'scisbd=1' if sort_bydate else ''
        url = f'https://scholar.google.com/scholar?{sort_bydate}&hl=zh-CN&as_sdt=0%2C5&q={keywords}&btnG=&as_ylo={as_ylo}&as_yhi={as_yhi}'
        # 打开Google Scholar网站
        self.driver.get(url)
        
        for _ in tqdm(range(1, max_pages+1), desc='搜索中'):
            while self.check_captcha():
                pyautogui.alert(title='状态异常', text='请手动完成人机验证后，点击“已完成”', button='已完成')
                self.driver.refresh()
                time.sleep(2)
            if self.check_error() != Errors.SUCCESS:
                if pyautogui.confirm(text='请检查页面出现了什么问题;\n解决后，点击“确定”将会重试;\n否则，点击“取消”提前结束脚本;', title='状态异常', buttons=['确定', '取消']) == '取消':
                    print('>> 提前结束')
                    break
                time.sleep(2)
            
            onepage = self.__search_onepage()
            if not onepage:
                print('>> 当前页为空, 重试')
                self.driver.refresh()
                time.sleep(2)
                continue
            
            self.results.extend(onepage)
            
            if not self.check_element_exist(check_type='CLASS_NAME', value='gs_ico_nav_next'):
                print('>> 全部结束')
                break
            self.__scroll2bottom()
            time.sleep(0.1)
            self.driver.find_element(by=By.CLASS_NAME, value="gs_ico_nav_next").click()
            time.sleep(delay)
        
        total_num = self.driver.find_element(by=By.ID, value='gs_ab_md').find_element(by=By.CLASS_NAME, value='gs_ab_mdw').text.strip()  # .replace('\n', '').split(',')[:-1]
        open(os.path.join(self.out_filepath, 'total_num.txt'), 'w+').write(''.join(total_num))
        
        
        return self.results
 
    def close_browser(self):
        # 关闭浏览器
        self.driver.quit()
    
    def save_file(self, filename='scholar.xlsx', nodup=False):
        unique_data = self.results
        if nodup:
            # 根据href字段进行去重
            unique_data = [dict(t) for t in {tuple(d.items()) for d in unique_data}]
        print(f'>> 去重效果：{len(self.results)} => {len(unique_data)}')
        try:
            pd.DataFrame(unique_data).dropna().reset_index(drop=True).to_excel(os.path.join(self.out_filepath, filename), index=False, encoding='utf-8')
        except Exception as e:
            if pyautogui.confirm(text=f'文件保存失败[{str(e)}]\n点击“确定”将内容复制到剪切板;\n否则, 点击“取消”直接结束脚本;', title='文件保存失败', buttons=['确定', '取消']) == '确定':
                pyperclip.copy(str(unique_data))
 
    def statistical_information(self):
        pass
 
 
class AnalyzeDraw:
    def __init__(self, out_filepath, filename='scholar.xlsx') -> None:
        self.out_filepath = out_filepath
        if not os.path.exists(self.out_filepath):
            os.mkdir(self.out_filepath)
        self.filename = filename
        self.out_filepath='/Users/lhl/Desktop/spider_cnki/Smart_mine'
        self.df = pd.read_excel(os.path.join(self.out_filepath, filename),engine='openpyxl')
    
    def draw_wordcloud(self):
        """提取title生成词云"""
        # 定义停用词集合
        english_stopwords = set(stopwords.words('english'))
        # 清洗和转换标题列
        self.df['title'] = self.df['title'].astype(str)
        # 提取英文标题并排除非英文内容
        english_titles = self.df['title'].apply(lambda x: ' '.join([word.lower() for word in nltk.word_tokenize(x) if word.isalpha() and word.lower() not in english_stopwords]))
        # 将所有英文标题合并为一个字符串
        text = ' '.join(english_titles)
        # 创建词云对象
        wc = WordCloud(width=800, height=400, background_color='white').generate(text)
        wc.to_file(os.path.join(self.out_filepath, f'{self.filename}.jpg'))
 
    def draw_wordsfrequency(self):
        # 停用词列表
        stop_words = ['a', 'an', 'and', 'or', 'in', 'on', 'for', 'with', 'the', 'using', 'based', 
                      'to', 'by', 'its', 'it', '&', 'as', 'via', 'base', 'improve', 'improved',]
        # 分词并计算词频
        word_counts = Counter(' '.join(self.df['title']).lower().split())
        # 去除停用词
        for stop_word in stop_words:
            word_counts.pop(stop_word, None)
        # 按照词频从高到低排序
        sorted_counts = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        # 提取词和频率
        words = [item[0] for item in sorted_counts]
        freqs = [item[1] for item in sorted_counts]
 
        # 创建DataFrame保存词频数据
        df_freq = pd.DataFrame({'Word': words, 'Frequency': freqs})
        # 保存词频数据到Excel文件
        df_freq.to_excel(os.path.join(self.out_filepath, 'word_frequency.xlsx'), index=False)
        
 
if __name__ == '__main__':
    keywords = input('>> 请输入搜索关键词: ').strip() or 'allintitle: Multimodal ("Graph Neural Network" OR GNN)'
    as_ylo = input('>> 请输入开始年份(留空为1900): ').strip() or '2000'
    as_yhi = input('>> 请输入结束年份(留空为不限): ').strip()
    max_pages = input('>> 请输入爬取多少页(最多为100): ').strip() or '100'
    sort_bydate = (input('>> 是否按日期排序(y/n, 默认否, 会覆盖年份): ').strip() or 'n')=='y'
 
    out_filepath = '_'.join(keywords.replace('"', '').replace(':', '').split())
    
    scholar = Scholar(out_filepath)
    scholar.start_browser(wait_time=60)
    results = scholar.search(keywords, sort_bydate, as_ylo, as_yhi, max_pages=int(max_pages), delay=random.randint(0, 0)) 
    scholar.close_browser()
    scholar.save_file(nodup=True)
    
    
    analyze = AnalyzeDraw(out_filepath)
    analyze.draw_wordcloud()
    analyze.draw_wordsfrequency()
    print('>> all done <<')

