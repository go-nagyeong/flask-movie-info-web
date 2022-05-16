from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import requests
from bs4 import BeautifulSoup
import pymysql
from datetime import datetime


# kobis 사이트에서 영화 정보 크롤링
movieinfo = []
def kobis_crawling():
    browser = webdriver.Chrome('/Users/ngkim/git/flask-movie-info-web/movie/chromedriver')
    browser.implicitly_wait(20)
    browser.get('https://www.kobis.or.kr/kobis/business/stat/boxs/findPeriodBoxOfficeList.do')

    for y in range(12, 22):
        browser.find_element(By.ID, 'sSearchFrom').clear()
        browser.switch_to.alert.accept()
        browser.find_element(By.ID, 'sSearchFrom').send_keys('20{}-01-01'.format(y))

        browser.find_element(By.ID, 'sSearchTo').clear()
        browser.switch_to.alert.accept()
        browser.find_element(By.ID, 'sSearchTo').send_keys('20{}-12-31'.format(y))

        browser.find_element(By.CLASS_NAME, 'btn_blue').send_keys(Keys.ENTER)
        soup = BeautifulSoup(browser.page_source, 'html.parser')

        index = 1
        for i in soup.select('tbody > tr'):
            title = i.select_one('td:nth-child(2)').text.strip()
            date = i.select_one('td:nth-child(3)').text.strip()
            sales = int(i.select_one('td:nth-child(4)').text.strip().replace(',', ''))
            audience = int(i.select_one('td:nth-child(7)').text.strip().replace(',', ''))
            showing = int(i.select_one('td:nth-child(10)').text.strip().replace(',', ''))

            selector = 'tbody > tr:nth-child(' + str(index) + ') a'
            browser.find_element(By.CSS_SELECTOR, selector).send_keys(Keys.ENTER)
            soup = BeautifulSoup(browser.page_source, 'html.parser')
            poster = 'https://www.kobis.or.kr' + soup.select_one('div.ovf > a')['href']
            browser.find_element(By.CSS_SELECTOR, 'div.hd_layer > a:nth-child(3)').send_keys(Keys.ENTER)

            movieinfo.append((title,date,sales,audience,showing,poster))

            index += 1

        # # 영화명
        # for i in soup.select('.ellip.per90'):
        #     title.append(i.text.strip())
        # # 개봉일
        # for i in soup.select('tr > td:nth-of-type(3)'):
        #     date.append(i.text.strip())
        # # 누적 매출액
        # for i in soup.select('tr > td:nth-of-type(6)'):
        #     sales.append(int(i.text.strip().replace(',', '')))
        # # 누적 관객 수
        # for i in soup.select('tr > td:nth-of-type(8)'):
        #     audience.append(int(i.text.strip().replace(',', '')))
        # # 상영 횟수
        # for i in soup.select('tr > td:nth-of-type(10)'):
        #     showing.append(int(i.text.strip().replace(',', '')))

    browser.close()
kobis_crawling()
len(movieinfo)

# 네이버에서 영화 평점, 줄거리 크롤링
movieinfo2 = []
def naver_crawling():
    for t in movieinfo:
        title = t[0]
        if title.count('#') > 0:
            title = title.replace('#', '%23')

        # 영화 평점
        resp = requests.get('https://search.naver.com/search.naver?sm=tab_hty.top&where=nexearch&query=영화+'+title)
        soup = BeautifulSoup(resp.text, 'html.parser')
        try: grade = float(soup.select_one('dl > div:nth-of-type(3) > dd').text)
        except: grade = 0

        # 영화 줄거리
        resp = requests.get('https://search.naver.com/search.naver?sm=tab_hty.top&where=nexearch&query=영화+'+title+'+정보')
        soup = BeautifulSoup(resp.text, 'html.parser')
        try: summary = soup.select_one('.intro_box > p').text
        except: summary = ''

        movieinfo2.append((grade,summary))
naver_crawling()
len(movieinfo2)

# 영화 정보들 하나의 배열에 합치고, 영화 중복 제거
movieinfos = []
def distinct_movieinfo_list():
    for i in range(len(movieinfo)):
        movieinfos.append(movieinfo[i] + movieinfo2[i])

    # movieinfo 영화 중복 제거
    movieinfos.sort()
    i = 0
    while i < len(movieinfos)-1:
        if movieinfos[i][0] == movieinfos[i+1][0]:
            del movieinfos[i]
            i = 0
        i += 1
distinct_movieinfo_list()
len(movieinfos)


# 다음에서 영화 출연 배우 크롤링
movieactor = []
def daum_crawling_actor():
    for t in movieinfos:
        title = t[0]
        if title.count('#') > 0:
            title = title.replace('#', '%23')

        resp = requests.get('https://search.daum.net/search?nil_suggest=btn&w=tot&DA=SBC&q=영화+'+title)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # 출연 배우
        try:
            for i in soup.select('div > dl:nth-of-type(3) a.stit'):
                movieactor.append((title, i.text))
        except:
            movieactor.append((title, ''))
daum_crawling_actor()
len(movieactor)

# 네이버에서 영화 장르, 리뷰 크롤링
moviegenre = []
moviereview = []
def naver_crawling_genre_review():
    for t in movieinfos:
        title = t[0]
        if title.count('#') > 0:
            title = title.replace('#', '%23')

        # 영화 장르
        resp = requests.get('https://search.naver.com/search.naver?sm=tab_hty.top&where=nexearch&query=영화+'+title+'+정보')
        soup = BeautifulSoup(resp.text, 'html.parser')
        try:
            genre = ''
            for i in soup.select('dl.info > div'):
                if (i.select_one('dt').text == '장르'):
                    genre = i.select_one('dd').text
                    break
            if (genre != ''):
                for i in genre.split(','):
                    moviegenre.append((title, i.strip()))
            else:
                moviegenre.append((title, ''))
        except:
            moviegenre.append((title, ''))

        # 영화 리뷰
        resp = requests.get('https://search.naver.com/search.naver?sm=tab_hty.top&where=nexearch&query=영화+'+title+'+평점')
        soup = BeautifulSoup(resp.text, 'html.parser')
        try:
            if (soup.select('p.area_p_title > strong')):
                for i in soup.select('p.area_p_title > strong'):
                    moviereview.append((title, i.text))
            else:
                moviereview.append((title, ''))
        except:
            moviereview.append((title, ''))
naver_crawling_genre_review()
len(moviegenre)
len(moviereview)

# 배우, 장르, 리뷰 정보들 중복 제거
def distinct_movieactor_genre_review_list():
    # movieactor 영화명 중복 제거
    movieactor.sort()
    i = 0
    while i < len(movieactor)-1:
        if movieactor[i][0] == movieactor[i+1][0] and movieactor[i][1] == movieactor[i+1][1]:
            del movieactor[i]
            i = 0
        i += 1

    # moviegenre 영화명 중복 제거
    moviegenre.sort()
    i = 0
    while i < len(moviegenre)-1:
        if moviegenre[i][0] == moviegenre[i+1][0] and moviegenre[i][1] == moviegenre[i+1][1]:
            del moviegenre[i]
            i = 0
        i += 1

    # moviereview 영화명 중복 제거
    moviereview.sort()
    i = 0
    while i < len(moviereview)-1:
        if moviereview[i][0] == moviereview[i+1][0] and moviereview[i][1] == moviereview[i+1][1]:
            del moviereview[i]
            i = 0
        i += 1
distinct_movieactor_genre_review_list()
len(movieactor)
len(moviegenre)
len(moviereview)

# 크롤링으로 모든 데이터들 DB에 삽입
def sql_insert():
    connect = pymysql.connect(user='root', passwd='1234', db='moviedb')
    cursor = connect.cursor()

    sql = "insert into movie(title, rel_date, sales, audience, play, poster, grade, summary) values (%s, %s, %s, %s, %s, %s, %s, %s)"
    cursor.executemany(sql, movieinfos)

    cursor.executemany("insert into movieactor(title, actor) values(%s, %s)", movieactor)
    cursor.executemany("insert into moviegenre(title, genre) values(%s, %s)", moviegenre)
    cursor.executemany("insert into moviereview(title, review) values(%s, %s)", moviereview)

    connect.commit()
    connect.close()
sql_insert()
