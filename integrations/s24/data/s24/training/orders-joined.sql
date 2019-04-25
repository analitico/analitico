# this query will group order, courier, customer and various timestamps
# to produce data for machine learning the total order time or the order
# category (as small, standard, huge). 
#
# issues:
# the main problem with this query is that a lot of records do not have 
# order_timestamps for the first item that was picked and the field 
# order.assigned_at seems to be often starting long before the shopper is at the store

select 
	ord.id 'order_id',  ord.amount 'order_amount', ord.volume 'order_volume', 
	ord.deliver_at_start 'order_deliver_at_start', ord.deliver_at_end 'order_deliver_at_end',
	ord.fulfillment_type 'order_fulfillment_type',
	count(odt.id) 'items_total', sum(odt.variable_weight) 'items_with_variable_weight', 
	ord.picker_id 'picker_id',
	ord.courier_id 'courier_id', courier.area 'courier_area',
	(select count(id) from s24.order where courier_id = ord.courier_id) 'courier_orders',
	datediff(ord.created_at, courier.created_at) 'courier_days',
	least(1, (select count(type) from s24.courier_vehicle where courier_id = ord.courier_id and (type = 1 or type = 3))) 'courier_has_scooter', 
	least(1, (select count(type) from s24.courier_vehicle where courier_id = ord.courier_id and type = 2)) 'courier_has_car',
	cust.id 'customer_id', cust.province 'customer_province', cust.area 'customer_area', cust.ztl 'customer_ztl', cust.lat 'customer_lat', cust.lng 'customer_lng',
	store.id 'store_id', store.name 'store_name', store.province 'store_province', store.area 'store_area', store.lat 'store_lat', store.lng 'store_lng',
	ord.store_customer_distance 'store_customer_distance', ord.store_customer_duration 'store_customer_duration',
	ord.created_at, ord.assigned_at, ord.picked_at, ord.paid_at, ord.delivered_at, min(odt.touched_at) 'first_touched_at', ots.first_detail_picked_at, min(odt.touched_at) 'touched_at',
	timestampdiff(minute, greatest(coalesce(min(odt.touched_at), 0), coalesce(ord.picked_at, 0)), ord.delivered_at) as total_min ### IMPORTANT: THIS IS THE VALUE WE ARE ESTIMATING
from s24.order as ord
	join s24.store as store on ord.store_id = store.id
	join s24.customer as cust on ord.customer_id = cust.id 
	join s24.order_detail as odt on ord.id = odt.order_id 
	join s24.order_timestamps as ots on ord.id = ots.order_id
	join s24.courier as courier on ord.courier_id = courier.id
where 
	ord.status >= 500 # only completed orders
group by ord.id
order by ord.id desc
