select 
	ord.id 'order_id', detail.id 'detail_id', 
    store.id 'store_id', store.name 'store_name', store.area 'store_area',
    ord.courier_id, (select count(id) from `order` t2 where t2.courier_id = ord.courier_id and t2.id <= ord.id) 'courier_orders',
    datediff(ord.created_at, courier.created_at) 'courier_days',
    detail.ref_id, detail.ean, detail.name, detail.category_id, detail.category_name,
    detail.type, detail.price, detail.variable_weight, 
    detail.status, detail.touched_at, timestamps.first_detail_picked_at, ord.paid_at, ord.delivered_at
from `order` as ord
    join order_detail as detail on detail.order_id = ord.id
    join order_timestamps as timestamps on timestamps.order_id = ord.id
    join store on store.id = ord.store_id
    join courier on courier.id = ord.courier_id
where detail.touched_at is not null
order by ord.id, detail.touched_at
