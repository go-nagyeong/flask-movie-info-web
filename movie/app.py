from flask import Flask, render_template, redirect, url_for, request, send_file
from io import BytesIO
import pymysql
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import datetime as dt
import platform
import json

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
    conn = pymysql.connect(user='root', passwd='1234', db='moviedb')
    # 영화명 자동 완성 데이터
    movie_frame = pd.read_sql("SELECT id, title, poster FROM movie_tb", con = conn)
    movie_list = movie_frame['title'].values.tolist()
    movie_id = dict(zip(movie_frame.title, movie_frame.id))
    movie_poster = dict(zip(movie_frame.title, movie_frame.poster))
    return render_template('index.html', movie_list = json.dumps(movie_list), movie_id = movie_id, movie_poster = movie_poster)


@app.route('/result', methods=['GET'])
def result():
    try:
        conn = pymysql.connect(user='root', passwd='1234', db='moviedb')
    except:
        return redirect(url_for('_except', err = 'DB 연결 실패'))
    else:
        try:
            # 영화명 자동 완성 데이터
            movie_frame = pd.read_sql("SELECT id, title, poster FROM movie_tb", con = conn)
            movie_list = movie_frame['title'].values.tolist()
            movie_id = dict(zip(movie_frame.title, movie_frame.id))
            movie_poster = dict(zip(movie_frame.title, movie_frame.poster))

            # 검색한 영화의 정보
            id = request.args.get('selected_movie')

            movie_info = pd.read_sql("SELECT * FROM movie_tb WHERE id = {}".format(id), con = conn)
            movie_info = movie_info.to_dict('records')[0]

            for i in ['country', 'genre', 'director', 'actor']:
                movie_info2 = pd.read_sql("SELECT a.{0} FROM {0}_tb a JOIN movie_{0}_tb b ON a.id = b.{0}_id WHERE b.movie_id = {1}".format(i, id), con = conn)
                movie_info[i] = ', '.join(movie_info2[i].values.tolist())

            movie_review = pd.read_sql("SELECT review FROM movie_review_tb WHERE movie_id = {}".format(id), con = conn)
            movie_info['reviews'] = movie_review['review'].values.tolist()

            # 검색한 영화의 개봉년도 기준 순위
            # (rel_year 기준, 영화 movie_count개 중 ranking위 입니다.)
            rel_year = movie_info['rel_date'].year
            ranking_by_rel_year = pd.read_sql("SELECT id, title, RANK() OVER (ORDER BY audience DESC) ranking FROM movie_tb WHERE year(rel_date) = {}".format(rel_year), con = conn)
            movie_count = len(ranking_by_rel_year)
            ranking = int(ranking_by_rel_year[ranking_by_rel_year['id'] == int(id)]['ranking'])
            
            # 개봉년도 기준 영화 1~10위 순위표를 위한 데이터
            if ranking <= 10:
                ranking_by_rel_year = ranking_by_rel_year[:10]
            else:
                search_movie = ranking_by_rel_year[ranking_by_rel_year['id'] == int(id)]
                ranking_by_rel_year = ranking_by_rel_year[:10]
                ranking_by_rel_year = ranking_by_rel_year.append(search_movie)

            # 장르별 전체 영화 순위
            # 순위를 매길 만큼 영화 개수가 많지 않은 장르는 제외
            genres = pd.read_sql("SELECT genre_id, count(*) count FROM movie_genre_tb GROUP BY genre_id HAVING count > 20 ORDER BY count DESC", con = conn)

            ranking_by_genre = {}
            for i in genres['genre_id']:
                rank = pd.read_sql("SELECT id, title, RANK() OVER (ORDER BY audience DESC) ranking FROM movie_tb m JOIN movie_genre_tb g ON g.movie_id = m.id WHERE g.genre_id = {}".format(i), con = conn)
                genre = pd.read_sql("SELECT genre FROM genre_tb WHERE id = {}".format(i), con = conn)
                genre = genre['genre'].to_string(index=False)
                ranking_by_genre[genre] = rank[0:10]

            return render_template('result.html', 
                movie_list = json.dumps(movie_list),
                movie_id = movie_id,
                movie_poster = movie_poster,
                movie_info = movie_info,
                rel_year = rel_year,
                movie_count = movie_count,
                ranking = ranking,
                ranking_by_rel_year = ranking_by_rel_year,
                ranking_by_genre = ranking_by_genre
            )
        except Exception as e:
            return redirect(url_for('_except', err = e))
        finally:
            conn.close()

@app.route('/except/')
def _except():
    err = request.args.get('err')
    return render_template('except.html', err = err)


# 코로나에 의한 영화 매출 동향
@app.route('/graph1/')
def graph1():
    try:
        conn = pymysql.connect(user='root', passwd='1234', db='moviedb')

        sql = """
        SELECT rel_date, sales
        FROM movie_tb
        """
        df = pd.read_sql(sql, con = conn)
        df['rel_date'] = pd.to_datetime(df['rel_date']).dt.year
        stats = df.groupby('rel_date').mean()

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

        sql = """
        SELECT m.rel_date, m.audience
        FROM movie_tb m JOIN movie_genre_tb g
        ON m.id = g.movie_id
        WHERE g.genre_id IN (8,16)
        """
        df = pd.read_sql(sql, con = conn)
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

        sql = """
        SELECT grade, sales
        FROM movie_tb
        """
        df = pd.read_sql(sql, con = conn)
        df = df[~df['grade'].isna()]
        df['grade'] = ((df['grade']*100)//100).astype('int')

        # 3점 미만과 10점은 영화 빈도가 매우 낮아 평균 매출 값이 통계적으로 무의미하다고 판단이 되어 산정하지 않음
        df.groupby('grade', as_index=False).count()
        df = df[(df['grade'] >= 3) & (df['grade'] <= 9)]

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

        sql = """
        SELECT play, sales
        FROM movie_tb
        """
        df = pd.read_sql(sql, con = conn)

        # 기초통계량 확인해서 범위 묶기
        df['play'].describe()
        df['play'] = (df['play']//5000)*5000

        # 빈도가 매우 낮아 평균 매출 값이 통계적으로 무의미하다고 판단이 되는 범위는 제거
        df.groupby('play', as_index=False).count()
        df = df[df['play'] < 50000]
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
    app.run(port=5001, debug=True)
