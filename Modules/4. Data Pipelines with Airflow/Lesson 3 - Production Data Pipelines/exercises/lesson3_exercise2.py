
import datetime
import logging

from airflow import DAG
from airflow.hooks.postgres_hook import PostgresHook

from airflow.operators.postgres_operator import PostgresOperator
from airflow.operators.python_operator import PythonOperator


def log_younger():
    redshift_hook = PostgresHook("redshift")
    records = redshift_hook.get_records("""
        SELECT birthyear FROM younger_riders ORDER BY birthyear DESC LIMIT 1
    """)
    if len(records) > 0 and len(records[0]) > 0:
        logging.info(f"Youngest rider was born in {records[0][0]}")
        
def log_oldest():
    redshift_hook = PostgresHook("redshift")
    records = redshift_hook.get_records("""
        SELECT birthyear FROM older_riders ORDER BY birthyear ASC LIMIT 1
    """)
    if len(records) > 0 and len(records[0]) > 0:
        logging.info(f"Oldest rider was born in {records[0][0]}")

dag = DAG(
    "lesson3.exercise2",
    start_date=datetime.datetime.now() - datetime.timedelta(days = 1)
)

#  Creates young riders table
young_riders = PostgresOperator(
    task_id='create_younger',
    dag=dag,
    sql="""
        BEGIN;
        DROP TABLE IF EXISTS younger_riders;
        CREATE TABLE younger_riders AS (
            SELECT * FROM trips WHERE birthyear > 2000
        );
        COMMIT;
    """,
    postgres_conn_id="redshift"
)

# Quality checks
log_young_tasks= PythonOperator(
    task_id="log_younger",
    dag=dag,
    python_callable=log_younger
)

# Create lifetime_rides
lifetime_rides = PostgresOperator(
    task_id='lifetime_rides',
    dag=dag,
    sql="""
        BEGIN;
        DROP TABLE IF EXISTS lifetime_rides;
        CREATE TABLE lifetime_rides AS (
            SELECT bikeid, COUNT(bikeid)
            FROM trips
            GROUP BY bikeid
        );
        COMMIT;
    """,
    postgres_conn_id="redshift"
)

# Create station_counts
station_counts = PostgresOperator(
    task_id='station_counts',
    dag=dag,
    sql="""
        BEGIN;
        DROP TABLE IF EXISTS city_station_counts;
        CREATE TABLE city_station_counts AS(
            SELECT city, COUNT(city)
            FROM stations
            GROUP BY city
        );
        COMMIT;
    """,
    postgres_conn_id="redshift"
)

# creates oldest riders
create_oldest_task = PostgresOperator(
    task_id="create_oldest",
    dag=dag,
    sql="""
        BEGIN;
        DROP TABLE IF EXISTS older_riders;
        CREATE TABLE older_riders AS (
            SELECT * FROM trips WHERE birthyear > 0 AND birthyear <= 1945
        );
        COMMIT;
    """,
    postgres_conn_id="redshift"
)

# Quality checks
log_oldest_tasks= PythonOperator(
    task_id="log_oldest",
    dag=dag,
    python_callable=log_oldest
)

young_riders >> log_young_tasks
log_young_tasks >> lifetime_rides
lifetime_rides >> station_counts
station_counts >> create_oldest_task
create_oldest_task >> log_oldest_tasks
