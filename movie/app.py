from flask import Flask, render_template, url_for, request, send_file
from io import BytesIO, StringIO
import pymysql
import pandas as pd
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import datetime as dt
import platform
import base64
import math


app = Flask(__name__)


# 시각화 한글 인코딩
if platform.system() == 'Windows':
    matplotlib.rc('font', family='Malgun Gothic')
elif platform.system() == 'Darwin': # Mac
    matplotlib.rc('font', family='AppleGothic')
else: # Linux
    matplotlib.rc('font', family='NanumGothic')

# 그래프에 마이너스 표시가 되도록 변경
plt.rcParams['axes.unicode_minus'] = False


@app.route('/')
def index():
   return render_template('index.html')


@app.route('/result', methods=['GET'])
def result():
    try:
        conn = pymysql.connect(user='root', passwd='1234', db='moviedb')

        # 검색한 영화의 정보
        keyword = request.args.get('title')
        movieinfo = pd.read_sql("select * from movieinfo where title='" + keyword + "'", con = conn)
        moviereview = pd.read_sql("select review from moviereview where title ='" + keyword + "'", con = conn)

        # 검색한 영화의 개봉년도 기준 순위
        rel_year = movieinfo.loc[0, 'rel_date'].year
        df = pd.read_sql("select rel_date, title, audience from movie order by audience desc", con = conn)
        df = df[pd.to_datetime(df['rel_date']).dt.year == rel_year].reset_index(drop=True)
        movie_count = len(df)
        ranking = df[df['title'] == keyword].index[0] + 1
        ranking_by_year = df[0:10]['title']

        # 장르별 영화 순위
        ranking_by_genre = {}
        df = pd.read_sql("select genre, count(*) from moviegenre group by genre order by count(*) desc", con = conn)
        df = df[df['genre'] != '']
        df = df[df['count(*)'] >= 10]

        for genre in df['genre']:
            dff = pd.read_sql("select * from movieinfo where genre like '%"+genre+"%' order by audience desc", con = conn)
            ranking_by_genre[genre] = dff[0:10]['title']

        return render_template('result.html', movieinfo = movieinfo, moviereview = moviereview, rel_year = rel_year, movie_count = movie_count, ranking = ranking, ranking_by_year = ranking_by_year, ranking_by_genre = ranking_by_genre)
    except Exception as e:
        print('예외가 발생했습니다.', e)
        return render_template('except.html')
    finally:
        conn.close()


# 코로나에 의한 영화 매출 동향
@app.route('/graph1/')
def graph1():
    try:
        conn = pymysql.connect(user='root', passwd='1234', db='moviedb')

        df = pd.read_sql("select rel_date, sales from movieinfo", con = conn)
        df['rel_date'] = pd.to_datetime(df['rel_date']).dt.year
        stats = df.groupby('rel_date').mean()[9:22]

        # 시각화
        fig = plt.figure()
        ax = fig.add_subplot()
        ax.plot(stats.index, stats['sales'], label='평균 매출액 (단위: 100억)')
        ax.set_xticks(stats.index)
        ax.set_xlabel('연도',size = 12)
        ax.set_ylabel('평균 매출액',size = 12)
        ax.legend()
        img = BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)

        return send_file(img, mimetype='image/png')
    except Exception as e:
        print('예외가 발생했습니다.', e)
    finally:
        conn.close()


@app.route('/stats1/')
def stats1():
    return render_template("stats1.html")


# 여름에 공포 영화 수요가 진짜 많은지
@app.route('/graph2/')
def graph2():
    try:
        conn = pymysql.connect(user='root', passwd='1234', db='moviedb')

        df = pd.read_sql("select rel_date, audience from movieinfo where genre regexp '공포|스릴러'", con = conn)
        df['rel_date'] = pd.to_datetime(df['rel_date']).dt.quarter
        stats = df.groupby('rel_date').mean()

        # 시각화
        fig = plt.figure()
        ax = fig.add_subplot()
        ax.plot(stats.index, stats['audience'], label='평균 관객수 (단위: 100만명)')
        ax.set_xticks(stats.index)
        ax.set_xticklabels(['겨울', '봄', '여름', '가을'])
        ax.set_ylabel('평균 관객수',size = 12)
        ax.legend()
        img = BytesIO()
        fig.savefig(img, format='png')
        img.seek(0)

        return send_file(img, mimetype='image/png')
    except Exception as e:
        print('예외가 발생했습니다.', e)
    finally:
        conn.close()

@app.route('/stats2/')
def stats2():
    return render_template("stats2.html")


# 평점과 매출액의 관계
@app.route('/graph3/')
def graph3():
    try:
        conn = pymysql.connect(user='root', passwd='1234', db='moviedb')

        df = pd.read_sql("select sales, grade from movieinfo", con = conn)
        df = df[df['grade'] != 0]
        df['grade'] = ((df['grade']*100)//100).astype('int')

        df.groupby('grade', as_index=False).count()
        # 5점 미만의 영화 빈도가 매우 낮아 평균 매출 값이 통계적으로 무의미하다고 판단이 되어
        # 5점 미만은 산정하지 않음
        df = df[df['grade'] >= 5]
        stats = df.groupby('grade').mean()

        # 시각화
        fig = plt.figure()
        ax = fig.add_subplot()
        ax.plot(stats.index, stats['sales'], label='평균 매출액 (단위: 100억)')
        ax.set_xticks(stats.index)
        ax.set_xlabel('평점',size = 12)
        ax.set_ylabel('평균 매출액',size = 12)
        ax.legend()
        img = BytesIO()
        fig.savefig(img, format='png')
        img.seek(0)

        return send_file(img, mimetype='image/png')
    except Exception as e:
        print('예외가 발생했습니다.', e)
    finally:
        conn.close()

@app.route('/stats3/')
def stats3():
    return render_template("stats3.html")


# 상영횟수와 매출액의 관계
@app.route('/graph4/')
def graph4():
    try:
        conn = pymysql.connect(user='root', passwd='1234', db='moviedb')

        df = pd.read_sql("select play, sales from movieinfo", con = conn)
        df['play'].describe()
        df['play'] = (df['play']//10000)*10000

        df.groupby('play', as_index=False).count()
        # 12만회 이상의 상영 횟수를 가지는 영화 빈도가 매우 낮아 평균 매출 값이
        # 통계적으로 무의미하다고 판단이 되어 12만회 이상은 산정하지 않음
        df = df[df['play'] < 120000]
        stats = df.groupby('play').mean()

        # 시각화
        fig = plt.figure()
        ax = fig.subplots()
        ax.plot(stats.index, stats['sales'], label = '평균 매출액 (단위: 100억)')
        ax.set_xlabel('상영 횟수', size = 12)
        ax.set_ylabel('평균 매출액', size = 12)
        # ax.axes.yaxis.set_visible(False)
        ax.legend()
        img4 = BytesIO()
        fig.savefig(img4, format='png', dpi=100)
        img4.seek(0)

        return send_file(img4, mimetype='image/png')
    except Exception as e:
        print('예외가 발생했습니다.', e)
    finally:
        conn.close()

@app.route('/stats4/')
def stats4():
    return render_template("stats4.html")


if __name__ == '__main__':
    app.run(debug=True)
