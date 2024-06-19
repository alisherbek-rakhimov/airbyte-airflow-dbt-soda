with transaction_summary as (select ct.USER_ID,
                                    count(ct.TRANSACTION_ID)                              as total_transactions,
                                    sum(case when lt.IS_FRAUDULENT then 1 else 0 end)     as fraudulent_transactions,
                                    sum(case when not lt.IS_FRAUDULENT then 1 else 0 end) as non_fraudulent_transactions
                             from {{ ref('customer_transactions') }} ct
                                      join {{ ref('labeled_transactions') }} lt
                             group by ct.USER_ID)

select user_id,
       total_transactions,
       fraudulent_transactions,
       non_fraudulent_transactions,
       (fraudulent_transactions::float / total_transactions) * 100 risk_score
from transaction_summary