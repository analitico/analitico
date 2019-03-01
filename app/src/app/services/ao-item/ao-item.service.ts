/**
 * Basic operations with items: load, save etc...
 */
import { Injectable } from '@angular/core';
import { AoApiClientService } from '../ao-api-client/ao-api-client.service';
import * as _ from 'lodash';

@Injectable({
    providedIn: 'root'
})
export class AoItemService {

    constructor(protected apiClient: AoApiClientService) { }

    // loads the json object
    loadItem(item) {
        const url = item.links.self;
        return this.apiClient.get(url)
            .then((response: any) => {
                return response.data;
            });
    }

    saveItem(item) {
        const url = item.links.self;
        return this.apiClient.patch(url, item)
            .then((response: any) => {
                return response.data;
            });
    }

    /**
     * Find if it can find a property with the required value (substring)
     * @param obj dictionary
     * @param filterString string to find
     */
    hasValueInProperty(obj, filterString) {
        if (typeof obj === 'object') {
            for (const key in obj) {
                // optional check for properties from prototype chain
                if (obj.hasOwnProperty(key)) {
                    const value = obj[key];

                    if (this.hasValueInProperty(value, filterString)) {
                        return true;
                    }

                }
            }
        } else if (Array.isArray(obj)) {
            for (let i = 0; i < obj.length; i++) {
                if (this.hasValueInProperty(obj[i], filterString)) {
                    return true;
                }
            }
        } else {
            try {
                if (('' + obj).toLowerCase().indexOf(filterString.toLowerCase()) >= 0) {
                    return true;
                }
            } catch (e) {
                console.error(e);
            }
        }

    }

    /**
     * Filter a collection of items by property values
     * @param items collection
     * @param filterString string to find in collection properties values
     */
    filterItemsByString(items, filterString) {
        const filtered = [];
        items.forEach(item => {
            if (this.hasValueInProperty(item, filterString.toLowerCase())) {
                filtered.push(item);
            }
        });
        return filtered;
    }


    /**
     * Filter a collection using a dictionary
     * @param items collection
     * @param filter dictionary of properties (path are supported) and required values
     */
    filterItemsByDictionary(items, filter): any {
        return items.filter((item) => {
            for (const filterKey in filter) {
                if (filter.hasOwnProperty(filterKey)) {
                    // get the value specified in the filter path
                    const value = _.get(item, filterKey);
                    const filterValue = filter[filterKey];
                    // compare object value with filter value
                    if (value !== filterValue) {
                        return false;
                    }
                }
            }
            return true;
        });
    }
}
