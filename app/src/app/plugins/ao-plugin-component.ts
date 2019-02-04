/**
 * Base abstract class for a plugin.
 * Plugins are used to process datasets
 */
import { Subject } from 'rxjs';

export class AoPluginComponent {
    // plugin data change will be notified using subject
    onNewDataSubject: Subject<any>;
    data: any;

    constructor() {
        this.onNewDataSubject = new Subject();
    }

    setData(data: any) {
        // store data
        this.data = data;
        // notify data update
        this.onNewDataSubject.next(data);
    }
}
