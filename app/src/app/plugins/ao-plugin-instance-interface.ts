import { Subject } from 'rxjs';
export interface IAoPluginInstance {
    pluginsService: any;
    setData: any;
    getData: any;
    updateData: any;
    onNewDataSubject: Subject<any>;
    setSourcePluginData: any;
}
