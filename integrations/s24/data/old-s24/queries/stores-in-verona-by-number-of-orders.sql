# number of orders per store
select store.ref_id, store.name, store.province, store.area, store.lat, store.lng, count(ord.id) 'store_orders'
from `order` as ord
join store on store.id = ord.store_id
where province = 'VR'
group by store.ref_id, store.name, store.province, store.area, store.lat, store.lng
order by count(ord.id) desc

