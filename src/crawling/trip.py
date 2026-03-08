from winreg import QueryInfoKey
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import time
import sys
 

import random
import os 

path = "c:/temp/chromedriver.exe"
driver = webdriver.Chrome(ChromeDriverManager().install())
url = "https://www.tripadvisor.com/Attractions-g983296-Activities-oa240-Jeju_Island.html" # 목록페이지
driver.get(url)
html = driver.page_source
soup = BeautifulSoup(html, 'html.parser')



# 하나의 관광지를 들어간 상태에서 클릭을 하여 리뷰 가져오기
def crawling(one_url, name):
    
    driver.get(one_url)

    f = open(name + '.txt', 'a', encoding="utf8")
    sys.stdout = f    
    
    time.sleep(1)
    #print(address.strip())
    while True:
        try :
            # 하나의 관광지에 있는 첫번째 페이지 리뷰들 가져오기
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            review_list = soup.find_all('div',class_='pIRBV _T KRIav')
            a = soup.find_all('div',class_='XllAv H4 _a')
            review_list.append(a)
            
            for x in review_list:
                print(x.text.strip())
                # print("\n")
                
            next_page=driver.find_element_by_xpath('//*[@id="tab-data-qa-reviews-0"]/div/div[5]/div[11]/div[1]/div/div[1]/div[2]/div').click()
            time.sleep(1)

        except:
            break
            


# 한 페이지에 있는 30개의 관광지 리스트
pagelist =[]
namelist = soup.find_all('div', class_='bUshh o csemS')
page_div = soup.find_all('div',class_='eZTON')
print(len(page_div))

# pagelist에 30개의 관광지 주소 넣기
for div in page_div:
    try:
        link = div.find('a')['href']
        pagelist.append("https://www.tripadvisor.com"+link)
    except: 
        continue
    
print(pagelist)

for i in range(0, len(pagelist)): 
    name = namelist[i].text

    # 지도에서 주소 가져오기
    # map_url = 'https://map.kakao.com/'
    # driver.get(map_url)
    # time.sleep(1)
    # qeury_text = name

    # element = driver.find_element_by_id("search.keyword.query")
    # element.send_keys(qeury_text)
    # element.send_keys('\n')

    # address = driver.find_element_by_xpath('//*[@id="info.search.place.list"]/li[1]/div[5]/div[2]/p[1]')
    # address = address.text()

    # 크롤링 하기
    crawling(pagelist[i], name)
    time.sleep(1)