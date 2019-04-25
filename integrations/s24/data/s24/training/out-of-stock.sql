use ai24;

select 
	odt.id 'odt_id', odt.ean 'odt_ean', odt.name 'odt_name', 
    category_id 'odt_category_id', category_name 'odt_category_name', 
    replaceable 'odt_replaceable', variable_weight 'odt_variable_weight',
    price 'odt_price', price_per_type 'odt_price_per_type', surcharge_fixed 'odt_surcharge_fixed', 
    odt.touched_at 'odt_touched_at',
    odt.order_id 'ord_id', ord.gdo 'ord_gdo', 
	sto.ref_id 'store_id', sto.name 'store_name', sto.area 'store_area', 
	odt.status 'odt_status'
from order_detail as odt
join ai24.order as ord on ord.id = order_id
join ai24.store as sto on ord.store_id = sto.id
where odt.status <> 'NEW' # and odt.surcharge_fixed <> 0
order by order_id desc
