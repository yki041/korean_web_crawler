from bs4 import BeautifulSoup
from multiprocessing import Process

from tqdm import tqdm, trange
import os
import random
import time
import platform
import calendar
import requests
import re

class ArticleCrawler(object):
    def __init__(self):
        self.categories = {'정치': 100, '경제': 101, '사회': 102,
                           '생활문화': 103, '세계': 104,
                           'IT과학': 105, '오피니언': 110,
                           'politics': 100, 'economy': 101, 'society': 102,
                           'living_culture': 103, 'world': 104,
                           'IT_science': 105, 'opinion': 110}
        self.selected_categories = []
        self.date = {}  # 'start_year': 0, 'start_month': 0, 'end_year': 0, 'end_month': 0}
        self.user_operating_system = str(platform.system())

    def set_category(self, *args):
        for arg in args:
            if self.categories.get(arg) is None:
                raise KeyError
        self.selected_categories = args


    def set_date_range(self, start_year:int, start_month:int, end_year:int, end_month:int):
        kwargs = {"start_year": start_year, "start_month": start_month,
                  "end_year": end_year, "end_month": end_month}
        from datetime import date
        assert start_year <= end_year <= date.today().year
        if end_year == date.today().year:
            assert end_month <= date.today().month

        assert 1 <= start_month <= 12 and 1 <= end_month <= 12

        if end_year == start_year:
            assert end_month >= start_month
        for k, v in kwargs.items():
            self.date[k] = v

    @staticmethod
    def make_news_page_url(category_url, start_year, end_year, start_month, end_month):
        made_urls = []
        for year in range(start_year, end_year+1):
            if start_year == end_year:
                year_startmonth = start_month
                year_endmonth = end_month
            else:
                if year == start_year:
                    year_startmonth = start_month
                    year_endmonth = 12
                elif year == end_year:
                    year_startmonth = 1
                    year_endmonth = end_month
                else:
                    year_startmonth = 1
                    year_endmonth = 12

            for month in range(year_startmonth, year_endmonth+1):
                for day in range(1, calendar.monthrange(year, month)[1]+1):
                    # url per each day
                    url = "{}{}{:02d}{:02d}".format(category_url, year,
                                                    month, day)
                    # totalpage는 네이버 페이지 구조를 이용해서 page=10000으로 지정해 totalpage를 알아냄
                    # page=10000을 입력할 경우 페이지가 존재하지 않기 때문에 page=totalpage로 이동 됨 (Redirect)
                    totalpage = ArticleParser.find_news_totalpage(url+"&page=10000")
                    for page in range(1, totalpage+1):
                        made_urls.append(url+"&page="+str(page))
        return made_urls

    @staticmethod
    def get_url_data(url, max_tries=10, failed_url="failed_url.txt"):
        start_time = time.time()
        min_wait = 30
        max_wait = 90
        for ii in range(max_tries):
            try:
                return requests.get(url)
            except requests.exceptions:
                time.sleep(random.randint(min_wait*(ii+1), max_wait*(ii+1)))
        if os.path.exists(failed_url):
            mode = "a"
        else:
            mode = "w"
        with open(failed_url, mode=mode) as f:
            f.write(url+"\n")
        raise ResponseTimeout(url, max_tries, time.time() - start_time)

    def crawling(self, category_name):
        # Multi process pid
        print(category_name + " PID: " + str(os.getpid()))

        writer = Writer(category_name=category_name, date=self.date)

        # 기사 URL 형식
        url = "http://news.naver.com/main/list.nhn?mode=LSD&mid=sec&sid1=" + str(
            self.categories.get(category_name)) + "&date="

        # start_year년 start_month월 ~ end_year의 end_month 날짜까지 기사를 수집합니다.
        day_urls = self.make_news_page_url(url,
                                           start_year=self.date["start_year"],
                                           start_month=self.date["start_month"],
                                           end_year=self.date["end_year"],
                                           end_month=self.date["end_month"])
        print("[{}] urls are generated".format(category_name))
        num_news_urls = 0
        for url in tqdm(day_urls, desc="Processing each url"):
            regex = re.compile("date=(\d+)")
            news_date = regex.findall(url)[0]

            request = self.get_url_data(url)

            document = BeautifulSoup(request.content, "html.parser")

            # html - newsflash_body - type06_headline, type06
            # 각 페이지에 있는 기사들 가져오기
            post_temp = document.select('.newsflash_body .type06_headline li dl')
            post_temp.extend(document.select('.newsflash_body .type06 li dl'))

            # 각 페이지에 있는 기사들의 url 저장
            post = []
            for line in post_temp:
                post.append(line.a.get('href'))  # 해당되는 page에서 모든 기사들의 URL을 post 리스트에 넣음
            del post_temp
            num_news_urls += len(post)
            
            for content_url in tqdm(post, desc="content in {}".format(url)):
                # 기사 url
                time.sleep(0.01)

                # 기사 HTML 가져옴
                request_content = self.get_url_data(content_url)
                try:
                    document_content = BeautifulSoup(request_content.content, "html.parser")
                except:
                    continue

                try:
                    # 기사 제목 가져옴
                    tag_headline = document_content.find_all("h3",
                                                             {"id": "articleTitle"},
                                                             {"class": "tts_head"})
                    text_headline = "" # 뉴스 기사 제목 초기화
                    text_headline = text_headline + ArticleParser.clear_headline(str(tag_headline[0].find_all(text=True)))
                    if not text_headline:
                        continue

                    # 기사 본문 가져옴
                    tag_content = document_content.find_all('div', {'id': 'articleBodyContents'})
                    text_sentence = ''  # 뉴스 기사 본문 초기화
                    text_sentence = text_sentence + ArticleParser.clear_content(
                        str(tag_content[0].find_all(text=True)))
                    if not text_sentence:  # 공백일 경우 기사 제외 처리
                        continue

                    # 기사 언론사 가져옴
                    tag_company = document_content.find_all('meta', {'property': 'me2:category1'})
                    text_company = ''  # 언론사 초기화
                    text_company = text_company + str(tag_company[0].get('content'))
                    if not text_company:  # 공백일 경우 기사 제외 처리
                        continue

                    # write crawled contents
                    writer.write(*[news_date, category_name, text_company, text_headline, text_sentence, content_url])

                    del text_company, text_sentence, text_headline
                    del tag_company
                    del tag_content, tag_headline
                    del request_content, document_content

                except Exception as ex:
                    del request_content, document_content

        print("Category {}, num_of_urls={}".format(category_name, num_news_urls))
        return None
        writer.close()

    def start(self):
        for category_name in self.selected_categories:
            self.crawling(category_name)
            #proc = Process(target=self.crawling, args=(category_name,))
            #proc.start()

class ArticleParser(object):
    special_symbol = re.compile('[\{\}\[\]\/?,;:|\)*~`!^\-_+<>@\#$&▲▶◆◀■【】\\\=\(\'\"]')
    content_pattern = re.compile('본문 내용|TV플레이어| 동영상 뉴스|flash 오류를 우회하기 위한 함수 추가function  flash removeCallback|tt|앵커 멘트|xa0')

    @classmethod
    def clear_content(cls, text):
        # 기사 본문에서 필요없는 특수문자 및 본문 양식 등을 다 지움
        newline_symbol_removed_text = text.replace('\\n', '').replace('\\t', '').replace('\\r', '')
        special_symbol_removed_content = re.sub(cls.special_symbol, ' ', newline_symbol_removed_text)
        end_phrase_removed_content = re.sub(cls.content_pattern, '', special_symbol_removed_content)
        blank_removed_content = re.sub(' +', ' ', end_phrase_removed_content).lstrip()  # 공백 에러 삭제
        reversed_content = ''.join(reversed(blank_removed_content))  # 기사 내용을 reverse 한다.
        content = ''
        for i in range(0, len(blank_removed_content)):
            # reverse 된 기사 내용중, ".다"로 끝나는 경우 기사 내용이 끝난 것이기 때문에 기사 내용이 끝난 후의 광고, 기자 등의 정보는 다 지움
            if reversed_content[i:i + 2] == '.다':
                content = ''.join(reversed(reversed_content[i:]))
                break
        return content

    @classmethod
    def clear_headline(cls, text):
        # 기사 제목에서 필요없는 특수문자들을 지움
        newline_symbol_removed_text = text.replace('\\n', '').replace('\\t', '').replace('\\r', '')
        special_symbol_removed_headline = re.sub(cls.special_symbol, '', newline_symbol_removed_text)
        return special_symbol_removed_headline

    @classmethod
    def find_news_totalpage(cls, url):
        # 당일 기사 목록 전체를 알아냄
        try:
            totlapage_url = url
            request_content = requests.get(totlapage_url)
            document_content = BeautifulSoup(request_content.content, 'html.parser')
            headline_tag = document_content.find('div', {'class': 'paging'}).find('strong')
            regex = re.compile(r'<strong>(?P<num>\d+)')
            match = regex.findall(str(headline_tag))
            return int(match[0])
        except Exception:
            return 0

class Writer(object):
    def __init__(self, category_name, date, sep="\t"):
        self.user_operating_system = str(platform.system())
        self.category_name = category_name
        self.sep = sep
        self.date = date
        self.start_year = None
        self.end_year = None
        self.start_month = None
        self.end_month = None
        self.init_range()

        self.file = None
        self.init_file()

    def init_range(self):
        def convert_2digit_format(obj):
            if isinstance(obj, str):
                if len(obj) == 1:
                    obj = "0" + obj  # 7 --> 07
                else:
                    assert len(obj) == 2, print("Violate len(obj)<=2, where obj={}".format(obj))
            elif isinstance(obj, int):
                obj = "{:02d}".format(obj)
            else:
                raise ValueError("Type should be str or int, but got ({}) whose type is {}".format(obj, type(obj)))
            return obj
        def convert_4digit_format(year):
            if isinstance(year, str):
                assert len(year) == 4 and 1800 < int(year) < 2020
                return year
            elif isinstance(year, int):
                assert len(str(year)) == 4 and 1800 < year < 2020
                return str(year)
            else:
                raise ValueError("Type should be str or int, but got ({}) whose type is {}".format(year, type(year)))

        keys = ["start_month", "end_month"]
        for key in keys:
            self.__setattr__(key, convert_2digit_format(self.date[key]))
        keys = ["start_year", "end_year"]
        for key in keys:
            self.__setattr__(key, convert_4digit_format(self.date[key]))


    def init_file(self):
        fname = "_".join(["Article", self.category_name, self.start_year+self.start_month,
                          self.end_year+self.end_month])
        if self.sep == ",":
            fname += ".csv"
        elif self.sep == "\t":
            fname += ".tsv"
        else:
            raise NotImplementedError
        mode = None
        if os.path.exists(fname):
            mode = "a"
        else:
            mode = "w"

        encoding = None
        if self.user_operating_system == "Windows":
            encoding = "euc-kr"
        elif self.user_operating_system in ["Linux", "Mac"]:
            # linux or MacOS
            encoding = "utf-8"
        else:
            raise NotImplementedError

        self.file = open(fname, mode=mode, encoding=encoding)


    def get_file(self):
        return self.file

    def write(self, *args):
        assert all([isinstance(arg, str) for arg in args])
        args = [arg.replace("\t","") for arg in args]
        self.file.write(self.sep.join(args)+"\n")

    def close(self):
        self.file.close()

class ResponseTimeout(Exception):
    def __init__(self, url, tries, taken_time):
        self.message = "Couldn't get {} after {} tries with {:.2f} secs".format(url,
                                                                                tries,
                                                                                taken_time)

    def __str__(self):
        return str(self.message)

if __name__ == "__main__":
    Crawler = ArticleCrawler()
    Crawler.set_category("생활문화", "정치", "경제", "사회", "세계", "IT과학", "오피니언")
    Crawler.set_date_range(2018,1,2018,12)
    Crawler.start()

    '''
    for year in range(2018,2000,-1):
        Crawler = ArticleCrawler()
        Crawler.set_category("생활문화","정치", "경제", "사회", "세계", "IT과학", "오피니언")
        Crawler.set_date_range(year,1,year,12)
        Crawler.start()
        time.sleep(random.randint(2400,4800))
    '''
