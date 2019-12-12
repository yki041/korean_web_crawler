import pickle
from selenium import webdriver
from bs4 import BeautifulSoup as bs
import time
import os
separator1 = "【"  # ord("【") == 12304, "【" == chr(ord("【"))
seperator2 = "】"  # ord("】") == 12305, "】" == chr(ord("】"))
DATA_DIR = "court_cases"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
"""
대법원 판례 예시
-【판시사항】
-【결정요지】 or 【판결요지】
-【참조조문】(text가 hierarchy를 잘 반영하지 못함.)
-【참조판례】(optional)
-【전문】
    -【피고인】
    -【신청인】
    -【변호인】
    -【재정대상사건】
    -【주문】
    -【이유】
-ex 대법원)대법원장   양승태(재판장)        대법관   이인복 이상훈 박병대 김용덕 박보영 김창석 김신 김소영 조희대 권순일(주심) 박상옥 이기택
-ex 대법원) 대법관   이동원(재판장) 조희대 김재형(주심) 민유숙
-ex 서울고등법원) 판사   홍일표(재판장) 임준호 박형명
-ex 서울가정법원) 판사   이은애(재판장) 이동희 박상인
-ex 서울중앙지방법원) 판사   노태악(재판장) 김정석 권상표
"""
chrome_options = webdriver.ChromeOptions()
#chrome_options.add_argument("--headless")
#chrome_options.add_argument("--no-sandbox")
#driver = webdriver.Chrome('/home/alberto/court_case_crawler/chromedriver',
driver = webdriver.Chrome('C:/Users/ddd/Downloads/chromedriver_win32/chromedriver',
                          chrome_options=chrome_options)
driver.get('https://glaw.scourt.go.kr/wsjo/panre/sjo050.do#1541405087832')  # 판례검색 사이트 접속
driver.find_element_by_name('srchw').send_keys('법원')  # 키워드 입력 "교통"
driver.find_element_by_id('srch_img').click()  # 검색버튼 클릭
driver.find_element_by_name("sort_sngo_day").click()
for j in range(1471, 2180):  # 1페이지부터 2179페이지까지 반복
    driver.find_element_by_xpath('//*[@id="tabwrap"]/div/div/div[1]/div[3]/div/fieldset/input').clear()
    driver.find_element_by_xpath('//*[@id="tabwrap"]/div/div/div[1]/div[3]/div/fieldset/input').send_keys(j)
    driver.find_element_by_xpath('//*[@id="tabwrap"]/div/div/div[1]/div[3]/div/fieldset/a/img').click()
    #driver.find_element_by_name("btn_move").click()

    for i in range(0, 20):  # 판례정보 읽기
        fname = "{}_page_{}_case.pk".format(j, i)
        x = str(i)
        driver.find_element_by_xpath('//*[@id="ln' + x + '"]/td[2]/dl/dt/a[1]/strong /strong').click()
        driver.switch_to.window(driver.window_handles[-1])  # 클릭해서 열린페이지로 이동

        subpage = driver.page_source
        for _ in range(10):
            try:
                soup = bs(subpage, 'html.parser')  # html 파싱
                result = {}
                infos = soup.find_all('div', class_='con_area_02')
                #for s in infos:  # 판례 내용을 읽어서 txt파일에 저장
                #    texts = [x for x in s.text.split("\xa0") if len(x) > 0]
                #    #file.write(s.text.replace("\xa0", "\t"))  # xa0 문자 처리
                result["본문"] = [info.text for info in infos]
                chjpanre = soup.find_all("p", class_="areaChjPanre")  #참조판례
                #print("len(참조판례):", len(chjpanre))
                #for part in chjpanre[1:]:
                #    print(part.text,)
                result["참조판례"] = [info.text for info in chjpanre[1:]]
                """
                text cleaning is required.
                [2]대법원 1997. 7. 22. 선고 96도2153 판결(공1997하, 2590)(변경)
                , 대법원 2010. 2. 26.자 2010모24 결정(변경)
                [3]대법원 2000. 2. 11. 선고 99도2983 판결
                """
                chjjomun = soup.find_all("p", class_="areaChjJomun")  #참조조문
                #print("len(참조조문):", len(chjjomun))
                #for part in chjjomun[1:]:
                #    print(part.text,)
                result["참조조문"] = [info.text for info in chjjomun[1:]]
                bmunchjpanre = soup.find_all("p", class_="areaBmunChjPanre")  #본문참조판례
                #print("len(본문참조판례):", len(bmunchjpanre))
                #for part in bmunchjpanre[1:]:
                #    print(part.text,)
                result["본문참조판례"] = [info.text for info in bmunchjpanre[1:]]
                bmunchjjomun = soup.find_all("p", class_="areaBmunChjJomun")  #본문참조조문
                #print("len(본문참조조문):", len(bmunchjjomun))
                #for part in bmunchjjomun[1:]:
                #    print(part.text,)
                result["본문참조조문"] = [info.text for info in bmunchjjomun[1:]]
                wsimpanre = soup.find_all("p", class_="areaWsimPan")  #원심판결
                #print("len(원심판결):", len(wsimpanre))
                #for part in wsimpanre[1:]:
                #    print(part.text,)
                result["원심판결"] = [info.text for info in wsimpanre[1:]]
                dasudpanre = soup.find_all("p", class_="areaDasudPanre")  #다수당사자판례
                #print("len(다수당사자판례):", len(dasudpanre))
                #for part in dasudpanre[1:]:
                #    print(part.text,)
                result["다수당사자판례"] = [info.text for info in dasudpanre[1:]]
                hsimpanre = soup.find_all("p", class_="areaHsimPan")  #상급심판결
                #print("len(상급심판결):", len(hsimpanre))
                #for part in hsimpanre[1:]:
                #    print(part.text,)
                result["상급심판결"] = [info.text for info in hsimpanre[1:]]
                ttleumpanre = soup.find_all("p", class_="areaTtleumPan")  #따름판례
                #print("len(따름판례):", len(ttleumpanre))
                #for part in ttleumpanre[1:]:
                #    print(part.text,)
                result["따름판례"] = [info.text for info in ttleumpanre[1:]]
                psuk = soup.find_all("p", class_="areaPsuk")  #평석
                #print("len(평석):", len(psuk))
                #for part in psuk[1:]:
                #    print(part.text,)
                result["평석"] = [info.text for info in psuk[1:]]
                relmhn = soup.find_all("p", class_="areaRelMhn")  #관련문헌
                #print("len(관련문헌):", len(relmhn))
                #for part in relmhn[1:]:
                #    print(part.text,)
                result["관련문헌"] = [info.text for info in relmhn[1:]]
                with open(os.path.join(DATA_DIR,fname), "wb") as f:
                    pickle.dump(result, f)
                break
            except:
                time.sleep(30)

        driver.close()
        driver.switch_to.window(driver.window_handles[0])  # 메인페이지로 돌아가기
        time.sleep(0.5)
    time.sleep(0.5)