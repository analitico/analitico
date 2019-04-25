select max(cus.province) 'provice', max(cus.area) 'area', max(cus.ztl) 'ztl', max(cus.has_subscription) 'has_subscription', cus.lat, cus.lng, count(*) 'customer_orders'
from ai24.order as ord
join ai24.customer as cus on cus.id = ord.customer_id
group by cus.lat, cus.lng
order by count(*) desc

