-- Joins Search Console landing pages against GA4 organic sessions and conversions,
-- so keyword performance can be judged on revenue impact instead of clicks alone.

with gsc_performance as (
  select
    page,
    query,
    date,
    sum(clicks) as clicks,
    sum(impressions) as impressions,
    avg(position) as avg_position
  from `project.raw.search_console_queries`
  group by page, query, date
),

organic_sessions as (
  select
    (select value.string_value from unnest(event_params) where key = 'page_location') as landing_page,
    date(timestamp_micros(event_timestamp)) as session_date,
    user_pseudo_id,
    (select value.int_value from unnest(event_params) where key = 'ga_session_id') as session_id
  from `project.analytics_XXXXXXXX.events_*`
  where event_name = 'session_start'
    and (select value.string_value from unnest(event_params) where key = 'medium') = 'organic'
),

organic_conversions as (
  select
    (select value.string_value from unnest(event_params) where key = 'page_location') as landing_page,
    date(timestamp_micros(event_timestamp)) as conversion_date,
    (select value.double_value from unnest(event_params) where key = 'value') as conversion_value
  from `project.analytics_XXXXXXXX.events_*`
  where event_name in ('purchase', 'generate_lead')
),

page_level_summary as (
  select
    g.page,
    g.date,
    sum(g.clicks) as total_clicks,
    sum(g.impressions) as total_impressions,
    count(distinct s.session_id) as organic_sessions,
    sum(c.conversion_value) as organic_conversion_value
  from gsc_performance g
  left join organic_sessions s
    on g.page = s.landing_page and g.date = s.session_date
  left join organic_conversions c
    on g.page = c.landing_page and g.date = c.conversion_date
  group by g.page, g.date
)

select
  page,
  date,
  total_clicks,
  total_impressions,
  organic_sessions,
  coalesce(organic_conversion_value, 0) as organic_conversion_value,
  safe_divide(coalesce(organic_conversion_value, 0), nullif(total_clicks, 0)) as value_per_click
from page_level_summary
order by organic_conversion_value desc;
