SELECT
    aea.member_id as member_id,
    STRING_AGG(distinct aea.member_display_name, ',') as member_names,
    SUM(aea.reward) as rewards,
    COUNT(ae.id) as total,
    COUNT(ae.id) FILTER (where ae.type = 'CHAIN') as chains,
    COUNT(ae.id) FILTER (where ae.type = 'AWAKENED') as awakeneds,
    COUNT(ae.id) FILTER (where ae.type = 'ONCE') as onces,
    COUNT(ae.id) FILTER (where ae.type = 'VEORA') as veoras

FROM activity_eventattendance aea
INNER JOIN activity_event ae on ae.id = aea.event_id
where ae.status = 'FINISHED'
group by aea.member_id
