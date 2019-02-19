import { Subject } from 'rxjs';
export interface IAoPluginInstance {
    pluginsService: any;
    setData: any;
    updateData: any;
    onNewDataSubject: Subject<any>;
}
