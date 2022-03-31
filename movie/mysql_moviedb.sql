use moviedb;

create table movie(
	title VARCHAR(200) PRIMARY KEY,
    rel_date DATE,
    sales BIGINT,
    audience INT,
    play INT,
	poster VARCHAR(500),
    grade DECIMAL(3,2),
    summary TEXT
);
create table movieactor(
	id INT AUTO_INCREMENT PRIMARY KEY,
	title VARCHAR(200),
    actor VARCHAR(100)
);
create table moviegenre(
	id INT AUTO_INCREMENT PRIMARY KEY,
	title VARCHAR(200),
    genre VARCHAR(100)
);
create table moviereview(
	id INT AUTO_INCREMENT PRIMARY KEY,
	title VARCHAR(200),
    review VARCHAR(200)
);

select * from movie;
select * from movieactor;
select * from moviegenre;
select * from moviereview;

drop table movie;
drop table movieactor;
drop table moviegenre;
drop table moviereview; 


create or replace view movieinfo
as
select
	m.title,
    m.rel_date,
    m.sales,
    m.audience,
    m.play,
    m.poster,
    m.grade,
    m.summary,
    (select group_concat(actor SEPARATOR ',') actor from movieactor where title = m.title) actor,
	(select group_concat(genre SEPARATOR ',') genre from moviegenre where title = m.title) genre
from movie m;

select * from movieinfo;

drop view movieinfo;