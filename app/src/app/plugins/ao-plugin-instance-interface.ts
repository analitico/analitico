import { Subject } from 'rxjs';
export interface IAoPluginInstance {
    pluginsService: any;
    setData: any;
    onNewDataSubject: Subject<any>;
}
