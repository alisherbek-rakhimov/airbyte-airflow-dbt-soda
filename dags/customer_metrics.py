from datetime import datetime

from airflow.decorators import dag, task
from airflow.providers.airbyte.operators.airbyte import AirbyteTriggerSyncOperator
from airflow.models.baseoperator import chain
from cosmos.airflow.task_group import DbtTaskGroup
from cosmos.config import RenderConfig
from cosmos.constants import LoadMode
from include.dbt.fraud.cosmos_config import DBT_CONFIG, DBT_PROJECT_CONFIG

AIRBYTE_JOB_ID_LOAD_CUSTOMER_TRANSACTIONS_RAW = 'fc69d10e-a799-46fe-b1b0-9abf7d5db905'
AIRBYTE_JOB_ID_LOAD_LABELED_TRANSACTIONS_RAW = '7a990e6a-72e9-414f-a721-6949a17c1b6a'
AIRBYTE_JOB_ID_RAW_TO_STAGING = '251ea9ff-0c4f-4b7a-8338-e3889cfe01b7'


@dag(
    start_date=datetime(2021, 12, 1),
    schedule_interval='@daily',
    catchup=False,
    tags=['airbyte', 'risk']
)
def customer_metrics():
    load_customer_transactions_raw = AirbyteTriggerSyncOperator(
        task_id='load_customer_transactions_raw',
        airbyte_conn_id='airbyte',
        connection_id=AIRBYTE_JOB_ID_LOAD_CUSTOMER_TRANSACTIONS_RAW
    )

    load_labeled_transactions_raw = AirbyteTriggerSyncOperator(
        task_id='load_labeled_transactions_raw',
        airbyte_conn_id='airbyte',
        connection_id=AIRBYTE_JOB_ID_LOAD_LABELED_TRANSACTIONS_RAW
    )

    write_to_staging = AirbyteTriggerSyncOperator(
        task_id='write_to_staging',
        airbyte_conn_id='airbyte',
        connection_id=AIRBYTE_JOB_ID_RAW_TO_STAGING
    )

    @task
    def airbyte_jobs_done():
        return True

    @task.external_python(python='/opt/airflow/soda_venv/bin/python')
    def audit_customer_transactions(
            scan_name='customer_transactions',
            checks_subpath='tables',
            data_source='staging'
    ):
        from include.soda.helpers import check
        check(scan_name, checks_subpath, data_source)

    @task.external_python(python='/opt/airflow/soda_venv/bin/python')
    def audit_labeled_transactions(
            scan_name='labeled_transactions',
            checks_subpath='tables',
            data_source='staging'
    ):
        from include.soda.helpers import check
        check(scan_name, checks_subpath, data_source)

    @task
    def quality_checks_done():
        return True

    publish = DbtTaskGroup(
        group_id='publish',
        project_config=DBT_PROJECT_CONFIG,
        profile_config=DBT_CONFIG,
        render_config=RenderConfig(
            load_method=LoadMode.DBT_LS,
            select=['path:models']
        )
    )

    chain(
        [load_customer_transactions_raw, load_labeled_transactions_raw, load_customer_transactions_raw, load_customer_transactions_raw],
        write_to_staging,
        airbyte_jobs_done(),
        [audit_customer_transactions(), audit_labeled_transactions()],
        quality_checks_done(),
        publish
    )

customer_metrics()
