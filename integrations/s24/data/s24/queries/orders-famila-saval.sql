

# alcuni ordini di famila, saval, verona
select 
	store.ref_id 'store_ref_id', store.name 'store_name', store.area 'store_area', store.province 'store_province', ord.id 'order_id', odt.id 'detail_id', 
	odt.ean 'item_ean', odt.ref_id 'item_ref_id', odt.name 'item_name',
    odt.category_id 'item_category_id', odt.category_name 'item_category_name'    
from order_detail as odt
join `order` as ord on ord.id = odt.order_id
join store on store.id = ord.store_id
where ord.status >= 500 and store.ref_id = 2769
order by ord.id desc, odt.id
