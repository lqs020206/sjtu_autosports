from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *
from config import account
from SJTUVenueTabLists import venueTabLists
from PIL import Image, ImageEnhance, ImageFilter
import requests
import shutil
import os
import datetime
import logging
import json
import sys
import getopt
from io import BytesIO
from time import sleep
import ddddocr

captchaFileName = 'captcha.png'
currentPath = os.path.dirname(os.path.abspath(__file__))
captPath = os.path.join(currentPath, captchaFileName)
captRecordPath = os.path.join(currentPath,'captchaRecord/')
logfilePath = os.path.join(currentPath, "sport.log")


def captcha_rec(captcha: Image):
    """
    使用 ddddocr 进行本地验证码识别，添加图片预处理
    """
    try:
        print("正在识别验证码...")
        
        # 图片预处理
        # 1. 转换为灰度图
        captcha = captcha.convert('L')
        
        # 2. 增加对比度
        enhancer = ImageEnhance.Contrast(captcha)
        captcha = enhancer.enhance(2.0)
        
        # 3. 二值化处理
        threshold = 140
        table = []
        for i in range(256):
            if i < threshold:
                table.append(0)
            else:
                table.append(1)
        captcha = captcha.point(table, '1')
        
        # 保存处理后的验证码图片用于调试
        captcha.save('last_captcha_processed.png')
        
        # 初始化 ddddocr
        ocr = ddddocr.DdddOcr(show_ad=False)
        
        # 将图片转换为字节
        imgByteArr = BytesIO()
        captcha.save(imgByteArr, format='png')
        imgByteArr = imgByteArr.getvalue()
        
        # 识别验证码
        result = ocr.classification(imgByteArr)
        
        if result and len(result) == 4:  # 验证码通常是4位
            # 确保结果只包含字母和数字
            result = ''.join(c for c in result if c.isalnum())
            print(f"验证码识别结果: {result}")
            return result
        else:
            print(f"验证码识别结果异常: {result}")
            return None
            
    except Exception as e:
        print(f"验证码识别出错: {str(e)}")
        return None


class SJTUSport(object):
    def __init__(self, deltaDays=7, venue='学生服务中心', venueItem='健身房', startTime=17, sckey=None):
        print("初始化浏览器...")
        self.options = Options()
        # 调试时完全禁用 headless 模式
        # self.options.headless = True
        
        # 设置窗口大小
        self.options.add_argument("--window-size=1920,1080")
        
        # 初始化浏览器
        self.driver = webdriver.Firefox(options=self.options)
        self.wait = WebDriverWait(self.driver, 20)  # 20秒超时
        
        # 访问网站
        print("正在访问预约网站...")
        self.driver.get('https://sports.sjtu.edu.cn')
        
        self.usr = account['username']
        self.psw = account['password']
        self.targetDate = datetime.datetime.now() + datetime.timedelta(deltaDays)
        self.venue = venue
        self.venueItem = venueItem
        self.startTime = startTime
        self.sckey = sckey
        
        # 等待页面完全加载
        try:
            self.wait.until(lambda driver: driver.title == '上海交通大学体育场馆预约平台')
            print("页面加载完成")
        except TimeoutException:
            print("页面加载超时，请检查网络连接")
            raise
        logging.info("SJTUSport initialize successfully")
        print("SJTUSport initialize successfully")

    def login(self):
        try:
            print("等待页面加载...")
            # 等待并点击登录按钮
            try:
                print("尝试查找登录按钮...")
                # 使用更精确的选择器
                login_btn = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '#app #logoin button'))
                )
                print("找到登录按钮")
                login_btn.click()
                print("已点击登录按钮")
                
                # 等待跳转到 jaccount 登录页面
                print("等待跳转到 jaccount 登录页面...")
                self.wait.until(lambda driver: 'jaccount.sjtu.edu.cn' in driver.current_url)
                print("已跳转到 jaccount 登录页面")
                
                # 确保页面完全加载
                sleep(2)
                
                max_attempts = 10  # 最大重试次数
                for attempt in range(max_attempts):
                    try:
                        print(f"登录尝试 {attempt + 1}/{max_attempts}")
                        
                        # 等待用户名输入框
                        userInput = self.wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, '#input-login-user'))
                        )
                        userInput.clear()
                        userInput.send_keys(self.usr)
                        print("已输入用户名")
                        
                        # 等待密码输入框
                        passwdInput = self.wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, '#input-login-pass'))
                        )
                        passwdInput.clear()
                        passwdInput.send_keys(self.psw)
                        print("已输入密码")
                        
                        # 处理验证码
                        print("获取验证码图片...")
                        try:
                            # 等待验证码图片加载
                            captcha_element = self.wait.until(
                                EC.presence_of_element_located((By.ID, 'captcha-img'))
                            )
                            print("找到验证码图片")
                            
                            max_captcha_attempts = 3  # 每次最多尝试3次验证码识别
                            for captcha_attempt in range(max_captcha_attempts):
                                try:
                                    # 等待验证码图片完全加载
                                    sleep(1)  # 给图片加载一点时间
                                    
                                    # 截取验证码图片
                                    captcha_png = captcha_element.screenshot_as_png
                                    captcha_img = Image.open(BytesIO(captcha_png))
                                    
                                    # 识别验证码
                                    captcha_text = captcha_rec(captcha_img)
                                    if captcha_text:
                                        print(f"第 {captcha_attempt + 1} 次尝试识别成功")
                                        
                                        # 输入验证码
                                        captchaInput = self.wait.until(
                                            EC.presence_of_element_located((By.ID, 'input-login-captcha'))
                                        )
                                        captchaInput.clear()
                                        captchaInput.send_keys(captcha_text)
                                        print("已输入验证码")
                                        
                                        # 点击登录按钮
                                        try:
                                            submit_btn = self.wait.until(
                                                EC.element_to_be_clickable((By.ID, 'submit-password-button'))
                                            )
                                            print("找到登录按钮")
                                            submit_btn.click()
                                            print("已点击登录按钮")
                                        except Exception as e:
                                            print(f"点击登录按钮失败: {str(e)}")
                                            # 尝试使用 JavaScript 点击
                                            try:
                                                self.driver.execute_script("document.getElementById('submit-password-button').click();")
                                                print("通过 JavaScript 点击登录按钮")
                                            except Exception as js_e:
                                                print(f"JavaScript 点击也失败: {str(js_e)}")
                                                raise
                                        
                                        # 等待一下看是否有错误提示
                                        sleep(2)
                                        
                                        # 检查是否有验证码错误提示
                                        error_elements = self.driver.find_elements(By.CLASS_NAME, 'auth-error')
                                        if error_elements and '验证码' in error_elements[0].text:
                                            print("验证码错误，将尝试重新识别")
                                            # 点击验证码图片刷新
                                            captcha_element.click()
                                            sleep(1)  # 等待新验证码加载
                                            continue
                                        
                                        # 如果没有错误提示，说明验证码可能正确
                                        break
                                        
                                    else:
                                        print(f"第 {captcha_attempt + 1} 次验证码识别失败")
                                        if captcha_attempt < max_captcha_attempts - 1:
                                            print("点击刷新验证码")
                                            captcha_element.click()
                                            sleep(1)  # 等待新验证码加载
                                            
                                except Exception as e:
                                    print(f"处理验证码时出错: {str(e)}")
                                    if captcha_attempt < max_captcha_attempts - 1:
                                        print("将尝试重新获取验证码")
                                        captcha_element.click()
                                        sleep(1)
                                    else:
                                        raise
                            
                            else:  # 所有验证码尝试都失败
                                print("验证码识别次数超过最大限制")
                                return 0
                            
                        except TimeoutException:
                            print("等待验证码图片超时")
                            continue
                        except Exception as e:
                            print(f"处理验证码时出错: {str(e)}")
                            continue
                        
                        # 等待登录结果
                        print("等待登录结果...")
                        try:
                            # 等待重定向回体育场馆预约平台
                            self.wait.until(
                                lambda driver: 'sports.sjtu.edu.cn' in driver.current_url and 
                                '预约' in self.driver.title
                            )
                            print("登录成功!")
                            return 1
                        except TimeoutException:
                            # 检查是否有错误信息
                            error_elements = self.driver.find_elements(By.CLASS_NAME, 'auth-error')
                            if error_elements:
                                error_text = error_elements[0].text
                                if '验证码' in error_text:
                                    print("验证码错误，重试...")
                                    continue
                                elif '用户名或密码' in error_text:
                                    print("用户名或密码错误!")
                                    return 0
                        
                    except Exception as e:
                        print(f"登录过程出错: {str(e)}")
                        if attempt == max_attempts - 1:
                            return 0
                        continue
                        
                print("登录失败，已达到最大重试次数")
                return 0
                
            except Exception as e:
                print(f"查找登录按钮时出错: {str(e)}")
                print("当前页面源码:", self.driver.page_source)
                return 0
            
        except Exception as e:
            print(f"登录过程发生严重错误: {str(e)}")
            return 0

    def searchAndEnterVenue(self):
        try:
            venueInput = self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, 'el-input__inner'))
            )
            venueInput.send_keys(self.venue)
            btn = self.wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, 'el-button--default'))
            )
            btn.click()
            sleep(1)

            btn = self.wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, 'el-card__body'))
            )
            btn.click()
            sleep(1)
        except TimeoutException:
            print("等待场馆选择加载超时")
        except NoSuchElementException:
            print("未找到场馆选择元素，可能是页面结构已变更")

    def chooseVenueItemTab(self):
        try:
            print(f"尝试选择场地类型: {self.venueItem}")
            self.wait.until(
                EC.presence_of_element_located((By.ID, venueTabLists[self.venue][self.venueItem]))
            )
            btn = self.driver.find_element(By.ID, venueTabLists[self.venue][self.venueItem])
            btn.click()
            print("已选择场地类型")
        except Exception as e:
            print(f"选择场地类型失败: {str(e)}")

    def chooseDateTab(self):
        dateId = 'tab-' + self.targetDate.strftime('%Y-%m-%d')
        btn = self.driver.find_element(By.ID, dateId)
        btn.click()
        sleep(1)

    def chooseStartTime(self):
        """
        Start time ranges from 7 to 21
        """
        timeSlotId = self.startTime - 7
        chart = self.driver.find_element(By.CLASS_NAME, 'chart')
        chart.screenshot('chart.png')
        wrapper = chart.find_element(By.CLASS_NAME, 'inner-seat-wrapper')
        timeSlot = wrapper.find_elements(By.CLASS_NAME, 'clearfix')[timeSlotId]
        seats = timeSlot.find_elements(By.CLASS_NAME, 'unselected-seat')
        assert len(seats) > 0, "No seats left in " + self.venue + "-" +self.venueItem + " at " + str(self.startTime) +":00 on " + self.targetDate.strftime('%Y-%m-%d')
        seat = seats[0]
        seat.click()

    def send_notification(self, title, desp, short=None):
        """
        发送Server酱通知
        """
        if not self.sckey:
            print("未配置Server酱密钥，跳过通知发送")
            return
            
        try:
            url = f"https://sctapi.ftqq.com/{self.sckey}.send"
            data = {
                "title": title,
                "desp": desp,
                "short": short if short else None,
                "noip": 1  # 隐藏IP
            }
            
            response = requests.post(url, data=data)
            if response.status_code == 200:
                print("通知发送成功")
                result = response.json()
                if result.get("code") == 0:
                    print("Server酱推送成功")
                else:
                    print(f"Server酱推送失败: {result.get('message')}")
            else:
                print(f"通知发送失败: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"发送通知时出错: {str(e)}")

    def order(self):
        try:
            self.searchAndEnterVenue()
            self.chooseVenueItemTab()
            self.chooseDateTab()
            self.chooseStartTime()

            # confirm order
            btn = self.driver.find_element(By.CSS_SELECTOR, '.drawerStyle>.butMoney>.is-round')
            btn.click()

            # process notice
            btn = self.driver.find_element(By.CSS_SELECTOR, '.dialog-footer>.tk>.el-checkbox>.el-checkbox__input>.el-checkbox__inner')
            btn.click()
            btn = self.driver.find_element(By.CSS_SELECTOR, '.dialog-footer>div>.el-button--primary')
            btn.click()
            sleep(1)

            # pay and commit
            btn = self.driver.find_element(By.CSS_SELECTOR, '.placeAnOrder>.right>.el-button--primary')
            btn.click()

            dialog = self.driver.find_element(By.CSS_SELECTOR, '[aria-label="提示"]')
            btn = dialog.find_element(By.CSS_SELECTOR, '.dialog-footer>.el-button--primary')
            btn.click()
            
            # 预约成功后发送通知
            order_info = f"{self.venue}-{self.venueItem} at {str(self.startTime)}:00 on {self.targetDate.strftime('%Y-%m-%d')}"
            title = "场地预约成功，请及时支付！"
            desp = f"""
### 预约信息
- 场馆：{self.venue}
- 场地：{self.venueItem}
- 日期：{self.targetDate.strftime('%Y-%m-%d')}
- 时间：{str(self.startTime)}:00
            
### 注意事项
1. 请在15分钟内完成支付，否则订单将自动取消
2. 请确保账户余额充足
3. 如需取消预约，请提前操作
            """
            short = f"已预约{self.venue}{self.venueItem}，请在15分钟内支付"
            
            self.send_notification(title, desp, short)
            
            logging.info('Order committed: ' + order_info)
            print('Order committed: ' + order_info)
            return 1
        except Exception as e:
            logging.error(str(e))
            print(str(e))
            return 0

    def shutDown(self):
        self.driver.quit()


def main(argv):
    venue = '子衿街学生活动中心'
    venueItem = '健身房'
    startTime = 20
    deltaDays = 7
    try:
        opts, arg= getopt.getopt(argv,'d:hi:t:v:',['day=','help','item=','time=','venue='])
    except getopt.GetoptError:
        print('Error: sport.py -i <venue item name> -l (list venues and venue items) -t <startTime ranging from 7 to 21> -v <venue name>')
        print('   or: sport.py --item=<venue item name> --list (list venues and venue items) --time=<startTime ranging from 7 to 21> --venue=<venue name>')
    
    for opt, arg in opts:
        if opt in ('-h','--help'):
            print('sport.py -d <delta days from today ranging from 0 to 7> -i <venue item name> -t <startTime ranging from 7 to 21> -v <venue name>')
            print('or: sport.py --day=<delta days from today ranging from 0 to 7> --item=<venue item name> --time=<startTime ranging from 7 to 21> --venue=<venue name>')
            print('venue-venueItem list:')
            for key in venueTabLists.keys():
                print(key,end=': { ')
                for subkey in venueTabLists[key].keys():
                    print(subkey,end=', ')
                print('}')
            sys.exit()
        elif opt in ('-d','--day'):
            deltaDays = eval(arg)
        elif opt in ('-i','--item'):
            venueItem = arg
        elif opt in ('-t','--time'):
            startTime = eval(arg)
        elif opt in ('-v','--venue'):
            venue = arg
            
    sport = SJTUSport(startTime=startTime, venue=venue, venueItem=venueItem, deltaDays=deltaDays)
    if sport.login() == 1:
        logging.info("Login successfully")
        print("Login successfully!")
    else:
        sport.shutDown()
        os._exit(0)
    if sport.order() == 1:
        logging.info("Order successfully")
        print("Order successfully!")
    else:
        sport.shutDown()
        os._exit(0)
    sport.shutDown()

if __name__ == "__main__":
    logging.basicConfig(
        filename=logfilePath,
        level='INFO',
        format='%(asctime)s  %(filename)s : %(levelname)s  %(message)s',
        datefmt='%Y-%m-%d %A %H:%M:%S',
    )
    logging.info("=================================")
    logging.info("Log Started")
    main(sys.argv[1:])
