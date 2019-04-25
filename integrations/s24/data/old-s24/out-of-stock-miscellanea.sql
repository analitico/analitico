use ai24;

select * 
from order_detail
order by order_id desc

# see what are the different available status
select status, count(*)
from order_detail
group by status

select * from order_detail 
where sel_thickness is not null

select name, variable_weight, quantity, price, price_per_type, surcharge_fixed, order_detail.*
from order_detail
where variable_weight = 1 and surcharge_fixed <> 0

# prezzo calcolato in base a variable_weight
select order_id, ref_id, ean, name, replaceable, variable_weight, category_id, category_name, price, price_per_type, 
	# prezzo considerando price se variable_weight è zero oppure price_per_type se variable_weight è 1
	((price*(1-variable_weight))+(variable_weight*price_per_type)) item_price, 
    # il prezzo corrente rispetto al prezzo pieno in percentuale (0-1) 
	((((price*(1-variable_weight))+(variable_weight*price_per_type)) + surcharge_fixed) / ((price*(1-variable_weight))+(variable_weight*price_per_type))) 'item_promo', 
	status,
	surcharge_fixed,
    order_detail.*
from order_detail
where status <> 'NEW' and surcharge_fixed <> 0
order by order_id desc




select * from ai24.order_detail order by id desc

select * from ai24.order order by id desc

select * from ai24.store order by id desc