/**
 * Base abstract class for a plugin.
 * Plugins are used to process datasets
 */
import { Subject } from 'rxjs';

export class AoPluginComponent {
    // plugin data change will be notified using subject
    onNewDataSubject: Subject<any>;
    data: any;
    sourcePluginData: any;

    constructor() {
        this.onNewDataSubject = new Subject();
    }

    // used to get the plugin data
    getData() {
        return this.data;
    }
    // used to set the plugin data
    setData(data: any) {
        // store data
        this.data = data;
    }

    // used to update the plugin data
    updateData(data: any) {
        // store data
        this.data = data;
        this.notifyChange();
    }

    notifyChange() {
        // notify data update to subscribers
        this.onNewDataSubject.next();
    }
}

