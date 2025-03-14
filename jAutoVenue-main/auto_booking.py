import schedule
import time
from datetime import datetime, timedelta
import logging
from sport import SJTUSport
import os
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config import account

# 设置日志
logging.basicConfig(
    filename='auto_booking.log',
    level='INFO',
    format='%(asctime)s  %(filename)s : %(levelname)s  %(message)s',
    datefmt='%Y-%m-%d %A %H:%M:%S',
)

def book_venue(max_retries=3, retry_interval=50):  # 最多重试3次，每次间隔300秒（5分钟）
    """预约下周场地"""
    print("=== 开始预约流程 ===")
    
    # 获取当前日期
    current_day = datetime.now().weekday()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"当前时间: {current_time}")
    
    # 计算距离下周相应日期的天数
    booking_days = {
        0: 7,  # 周一预约下周一
        1: 7,  # 周二预约下周二
        2: 7,  # 周三预约下周三
        4: 7,  # 周五预约下周五
    }
    
    if current_day not in booking_days:
        msg = f"今天不是预约日 (当前是周{current_day + 1})"
        logging.info(msg)
        print(msg)
        return

    for attempt in range(max_retries):
        print(f"\n=== 第 {attempt + 1} 次尝试预约 ===")
        sport = None
        try:
            delta_days = booking_days[current_day]
            target_date = (datetime.now() + timedelta(days=delta_days)).strftime("%Y-%m-%d")
            print(f"准备预约日期: {target_date}")
            
            sport = None
            try:
                print("正在初始化预约系统...")
                # sport = SJTUSport(
                #     deltaDays=delta_days,
                #     venue='子衿街学生活动中心',
                #     venueItem='桌游室',
                #     startTime=19,
                #     sckey=account['sckey']
                # )
                sport = SJTUSport(
                    deltaDays=delta_days,
                    venue='学生服务中心',
                    venueItem='学生中心健身房',
                    startTime=17,
                    sckey=account['sckey']
                )
                
                
                print("正在登录...")
                # 登录
                if sport.login() == 1:
                    logging.info("登录成功")
                    print("登录成功!")
                else:
                    msg = "登录失败，请检查账号密码是否正确"
                    logging.error(msg)
                    print(msg)
                    raise Exception(msg)
                
                print("正在搜索场馆...")
                try:
                    sport.searchAndEnterVenue()
                    print("已找到学生活动中心")
                except TimeoutException:
                    msg = "搜索场馆超时，可能是网络问题"
                    logging.error(msg)
                    print(msg)
                    raise Exception(msg)
                except NoSuchElementException:
                    msg = "未找到场馆，可能是页面结构已变更"
                    logging.error(msg)
                    print(msg)
                    raise Exception(msg)
                    
                print("正在选择场地类型...")
                try:
                    sport.chooseVenueItemTab()
                    print("已选择桌游室")
                except Exception as e:
                    msg = f"选择场地类型失败: {str(e)}"
                    logging.error(msg)
                    print(msg)
                    raise Exception(msg)
                    
                print("正在选择日期...")
                try:
                    sport.chooseDateTab()
                    print(f"已选择日期: {target_date}")
                except Exception as e:
                    msg = f"选择日期失败: {str(e)}"
                    logging.error(msg)
                    print(msg)
                    raise Exception(msg)
                    
                print("正在选择时间段...")
                try:
                    sport.chooseStartTime()
                    print("已选择17:00时间段")
                except AssertionError:
                    msg = "没有可用场地"
                    logging.error(msg)
                    print(msg)
                    raise Exception(msg)
                except Exception as e:
                    msg = f"选择时间失败: {str(e)}"
                    logging.error(msg)
                    print(msg)
                    raise Exception(msg)
                    
                print("正在提交预约...")
                # 预约
                if sport.order() == 1:
                    msg = f"预约成功! 场地: 子衿街学生活动中心桌游室, 日期: {target_date}, 时间: 17:00"
                    logging.info(msg)
                    print(msg)
                    return  # 预约成功，直接返回
                else:
                    msg = "预约失败，请检查日志获取详细信息"
                    logging.error(msg)
                    print(msg)
                    raise Exception(msg)
                    
            except Exception as e:
                raise e  # 向上传递异常，让外层处理重试逻辑
                
        except Exception as e:
            msg = f"第 {attempt + 1} 次预约尝试失败: {str(e)}"
            logging.error(msg)
            print(msg)
            
            if sport:
                sport.shutDown()
                
            if attempt < max_retries - 1:  # 如果不是最后一次尝试
                print(f"等待 {retry_interval} 秒后重试...")
                time.sleep(retry_interval)
            else:
                print("已达到最大重试次数，预约失败")
                
        finally:
            if sport:
                sport.shutDown()
    
    print("=== 预约流程结束 ===\n")

def should_run_today():
    """检查今天是否需要运行预约程序"""
    weekday = datetime.now().weekday()
    return weekday in [0, 1, 2, 4]  # 周一、二、三、五

def schedule_booking():
    """定时任务调度函数"""
    if should_run_today():
        print("今天是预约日，开始执行预约...")
        book_venue()
    else:
        print("今天不是预约日，跳过执行")

def main():
    print("自动预约服务已启动")
    print("将在每天12:00检查并执行预约")
    
    # 设置在每天12:00运行预约程序
    schedule.every().day.at("12:00").do(schedule_booking)
    
    # 设置当前时间为 11:59 进行测试
    current_time = datetime.now()
    current_time = current_time.replace(hour=11, minute=59)  # 使用 replace 方法正确设置时间
    print(f"当前时间设置为: {current_time.strftime('%H:%M')}")
    
    if (current_time.hour == 11 and current_time.minute >= 59) or \
       (current_time.hour == 12 and current_time.minute <= 5):
        if should_run_today():
            print("当前时间接近12:00，立即执行预约...")
            book_venue()
    
    logging.info("Auto booking service started")
    print("\n定时服务已启动，等待下一次执行...")
    print("预约时间：每周一、二、三、五 12:00")
    
    try:
        while True:
            # 为了测试，这里也使用设置的时间
            schedule.run_pending()
            time.sleep(30)  # 每30秒检查一次是否需要执行任务
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"\n程序发生错误: {str(e)}")
        logging.error(f"Program error: {str(e)}")
    finally:
        print("程序结束")

if __name__ == "__main__":
    main() 