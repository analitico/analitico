# how many records with order_detail timestamps
select count(*)
from order_detail
where touched_at is not null;

# how many records per store?
select ord.store_id 'store_id', store.name 'store_name', count(ord.id) 'total_orders'
from `order` ord
join store on store.id = ord.store_id
where ord.status >= 500
group by ord.store_id
order by count(ord.id) desc

## vedi la storia di un singolo corriere, nota i buchi nei 'courier_orders', come mai?
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
where detail.touched_at is not null and courier_id = 101498
order by ord.id, detail.touched_at




select odt.id, odt.order_id, odt.description, odt.touched_at, ots.first_detail_picked_at
from s24.order_detail as odt
join s24.order_timestamps as ots on odt.order_id = ots.order_id
where odt.category_name is not null
and touched_at is not null
order by order_id desc, odt.id desc;


# query con detail e tempo da articolo precedente
select t1.touched_at, t1.id, t1.order_id, t1.replaceable, t1.status, t1.name, t1.type, t1.selling_type, t1.description, t1.category_id, t1.category_name, t1.touched_at,
	timestampdiff(second, (
		select touched_at from order_detail t2 where t1.order_id = t2.order_id and t2.touched_at < t1.touched_at order by t2.touched_at desc limit 1
	), t1.touched_at) as time_diff
from order_detail t1
where t1.touched_at is not null
order by t1.order_id desc, t1.touched_at desc


# numero di spese per negozio
select store.id, store.name, store.area, count(ord.id) as 'orders'
from store
left join s24.order as ord on store.id = ord.store_id
group by store.id, store.name, store.area
order by count(ord.id) desc;


SELECT `COLUMN_NAME` 
FROM `INFORMATION_SCHEMA`.`COLUMNS` 
WHERE `TABLE_SCHEMA`='ai24' 
AND `TABLE_NAME`='order_detail';